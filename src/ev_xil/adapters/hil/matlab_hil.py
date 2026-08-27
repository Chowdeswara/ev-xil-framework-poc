"""ASAM XIL 2.1 / CAN Architecture HIL Platform Adapter implementing TestPlatform contract & Multi-Port Routing."""

import os
import struct
import logging
from typing import Dict, Any, Optional, List
from ev_xil.core.platform import TestPlatform, PlatformAdapter
from ev_xil.adapters.hil.restbus import RestbusSimulator

logger = logging.getLogger(__name__)

# Attempt to import python-can if SocketCAN / Vector hardware is present
try:
    import can
    CAN_HARDWARE_AVAILABLE = True
except ImportError:
    CAN_HARDWARE_AVAILABLE = False


class ASAMXILMockPort:
    """ASAM XIL 2.1 MAPort Mock & Multi-Port Emulation Engine for Speedgoat / Vector HIL test benches."""

    def __init__(
        self,
        max_torque_nm: float = 350.0,
        interlock_active_high: bool = True,
        communication_delay_ms: float = 2.0,
    ) -> None:
        self.max_torque_nm: float = max_torque_nm
        self.interlock_active_high: bool = interlock_active_high
        self.communication_delay_ms: float = communication_delay_ms
        self.simulation_time_ms: float = 0.0

        # CAN raw payload registers (8-byte payload frames)
        self.can_rx_0x100: bytearray = bytearray(8)  # Control message
        self.can_tx_0x200: bytearray = bytearray(8)  # Feedback message

        # Active faults map: signal_name -> {"type": str, "value": float}
        self.active_faults: Dict[str, Dict[str, Any]] = {}

        # Default decoded signal values across ports
        self.signals: Dict[str, float] = {
            "CAN_0x100_Byte0": 0.0,
            "CAN_0x100_Byte1_Bit0": 1.0 if interlock_active_high else 0.0,
            "CAN_0x200_Byte0_1": 0.0,
            "CAN_0x200_Byte2_3": 0.0,
            "accelerator": 0.0,
            "drive_enable": 1.0 if interlock_active_high else 0.0,
            "brake": 0.0,
            "speed": 0.0,
            "torque": 0.0,
            "Throttle_Input": 0.0,
            "Brake_Interlock": 1.0 if interlock_active_high else 0.0,
            "Speedgoat/Plant/Pedal_Position": 0.0,
            "Speedgoat/Plant/HV_Interlock_Pin": 1.0 if interlock_active_high else 0.0,
            "Motor_Torque": 0.0,
            "Vehicle_Speed": 0.0,
            "VehicleSpeed_CAN": 0.0,
            "TorqueRequest_CAN": 0.0,
            "CAN1/Msg0x200/VehicleSpeed": 0.0,
            "CAN1/Msg0x200/TorqueRequest": 0.0,
            "ECU_State": 1.0,  # 1.0 = RUNNING, 0.0 = SHUTDOWN
            "ECU/OperatingState": 1.0,
            "ECU_DiagnosticStatus": 0.0,  # 0.0 = NO_DTC, 53249.0 (0xD001) = DTC_INTERLOCK_OPEN
            "ECU/DTC_Status": 0.0,
            "accel_pedal_pos": 0.0,
            "hv_interlock": 1.0 if interlock_active_high else 0.0,
            "motor_torque_nm": 0.0,
            "motor_speed_rpm": 0.0,
            "fault_status": 0.0,
        }
        self.restbus: Optional[RestbusSimulator] = None
        self._pack_can_tx_0x200(0.0, 0.0)

    def inject_fault(self, signal_name: str, fault_type: str, value: float = 0.0) -> None:
        """Injects electrical or bus communication faults (OPEN_CIRCUIT, COMM_TIMEOUT, STUCK_AT)."""
        self.active_faults[signal_name] = {"type": fault_type.upper(), "value": float(value)}
        self._update_can_physics()

    def clear_faults(self) -> None:
        """Clears all active fault conditions."""
        self.active_faults.clear()
        self._update_can_physics()

    def set_signal(self, name: str, val: float) -> None:
        val = float(val)

        if name in self.active_faults:
            fault = self.active_faults[name]
            if fault["type"] == "STUCK_AT":
                val = fault["value"]
            elif fault["type"] in ("OPEN_CIRCUIT", "SHORT_TO_GROUND"):
                val = 0.0

        self.signals[name] = val

        # Sync signal names across ports
        if name in ("CAN_0x100_Byte0", "Throttle_Input", "accel_pedal_pos", "accelerator", "Speedgoat/Plant/Pedal_Position"):
            self.signals["CAN_0x100_Byte0"] = val
            self.signals["Throttle_Input"] = val
            self.signals["accel_pedal_pos"] = val
            self.signals["accelerator"] = val
            self.signals["Speedgoat/Plant/Pedal_Position"] = val
            self.can_rx_0x100[0] = int((max(0.0, min(100.0, val)) / 100.0) * 255)
        elif name in ("CAN_0x100_Byte1_Bit0", "Brake_Interlock", "hv_interlock", "drive_enable", "Speedgoat/Plant/HV_Interlock_Pin"):
            self.signals["CAN_0x100_Byte1_Bit0"] = val
            self.signals["Brake_Interlock"] = val
            self.signals["hv_interlock"] = val
            self.signals["drive_enable"] = val
            self.signals["Speedgoat/Plant/HV_Interlock_Pin"] = val
            bit_val = 1 if val >= 0.5 else 0
            self.can_rx_0x100[1] = (self.can_rx_0x100[1] & 0xFE) | bit_val
        elif name in ("brake", "brake_pedal_pos"):
            self.signals["brake"] = val
            self.signals["brake_pedal_pos"] = val

        self._update_can_physics()

    def get_signal(self, name: str) -> float:
        if name in self.active_faults:
            fault = self.active_faults[name]
            if fault["type"] in ("OPEN_CIRCUIT", "SHORT_TO_GROUND"):
                return 0.0
            elif fault["type"] == "STUCK_AT":
                return fault["value"]

        return self.signals.get(name, 0.0)

    def step(self, duration_ms: float) -> None:
        self.simulation_time_ms += duration_ms
        self._update_can_physics()

        # Update vehicle speed
        t_val = self.signals["torque"]
        speed_inc = (t_val / 100.0) * (duration_ms / 10.0)
        new_speed = max(0.0, self.signals["speed"] + speed_inc)
        self.signals["speed"] = new_speed
        self.signals["Vehicle_Speed"] = new_speed
        self.signals["VehicleSpeed_CAN"] = new_speed
        self.signals["CAN1/Msg0x200/VehicleSpeed"] = new_speed
        self.signals["CAN_0x200_Byte2_3"] = new_speed
        self.signals["motor_speed_rpm"] = new_speed * 60.0

        self._pack_can_tx_0x200(t_val, new_speed)

    def _pack_can_tx_0x200(self, torque_nm: float, speed_kmh: float) -> None:
        t_int = max(0, min(65535, int((torque_nm / 500.0) * 65535)))
        s_int = max(0, min(65535, int((speed_kmh / 250.0) * 65535)))
        struct.pack_into(">HH", self.can_tx_0x200, 0, t_int, s_int)

    def _update_can_physics(self) -> None:

        if "COMM_TIMEOUT" in [f["type"] for f in self.active_faults.values()]:
            self.signals["torque"] = 0.0
            self.signals["Motor_Torque"] = 0.0
            self.signals["TorqueRequest_CAN"] = 0.0
            self.signals["CAN1/Msg0x200/TorqueRequest"] = 0.0
            self.signals["CAN_0x200_Byte0_1"] = 0.0
            self.signals["ECU_State"] = 0.0
            self.signals["ECU/OperatingState"] = 0.0
            self.signals["ECU_DiagnosticStatus"] = 57346.0  # 0xE002
            self.signals["ECU/DTC_Status"] = 57346.0
            self.signals["fault_status"] = 1.0
            return

        throttle = self.signals.get("accelerator", self.signals.get("Throttle_Input", self.signals.get("Speedgoat/Plant/Pedal_Position", 0.0)))
        interlock = self.signals.get("drive_enable", self.signals.get("Brake_Interlock", self.signals.get("Speedgoat/Plant/HV_Interlock_Pin", 1.0)))

        if "Brake_Interlock" in self.active_faults or "drive_enable" in self.active_faults or "Speedgoat/Plant/HV_Interlock_Pin" in self.active_faults:
            fault_key = "drive_enable" if "drive_enable" in self.active_faults else "Brake_Interlock"
            if "Speedgoat/Plant/HV_Interlock_Pin" in self.active_faults:
                fault_key = "Speedgoat/Plant/HV_Interlock_Pin"
            fault = self.active_faults[fault_key]
            if fault["type"] in ("OPEN_CIRCUIT", "SHORT_TO_GROUND"):
                interlock = 0.0
            elif fault["type"] == "STUCK_AT":
                interlock = fault["value"]

        interlock_closed = (interlock >= 0.5) if self.interlock_active_high else (interlock < 0.5)

        if not interlock_closed:
            t_val = 0.0
            ecu_st = 0.0  # SHUTDOWN
            dtc = 53249.0  # 0xD001 (DTC_INTERLOCK_FAULT)
            fault_code = 1.0
        else:
            t_val = (max(0.0, min(100.0, throttle)) / 100.0) * self.max_torque_nm
            
            # Check restbus status (BMS, MCU, TCU)
            restbus_fault = False
            if hasattr(self, "restbus") and self.restbus:
                bms_timeout = self.restbus.timeouts.get("BMS", False)
                bms_crc = self.restbus.crc_faults.get("BMS", False)
                mcu_timeout = self.restbus.timeouts.get("MCU", False)
                mcu_crc = self.restbus.crc_faults.get("MCU", False)
                tcu_timeout = self.restbus.timeouts.get("TCU", False)
                tcu_crc = self.restbus.crc_faults.get("TCU", False)
                if bms_timeout or bms_crc or mcu_timeout or mcu_crc or tcu_timeout or tcu_crc:
                    restbus_fault = True

            if restbus_fault:
                ecu_st = 3.0  # Limp/Fault
                dtc = 81.0  # DTC 0x51
                fault_code = 1.0
            else:
                ecu_st = 2.0 if (hasattr(self, "restbus") and self.restbus) else 1.0
                dtc = 0.0
                fault_code = 0.0

        self.signals["torque"] = t_val
        self.signals["Motor_Torque"] = t_val
        self.signals["TorqueRequest_CAN"] = t_val
        self.signals["CAN1/Msg0x200/TorqueRequest"] = t_val
        self.signals["CAN_0x200_Byte0_1"] = t_val
        self.signals["motor_torque_nm"] = t_val
        self.signals["ECU_State"] = ecu_st
        self.signals["ECU/OperatingState"] = ecu_st
        self.signals["ECU_DiagnosticStatus"] = dtc
        self.signals["ECU/DTC_Status"] = dtc
        self.signals["fault_status"] = fault_code


