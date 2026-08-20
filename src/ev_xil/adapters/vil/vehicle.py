"""Vehicle-in-the-Loop (VIL) Platform Adapter implementing TestPlatform contract & Real Vehicle Environment Physics."""

import math
import logging
from typing import Dict, Any, Optional, List
from ev_xil.core.platform import TestPlatform, PlatformAdapter

logger = logging.getLogger(__name__)


class RealVehicleEnvironmentMock:
    """Simulates real vehicle environment, chassis dyno physics, DAQ velocity, and gateway diagnostics."""

    def __init__(
        self,
        curb_mass_kg: float = 1600.0,
        wheel_radius_m: float = 0.32,
        drag_coefficient: float = 0.28,
        frontal_area_m2: float = 2.2,
        air_density: float = 1.225,
        rolling_resistance_cr: float = 0.015,
        max_torque_nm: float = 350.0,
        interlock_active_high: bool = True,
    ) -> None:
        self.mass_kg: float = curb_mass_kg
        self.wheel_radius_m: float = wheel_radius_m
        self.cd: float = drag_coefficient
        self.area_m2: float = frontal_area_m2
        self.rho: float = air_density
        self.crr: float = rolling_resistance_cr
        self.max_torque_nm: float = max_torque_nm
        self.interlock_active_high: bool = interlock_active_high

        self.simulation_time_ms: float = 0.0
        self.vehicle_speed_ms: float = 0.0

        # Signals Map across CAN, DAQ, and Diagnostics
        self.signals: Dict[str, float] = {
            "CAN/GW_0x100/Throttle_Pedal": 0.0,
            "CAN/GW_0x100/Interlock_State": 1.0 if interlock_active_high else 0.0,
            "CAN/GW_0x200/Motor_Torque": 0.0,
            "DAQ/WheelSpeed_Kmh": 0.0,
            "DAQ/GNSS_Velocity_Kmh": 0.0,
            "DIAG/DTC_Count": 0.0,
            "DIAG/Torque_Plausibility_Fault": 0.0,
            "Throttle_Input": 0.0,
            "Brake_Interlock": 1.0 if interlock_active_high else 0.0,
            "Motor_Torque": 0.0,
            "Vehicle_Speed": 0.0,
            "GNSS_Speed": 0.0,
            "Diagnostic_Fault": 0.0,
            "Torque_Fault": 0.0,
            "accelerator": 0.0,
            "drive_enable": 1.0 if interlock_active_high else 0.0,
            "brake": 0.0,
            "speed": 0.0,
            "torque": 0.0,
            "fault_status": 0.0,
        }

    def set_signal(self, name: str, val: float) -> None:
        val = float(val)
        self.signals[name] = val

        # Sync signal aliases across CAN, DAQ, and Diagnostics
        if name in ("CAN/GW_0x100/Throttle_Pedal", "Throttle_Input", "accelerator"):
            self.signals["CAN/GW_0x100/Throttle_Pedal"] = val
            self.signals["Throttle_Input"] = val
            self.signals["accelerator"] = val
        elif name in ("CAN/GW_0x100/Interlock_State", "Brake_Interlock", "drive_enable"):
            self.signals["CAN/GW_0x100/Interlock_State"] = val
            self.signals["Brake_Interlock"] = val
            self.signals["drive_enable"] = val

        self._update_physics()

    def get_signal(self, name: str) -> float:
        return self.signals.get(name, 0.0)

    def step(self, duration_ms: float) -> None:
        self.simulation_time_ms += duration_ms
        self._update_physics()

        # Update Vehicle Speed / DAQ GNSS Velocity based on torque
        t_val = self.signals["torque"]
        speed_increment = (t_val / 100.0) * (duration_ms / 10.0)
        new_speed = max(0.0, self.signals["speed"] + speed_increment)

        self.signals["speed"] = new_speed
        self.signals["Vehicle_Speed"] = new_speed
        self.signals["GNSS_Speed"] = new_speed
        self.signals["DAQ/WheelSpeed_Kmh"] = new_speed
        self.signals["DAQ/GNSS_Velocity_Kmh"] = new_speed
        self.vehicle_speed_ms = new_speed / 3.6

    def _update_physics(self) -> None:
        throttle = self.signals.get("accelerator", self.signals.get("Throttle_Input", 0.0))
        interlock = self.signals.get("drive_enable", self.signals.get("Brake_Interlock", 1.0))

        interlock_closed = (interlock >= 0.5) if self.interlock_active_high else (interlock < 0.5)

        if not interlock_closed:
            t_val = 0.0
            dtc_cnt = 1.0
            trq_flt = 1.0
            fault_code = 1.0
        else:
            t_val = (max(0.0, min(100.0, throttle)) / 100.0) * self.max_torque_nm
            dtc_cnt = 0.0
            trq_flt = 0.0
            fault_code = 0.0

        self.signals["torque"] = t_val
        self.signals["Motor_Torque"] = t_val
        self.signals["CAN/GW_0x200/Motor_Torque"] = t_val
        self.signals["Diagnostic_Fault"] = dtc_cnt
        self.signals["DIAG/DTC_Count"] = dtc_cnt
        self.signals["Torque_Fault"] = trq_flt
        self.signals["DIAG/Torque_Plausibility_Fault"] = trq_flt
        self.signals["fault_status"] = fault_code


