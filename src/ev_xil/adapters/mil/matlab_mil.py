"""MATLAB / Simulink Model-in-the-Loop (MIL) Adapter implementing TestPlatform contract."""

import os
import logging
from typing import Dict, Any, Optional, List
from ev_xil.core.platform import TestPlatform, PlatformAdapter

logger = logging.getLogger(__name__)

# Attempt to import matlab.engine if available
try:
    import matlab.engine
    MATLAB_ENGINE_AVAILABLE = True
except ImportError:
    MATLAB_ENGINE_AVAILABLE = False


class StatefulMockEngine:
    """Stateful Mock Simulation Engine for EV Powertrain MIL testing when MATLAB is absent."""

    def __init__(self, max_torque_nm: float = 350.0, interlock_active_high: bool = True) -> None:
        self.max_torque_nm: float = max_torque_nm
        self.interlock_active_high: bool = interlock_active_high
        self.simulation_time_ms: float = 0.0

        # State storage
        self.signals: Dict[str, float] = {
            "accelerator": 0.0,
            "drive_enable": 1.0 if interlock_active_high else 0.0,
            "brake": 0.0,
            "speed": 0.0,
            "torque": 0.0,
            "Throttle_Input": 0.0,
            "Brake_Interlock": 1.0 if interlock_active_high else 0.0,
            "Motor_Torque": 0.0,
            "Vehicle_Speed": 0.0,
            "accel_pedal_pos": 0.0,
            "hv_interlock": 1.0 if interlock_active_high else 0.0,
            "motor_torque_nm": 0.0,
            "motor_speed_rpm": 0.0,
            "fault_status": 0.0,
        }

    def set_signal(self, name: str, val: float) -> None:
        val = float(val)
        self.signals[name] = val

        # Sync alias names
        if name in ("accelerator", "Throttle_Input", "accel_pedal_pos"):
            self.signals["accelerator"] = val
            self.signals["Throttle_Input"] = val
            self.signals["accel_pedal_pos"] = val
        elif name in ("drive_enable", "Brake_Interlock", "hv_interlock"):
            self.signals["drive_enable"] = val
            self.signals["Brake_Interlock"] = val
            self.signals["hv_interlock"] = val
        elif name in ("brake", "brake_pedal_pos"):
            self.signals["brake"] = val
            self.signals["brake_pedal_pos"] = val

        self._update_physics()

    def get_signal(self, name: str) -> float:
        return self.signals.get(name, 0.0)

    def step(self, duration_ms: float) -> None:
        self.simulation_time_ms += duration_ms
        self._update_physics()

        # Simple vehicle physics model: Speed = Speed + (Torque/100) * (dt/10)
        torque = self.signals["torque"]
        speed_inc = (torque / 100.0) * (duration_ms / 10.0)
        new_speed = max(0.0, self.signals["speed"] + speed_inc)
        self.signals["speed"] = new_speed
        self.signals["Vehicle_Speed"] = new_speed
        self.signals["motor_speed_rpm"] = new_speed * 60.0

    def _update_physics(self) -> None:
        throttle = self.signals.get("accelerator", self.signals.get("Throttle_Input", 0.0))
        interlock = self.signals.get("drive_enable", self.signals.get("Brake_Interlock", 1.0))

        interlock_closed = (interlock >= 0.5) if self.interlock_active_high else (interlock < 0.5)

        if not interlock_closed:
            t_val = 0.0
            fault = 1.0
        else:
            t_val = (max(0.0, min(100.0, throttle)) / 100.0) * self.max_torque_nm
            fault = 0.0

        self.signals["torque"] = t_val
        self.signals["Motor_Torque"] = t_val
        self.signals["motor_torque_nm"] = t_val
        self.signals["fault_status"] = fault


