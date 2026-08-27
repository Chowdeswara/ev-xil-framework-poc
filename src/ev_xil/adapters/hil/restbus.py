import threading
import time
import struct
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def calculate_autosar_crc8(data: bytearray) -> int:
    """Calculates AUTOSAR CRC-8 Profile 1 (Polynomial 0x2F, Initial 0xFF, XOR 0xFF)."""
    crc = 0xFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x2F) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc ^ 0xFF

class RestbusSimulator:
    """Multi-threaded CAN Restbus Simulation Engine with cyclic scheduling and AUTOSAR CRC-8 Checksums."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, can_bus: Optional[Any] = None) -> None:
        self.config = config or {}
        self.can_bus = can_bus
        
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        # In-memory virtual signal registry
        self.signals: Dict[str, Dict[str, float]] = {
            "BMS": {
                "SOC": 80.0,
                "Voltage": 350.0,
                "Temperature": 25.0,
                "RollingCounter": 0.0,
            },
            "ABS": {
                "ESP_Status": 1.0,
                "WheelSpeed_FL": 0.0,
                "WheelSpeed_FR": 0.0,
                "Brake_Plausibility": 1.0,
                "RollingCounter": 0.0,
            },
            "Cluster": {
                "Odometer": 12500.0,
                "DriveMode": 1.0,  # 1=Eco, 2=Normal, 3=Sport
                "AmbientTemp": 25.0,
            },
            "MCU": {
                "Motor_Temp": 35.0,
                "Inverter_Temp": 30.0,
                "Actual_Torque": 0.0,
                "RollingCounter": 0.0,
            },
            "TCU": {
                "Selected_Gear": 1.0,  # 1=Park, 2=Reverse, 3=Neutral, 4=Drive
                "Clutch_Pressure": 0.0,
                "RollingCounter": 0.0,
            }
        }

        # Initialize from config nodes if provided
        nodes_cfg = self.config.get("nodes", {})
        for node_name, node_data in nodes_cfg.items():
            if node_name in self.signals:
                self.signals[node_name].update(node_data.get("signals", {}))

        # Default cyclic scheduling periods (in seconds)
        self.node_periods: Dict[str, float] = {
            "ABS": 0.010,       # 10ms
            "BMS": 0.020,       # 20ms
            "MCU": 0.020,       # 20ms
            "TCU": 0.050,       # 50ms
            "Cluster": 0.100,   # 100ms
        }

        # Override periods from config settings if specified
        restbus_settings = self.config.get("restbus", {}) if hasattr(self, "config") else {}
        nodes_settings = restbus_settings.get("nodes", {}) if isinstance(restbus_settings, dict) else {}
        for node_name, node_data in nodes_settings.items():
            if "cycle_period_ms" in node_data:
                self.node_periods[node_name] = node_data["cycle_period_ms"] / 1000.0

        # Fault injection flags
        self.timeouts: Dict[str, bool] = {
            "BMS": False, "ABS": False, "Cluster": False, "MCU": False, "TCU": False
        }
        self.crc_faults: Dict[str, bool] = {
            "BMS": False, "ABS": False, "Cluster": False, "MCU": False, "TCU": False
        }

    def start(self) -> None:
        """Start the background daemon cyclic broadcast thread."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self.thread = threading.Thread(target=self._cyclic_loop, daemon=True)
            self.thread.start()
            logger.info("Restbus simulation engine started.")

    def stop(self) -> None:
        """Stop the background cyclic broadcast thread."""
        with self.lock:
            if not self.is_running:
                return
            self.is_running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
            logger.info("Restbus simulation engine stopped.")

    def inject_timeout(self, node: str, enable: bool) -> None:
        """Inject communication timeout (drops frame) for the specified node."""
        with self.lock:
            if node in self.timeouts:
                self.timeouts[node] = enable

    def inject_crc_counter_fault(self, node: str, enable: bool) -> None:
        """Inject rolling counter/CRC corruption for the specified node."""
        with self.lock:
            if node in self.crc_faults:
                self.crc_faults[node] = enable

    def set_signal(self, node: str, signal_name: str, value: float) -> None:
        """Dynamically update a signal value at runtime."""
        with self.lock:
            if node in self.signals and signal_name in self.signals[node]:
                self.signals[node][signal_name] = float(value)

    def get_signal(self, node: str, signal_name: str) -> float:
        """Read a signal value at runtime."""
        with self.lock:
            return self.signals.get(node, {}).get(signal_name, 0.0)

    def _cyclic_loop(self) -> None:
        """Cyclic loop running in background thread with node-specific cycle times."""
        last_ticks: Dict[str, float] = {
            "BMS": 0.0, "ABS": 0.0, "Cluster": 0.0, "MCU": 0.0, "TCU": 0.0
        }
        counters: Dict[str, int] = {
            "BMS": 0, "ABS": 0, "Cluster": 0, "MCU": 0, "TCU": 0
        }

        # Resolution scheduler tick (2ms)
        loop_tick_s = 0.002

        while True:
            current_time = time.time()
            
            with self.lock:
                if not self.is_running:
                    break
                timeouts = dict(self.timeouts)
                crc_faults = dict(self.crc_faults)
                bms_data = dict(self.signals["BMS"])
                abs_data = dict(self.signals["ABS"])
                cluster_data = dict(self.signals["Cluster"])
                mcu_data = dict(self.signals["MCU"])
                tcu_data = dict(self.signals["TCU"])
                periods = dict(self.node_periods)

            # Check and broadcast BMS
            if current_time - last_ticks["BMS"] >= periods["BMS"]:
                counters["BMS"] = (counters["BMS"] + 1) % 16
                bms_data["RollingCounter"] = 99.0 if crc_faults["BMS"] else float(counters["BMS"])
                if not timeouts["BMS"]:
                    self._send_frame(0x301, bms_data, crc_faults["BMS"])
                last_ticks["BMS"] = current_time

            # Check and broadcast ABS
            if current_time - last_ticks["ABS"] >= periods["ABS"]:
                counters["ABS"] = (counters["ABS"] + 1) % 16
                abs_data["RollingCounter"] = 99.0 if crc_faults["ABS"] else float(counters["ABS"])
                if not timeouts["ABS"]:
                    self._send_frame(0x205, abs_data, crc_faults["ABS"])
                last_ticks["ABS"] = current_time

            # Check and broadcast Cluster
            if current_time - last_ticks["Cluster"] >= periods["Cluster"]:
                counters["Cluster"] = (counters["Cluster"] + 1) % 16
                cluster_data["RollingCounter"] = 99.0 if crc_faults["Cluster"] else float(counters["Cluster"])
                if not timeouts["Cluster"]:
                    self._send_frame(0x401, cluster_data, crc_faults["Cluster"])
                last_ticks["Cluster"] = current_time

            # Check and broadcast MCU
            if current_time - last_ticks["MCU"] >= periods["MCU"]:
                counters["MCU"] = (counters["MCU"] + 1) % 16
                mcu_data["RollingCounter"] = 99.0 if crc_faults["MCU"] else float(counters["MCU"])
                if not timeouts["MCU"]:
                    self._send_frame(0x150, mcu_data, crc_faults["MCU"])
                last_ticks["MCU"] = current_time

            # Check and broadcast TCU
            if current_time - last_ticks["TCU"] >= periods["TCU"]:
                counters["TCU"] = (counters["TCU"] + 1) % 16
                tcu_data["RollingCounter"] = 99.0 if crc_faults["TCU"] else float(counters["TCU"])
                if not timeouts["TCU"]:
                    self._send_frame(0x220, tcu_data, crc_faults["TCU"])
                last_ticks["TCU"] = current_time

            time.sleep(loop_tick_s)

    def _send_frame(self, arbitration_id: int, data_dict: Dict[str, float], corrupt_crc: bool = False) -> None:
        """Formats and transmits CAN frame, calculating AUTOSAR CRC-8 Checksum for Byte 7."""
        payload = bytearray(8)
        if arbitration_id == 0x301:
            soc = int(max(0, min(100, data_dict.get("SOC", 80.0))))
            volts = int(max(0, min(1000, data_dict.get("Voltage", 350.0))))
            temp = int(max(-40, min(120, data_dict.get("Temperature", 25.0))) + 40)
            cnt = int(data_dict.get("RollingCounter", 0.0)) & 0x0F
            
            payload[0] = soc
            struct.pack_into(">H", payload, 1, volts)
            payload[3] = temp
            payload[4] = cnt
            
        elif arbitration_id == 0x205:
            esp = int(data_dict.get("ESP_Status", 1.0)) & 0xFF
            ws_fl = int(max(0, min(250, data_dict.get("WheelSpeed_FL", 0.0))) * 10)
            ws_fr = int(max(0, min(250, data_dict.get("WheelSpeed_FR", 0.0))) * 10)
            brake = int(data_dict.get("Brake_Plausibility", 1.0)) & 0xFF
            cnt = int(data_dict.get("RollingCounter", 0.0)) & 0x0F
            
            payload[0] = esp
            struct.pack_into(">H", payload, 1, ws_fl)
            struct.pack_into(">H", payload, 3, ws_fr)
            payload[5] = brake
            payload[6] = cnt
            
        elif arbitration_id == 0x401:
            odo = int(max(0, min(999999, data_dict.get("Odometer", 12500.0))))
            mode = int(data_dict.get("DriveMode", 1.0)) & 0xFF
            temp = int(max(-40, min(100, data_dict.get("AmbientTemp", 25.0))) + 40)
            
            payload[0] = (odo >> 16) & 0xFF
            payload[1] = (odo >> 8) & 0xFF
            payload[2] = odo & 0xFF
            payload[3] = mode
            payload[4] = temp

        elif arbitration_id == 0x150:
            m_temp = int(max(-40, min(150, data_dict.get("Motor_Temp", 35.0))) + 40)
            i_temp = int(max(-40, min(120, data_dict.get("Inverter_Temp", 30.0))) + 40)
            torque = int(max(-500, min(500, data_dict.get("Actual_Torque", 0.0))) + 500)
            cnt = int(data_dict.get("RollingCounter", 0.0)) & 0x0F

            payload[0] = m_temp
            payload[1] = i_temp
            struct.pack_into(">H", payload, 2, torque)
            payload[4] = cnt

        elif arbitration_id == 0x220:
            gear = int(data_dict.get("Selected_Gear", 1.0)) & 0xFF
            press = int(max(0, min(50, data_dict.get("Clutch_Pressure", 0.0))) * 10)
            cnt = int(data_dict.get("RollingCounter", 0.0)) & 0x0F

            payload[0] = gear
            struct.pack_into(">H", payload, 1, press)
            payload[3] = cnt

        # Compute J1850 / AUTOSAR CRC-8 Checksum over Bytes 0 to 6
        crc_val = calculate_autosar_crc8(payload[:7])
        
        # Inject corrupted checksum byte if fault active
        payload[7] = 0xAA if corrupt_crc else crc_val

        if self.can_bus:
            try:
                import can
                msg = can.Message(arbitration_id=arbitration_id, data=payload, is_extended_id=False)
                self.can_bus.send(msg)
            except Exception as e:
                logger.warning(f"Failed to transmit frame 0x{arbitration_id:03X} on python-can bus: {e}")