class MatlabHilAdapter(TestPlatform):
    """HIL Platform Adapter implementing TestPlatform contract & Multi-Port ASAM XIL Routing (MAPort, NetworkPort, ECUMPort)."""

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(config)
        self.backend_settings: Dict[str, Any] = {}
        self.maport_map: Dict[str, str] = {}
        self.network_port_map: Dict[str, str] = {}
        self.ecu_port_map: Dict[str, str] = {}

        if config:
            if hasattr(config, "backend_settings"):
                self.backend_settings = config.backend_settings or {}
            elif isinstance(config, dict):
                self.backend_settings = config.get("backend_settings", {})

            if hasattr(config, "maport"):
                self.maport_map = config.maport or {}
            if hasattr(config, "network_port"):
                self.network_port_map = config.network_port or {}
            if hasattr(config, "ecu_port"):
                self.ecu_port_map = config.ecu_port or {}

        self.mock_mode: bool = self.backend_settings.get("mock_mode", True)
        self.max_torque_nm: float = self.backend_settings.get("max_torque_nm", 350.0)
        self.interlock_active_high: bool = self.backend_settings.get("interlock_active_high", True)
        self.comm_delay_ms: float = self.backend_settings.get("communication_delay_ms", 2.0)
        self.can_bustype: str = self.backend_settings.get("can_bustype", "virtual")

        self.can_bus: Optional[Any] = None
        self.mock_port: Optional[ASAMXILMockPort] = None
        self.restbus: Optional[RestbusSimulator] = None
        self.is_mocking: bool = True
        self.is_running: bool = False

    def connect(self) -> None:
        """Connects to real SocketCAN / Vector hardware or initializes ASAMXILMockPort."""
        if CAN_HARDWARE_AVAILABLE and not self.mock_mode and self.can_bustype != "virtual":
            try:
                logger.info(f"Connecting to hardware CAN bus ({self.can_bustype})...")
                self.can_bus = can.interface.Bus(bustype=self.can_bustype, channel=0, bitrate=500000)
                self.restbus = RestbusSimulator(self.backend_settings, self.can_bus)
                self.restbus.start()
                self.is_mocking = False
                self.is_connected = True
                return
            except Exception as e:
                logger.warning(f"Failed to connect to hardware CAN bus ({e}). Auto-switching to ASAMXILMockPort.")

        logger.info("Using ASAMXILMockPort engine for Multi-Port HIL execution.")
        self.mock_port = ASAMXILMockPort(
            max_torque_nm=self.max_torque_nm,
            interlock_active_high=self.interlock_active_high,
            communication_delay_ms=self.comm_delay_ms,
        )
        self.restbus = RestbusSimulator(self.backend_settings, None)
        self.restbus.start()
        self.mock_port.restbus = self.restbus
        self.is_mocking = True
        self.is_connected = True

    def configure(self, config: Dict[str, Any]) -> None:
        """Applies dynamic runtime configuration."""
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config.update(config)

    def start(self) -> None:
        """Starts HIL hardware execution."""
        self.is_running = True

    def stop(self) -> None:
        """Stops HIL hardware execution."""
        self.is_running = False

    def disconnect(self) -> None:
        self.stop()
        if self.restbus:
            try:
                self.restbus.stop()
            except Exception:
                pass
            self.restbus = None
        if self.can_bus:
            try:
                self.can_bus.shutdown()
            except Exception:
                pass
            self.can_bus = None
        self.mock_port = None
        self.is_connected = False

    def inject_fault(self, signal_name: str, fault_type: str, value: float = 0.0) -> None:
        """Injects electrical or communication fault on HIL bus."""
        if self.mock_port:
            self.mock_port.inject_fault(signal_name, fault_type, value)

    def clear_faults(self) -> None:
        """Clears all injected faults."""
        if self.mock_port:
            self.mock_port.clear_faults()

    # Multi-Port Specific Accessors
    def read_maport(self, signal: str) -> float:
        resolved = self.maport_map.get(signal, signal)
        return self.read_signal(resolved)

    def write_maport(self, signal: str, value: float) -> None:
        resolved = self.maport_map.get(signal, signal)
        self.write_signal(resolved, value)

    def read_network_port(self, signal: str) -> float:
        resolved = self.network_port_map.get(signal, signal)
        return self.read_signal(resolved)

    def write_network_port(self, signal: str, value: float) -> None:
        resolved = self.network_port_map.get(signal, signal)
        self.write_signal(resolved, value)

    def read_ecu_port(self, signal: str) -> float:
        resolved = self.ecu_port_map.get(signal, signal)
        return self.read_signal(resolved)

    def write_ecu_port(self, signal: str, value: float) -> None:
        resolved = self.ecu_port_map.get(signal, signal)
        self.write_signal(resolved, value)

    def read_signal(self, signal_name: str) -> float:
        # Route restbus signal queries (e.g. BMS/SOC, MCU/Motor_Temp)
        if "/" in signal_name:
            parts = signal_name.split("/", 1)
            if parts[0] in ("BMS", "ABS", "Cluster", "MCU", "TCU") and self.restbus:
                try:
                    return float(self.restbus.get_signal(parts[0], parts[1]))
                except (ValueError, TypeError):
                    return self.restbus.get_signal(parts[0], parts[1])

        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if self.is_mocking and self.mock_port:
            val = self.mock_port.get_signal(signal_name)
            if val == 0.0 and resolved != signal_name:
                val = self.mock_port.get_signal(resolved)
            return val
        return 0.0

    def write_signal(self, signal_name: str, value: float) -> None:
        # Route restbus signal updates (e.g. BMS/SOC, MCU/Motor_Temp)
        if "/" in signal_name:
            parts = signal_name.split("/", 1)
            if parts[0] in ("BMS", "ABS", "Cluster", "MCU", "TCU") and self.restbus:
                self.restbus.set_signal(parts[0], parts[1], value)
                return

        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if self.is_mocking and self.mock_port:
            self.mock_port.set_signal(signal_name, value)
            if resolved != signal_name:
                self.mock_port.set_signal(resolved, value)

    # Shorthand aliases for TestPlatform contract
    def read(self, signal: str) -> float:
        return self.read_signal(signal)

    def write(self, signal: str, value: float) -> None:
        self.write_signal(signal, value)

    def capture(self, signals: List[str]) -> Dict[str, List[float]]:
        """Captures snapshot of specified signals."""
        return {sig: [self.read(sig)] for sig in signals}

    def step(self, duration_ms: float) -> None:
        if self.is_mocking and self.mock_port:
            self.mock_port.step(duration_ms)


# Backwards compatibility aliases
MatlabXilAdapter = MatlabHilAdapter
HilCanNetworkMock = ASAMXILMockPort