class MatlabMILPlatform(TestPlatform):
    """MIL Platform Adapter implementing TestPlatform contract with MATLAB Engine & Stateful Mock Engine."""

    def __init__(self, config: Optional[Any] = None) -> None:
        super().__init__(config)
        self.backend_settings: Dict[str, Any] = {}
        if config and hasattr(config, "backend_settings"):
            self.backend_settings = config.backend_settings or {}
        elif isinstance(config, dict):
            self.backend_settings = config.get("backend_settings", {})

        self.mock_mode: bool = self.backend_settings.get("mock_mode", True)
        self.max_torque_nm: float = self.backend_settings.get("max_torque_nm", 350.0)
        self.interlock_active_high: bool = self.backend_settings.get("interlock_active_high", True)

        self.matlab_engine: Optional[Any] = None
        self.mock_engine: Optional[StatefulMockEngine] = None
        self.is_mocking: bool = True
        self.is_running: bool = False

    def connect(self) -> None:
        if MATLAB_ENGINE_AVAILABLE and not self.mock_mode:
            try:
                # 1. Check if an interactive MATLAB GUI desktop session is open & shared
                active_sessions = matlab.engine.find_matlab()
                if active_sessions:
                    logger.info(f"Connecting to open shared MATLAB GUI session: {active_sessions[0]}")
                    self.matlab_engine = matlab.engine.connect_matlab(active_sessions[0])
                else:
                    logger.info("Connecting to new MATLAB Engine instance...")
                    self.matlab_engine = matlab.engine.start_matlab()

                model_path = getattr(self.config, "model_path", None)
                if model_path and os.path.exists(model_path):
                    self.matlab_engine.load_system(model_path, nargout=0)

                self.mock_engine = StatefulMockEngine(
                    max_torque_nm=self.max_torque_nm,
                    interlock_active_high=self.interlock_active_high,
                )
                self.is_mocking = False
                self.is_connected = True
                return
            except Exception as e:
                logger.warning(f"Failed to connect to live MATLAB Engine ({e}). Auto-switching to Mock Engine.")

        logger.info("Using Stateful Mock Engine for MIL execution.")
        self.mock_engine = StatefulMockEngine(
            max_torque_nm=self.max_torque_nm,
            interlock_active_high=self.interlock_active_high,
        )
        self.is_mocking = True
        self.is_connected = True

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply dynamic configurations or update backend settings."""
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config.update(config)

    def start(self) -> None:
        """Starts simulation execution."""
        self.is_running = True
        if not self.is_mocking and self.matlab_engine:
            try:
                self.matlab_engine.set_param("EV_Controller", "SimulationCommand", "start", nargout=0)
            except Exception as e:
                logger.warning(f"Could not issue start command to Simulink: {e}")

    def stop(self) -> None:
        """Stops simulation execution."""
        self.is_running = False
        if not self.is_mocking and self.matlab_engine:
            try:
                self.matlab_engine.set_param("EV_Controller", "SimulationCommand", "stop", nargout=0)
            except Exception as e:
                logger.warning(f"Could not issue stop command to Simulink: {e}")

    def disconnect(self) -> None:
        self.stop()
        if self.matlab_engine is not None:
            try:
                self.matlab_engine.quit()
            except Exception:
                pass
            self.matlab_engine = None
        self.mock_engine = None
        self.is_connected = False

    def read_signal(self, signal_name: str) -> float:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if not self.is_mocking and self.matlab_engine:
            try:
                return float(self.matlab_engine.get_param(resolved, "Value"))
            except Exception as e:
                logger.warning(f"Live MATLAB get_param failed for '{resolved}' ({e}). Falling back to Mock Engine.")
                self.is_mocking = True

        if self.mock_engine:
            val = self.mock_engine.get_signal(signal_name)
            if val == 0.0 and resolved != signal_name:
                val = self.mock_engine.get_signal(resolved)
            return val
        return 0.0

    def write_signal(self, signal_name: str, value: float) -> None:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name
        if not self.is_mocking and self.matlab_engine:
            try:
                self.matlab_engine.set_param(resolved, "Value", str(value), nargout=0)
            except Exception as e:
                logger.warning(f"Live MATLAB set_param failed for '{resolved}' ({e}). Falling back to Mock Engine.")
                self.is_mocking = True

        if self.mock_engine:
            self.mock_engine.set_signal(signal_name, value)
            if resolved != signal_name:
                self.mock_engine.set_signal(resolved, value)

    # Shorthand aliases for TestPlatform contract
    def read(self, signal: str) -> float:
        return self.read_signal(signal)

    def write(self, signal: str, value: float) -> None:
        self.write_signal(signal, value)

    def capture(self, signals: List[str]) -> Dict[str, List[float]]:
        """Captures snapshot of specified signals."""
        return {sig: [self.read(sig)] for sig in signals}

    def step(self, duration_ms: float) -> None:
        if not self.is_mocking and self.matlab_engine:
            try:
                self.matlab_engine.set_param("EV_Controller", "SimulationCommand", "step", nargout=0)
            except Exception as e:
                logger.warning(f"Live MATLAB step failed ({e}). Falling back to Mock Engine.")
                self.is_mocking = True

        if self.mock_engine:
            self.mock_engine.step(duration_ms)


# Backwards compatibility aliases
MatlabMilAdapter = MatlabMILPlatform