class VehicleAdapter(TestPlatform):
    """VIL Platform Adapter implementing TestPlatform contract with RealVehicleEnvironmentMock."""

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(config)
        self.backend_settings: Dict[str, Any] = {}
        if config and hasattr(config, "backend_settings"):
            self.backend_settings = config.backend_settings or {}
        elif isinstance(config, dict):
            self.backend_settings = config.get("backend_settings", {})

        self.mock_mode: bool = self.backend_settings.get("mock_mode", True)
        self.curb_mass_kg: float = self.backend_settings.get("curb_mass_kg", 1600.0)
        self.wheel_radius_m: float = self.backend_settings.get("wheel_radius_m", 0.32)
        self.drag_coefficient: float = self.backend_settings.get("drag_coefficient", 0.28)
        self.max_torque_nm: float = self.backend_settings.get("max_torque_nm", 350.0)
        self.interlock_active_high: bool = self.backend_settings.get("interlock_active_high", True)

        self.env_mock: Optional[RealVehicleEnvironmentMock] = None
        self.is_mocking: bool = True
        self.is_running: bool = False

    def connect(self) -> None:
        logger.info("Initializing Vehicle-in-the-Loop (VIL) Real Vehicle Environment & Telemetry Gateway.")
        self.env_mock = RealVehicleEnvironmentMock(
            curb_mass_kg=self.curb_mass_kg,
            wheel_radius_m=self.wheel_radius_m,
            drag_coefficient=self.drag_coefficient,
            max_torque_nm=self.max_torque_nm,
            interlock_active_high=self.interlock_active_high,
        )
        self.is_mocking = True
        self.is_connected = True

    def configure(self, config: Dict[str, Any]) -> None:
        """Applies dynamic runtime configuration."""
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config.update(config)

    def start(self) -> None:
        """Starts VIL simulation execution."""
        self.is_running = True

    def stop(self) -> None:
        """Stops VIL simulation execution."""
        self.is_running = False

    def disconnect(self) -> None:
        self.stop()
        self.env_mock = None
        self.is_connected = False

    def read_signal(self, signal_name: str) -> float:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if self.env_mock:
            val = self.env_mock.get_signal(signal_name)
            if val == 0.0 and resolved != signal_name:
                val = self.env_mock.get_signal(resolved)
            return val
        return 0.0

    def write_signal(self, signal_name: str, value: float) -> None:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if self.env_mock:
            self.env_mock.set_signal(signal_name, value)
            if resolved != signal_name:
                self.env_mock.set_signal(resolved, value)

    # Shorthand aliases for TestPlatform contract
    def read(self, signal: str) -> float:
        return self.read_signal(signal)

    def write(self, signal: str, value: float) -> None:
        self.write_signal(signal, value)

    def capture(self, signals: List[str]) -> Dict[str, List[float]]:
        """Captures snapshot of specified signals."""
        return {sig: [self.read(sig)] for sig in signals}

    def step(self, duration_ms: float) -> None:
        if self.env_mock:
            self.env_mock.step(duration_ms)


# Backwards compatibility aliases
VehicleVilAdapter = VehicleAdapter
VehicleDynamicsSim = RealVehicleEnvironmentMock
