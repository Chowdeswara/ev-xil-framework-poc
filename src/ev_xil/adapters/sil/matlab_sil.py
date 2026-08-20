"""Software-in-the-Loop (SIL) Adapter implementing TestPlatform contract with C-DLL & Virtual C-Runtime."""

import os
import ctypes
import logging
from typing import Dict, Any, Optional, List
from ev_xil.core.platform import TestPlatform, PlatformAdapter

logger = logging.getLogger(__name__)


class VirtualCRuntime:
    """Simulates AUTOSAR / C-code ECU periodic task execution and global memory structures."""

    def __init__(self, max_torque_nm: float = 350.0, interlock_active_high: bool = True, task_period_ms: float = 10.0) -> None:
        self.max_torque_nm: float = max_torque_nm
        self.interlock_active_high: bool = interlock_active_high
        self.task_period_ms: float = task_period_ms
        self.simulation_time_ms: float = 0.0

        # C-structure memory simulation
        self.c_memory: Dict[str, float] = {
            "EV_Controller_U.Throttle_Pedal_In": 0.0,
            "EV_Controller_U.HV_Interlock_State": 1.0 if interlock_active_high else 0.0,
            "EV_Controller_Y.Target_Torque_Out": 0.0,
            "EV_Plant_Y.Vehicle_Speed_Kmh": 0.0,
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

    def write_var(self, var_name: str, val: float) -> None:
        val = float(val)
        self.c_memory[var_name] = val

        # Sync mapped C-struct fields with canonical logical names
        if var_name in ("EV_Controller_U.Throttle_Pedal_In", "Throttle_Input", "accel_pedal_pos", "accelerator"):
            self.c_memory["EV_Controller_U.Throttle_Pedal_In"] = val
            self.c_memory["Throttle_Input"] = val
            self.c_memory["accel_pedal_pos"] = val
            self.c_memory["accelerator"] = val
        elif var_name in ("EV_Controller_U.HV_Interlock_State", "Brake_Interlock", "hv_interlock", "drive_enable"):
            self.c_memory["EV_Controller_U.HV_Interlock_State"] = val
            self.c_memory["Brake_Interlock"] = val
            self.c_memory["hv_interlock"] = val
            self.c_memory["drive_enable"] = val
        elif var_name in ("brake", "brake_pedal_pos"):
            self.c_memory["brake"] = val
            self.c_memory["brake_pedal_pos"] = val

        self._execute_c_task()

    def read_var(self, var_name: str) -> float:
        return self.c_memory.get(var_name, 0.0)

    def step(self, duration_ms: float) -> None:
        steps = max(1, int(duration_ms / self.task_period_ms))
        for _ in range(steps):
            self.simulation_time_ms += self.task_period_ms
            self._execute_c_task()

            # Integrate Vehicle Speed (Kmh)
            t_val = self.c_memory["EV_Controller_Y.Target_Torque_Out"]
            speed_inc = (t_val / 100.0) * (self.task_period_ms / 10.0)
            new_speed = max(0.0, self.c_memory["EV_Plant_Y.Vehicle_Speed_Kmh"] + speed_inc)
            self.c_memory["EV_Plant_Y.Vehicle_Speed_Kmh"] = new_speed
            self.c_memory["Vehicle_Speed"] = new_speed
            self.c_memory["speed"] = new_speed

    def _execute_c_task(self) -> None:
        """Simulates periodic ECU 10ms C-task function `EV_Controller_Step()`."""
        throttle = self.c_memory.get("accelerator", self.c_memory.get("EV_Controller_U.Throttle_Pedal_In", 0.0))
        interlock = self.c_memory.get("drive_enable", self.c_memory.get("EV_Controller_U.HV_Interlock_State", 1.0))

        interlock_closed = (interlock >= 0.5) if self.interlock_active_high else (interlock < 0.5)

        if not interlock_closed:
            t_val = 0.0
            fault = 1.0
        else:
            t_val = (max(0.0, min(100.0, throttle)) / 100.0) * self.max_torque_nm
            fault = 0.0

        self.c_memory["EV_Controller_Y.Target_Torque_Out"] = t_val
        self.c_memory["Motor_Torque"] = t_val
        self.c_memory["motor_torque_nm"] = t_val
        self.c_memory["torque"] = t_val
        self.c_memory["fault_status"] = fault


class MatlabSILPlatform(TestPlatform):
    """SIL Platform Adapter implementing TestPlatform contract with C DLL & Virtual C-Runtime."""

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
        self.task_period_ms: float = self.backend_settings.get("task_period_ms", 10.0)

        self.dll_handle: Optional[Any] = None
        self.c_runtime: Optional[VirtualCRuntime] = None
        self.is_mocking: bool = True
        self.is_running: bool = False

    def connect(self) -> None:
        """Loads compiled SIL C-DLL or initializes Virtual C-Runtime."""
        dll_path = getattr(self.config, "model_path", None)
        if dll_path and os.path.exists(dll_path) and not self.mock_mode:
            try:
                logger.info(f"Loading compiled SIL C DLL via ctypes: {dll_path}")
                self.dll_handle = ctypes.CDLL(dll_path)

                # Initialize C runtime pointers
                if hasattr(self.dll_handle, "EV_Controller_initialize"):
                    self.dll_handle.EV_Controller_initialize()

                self.c_runtime = VirtualCRuntime(
                    max_torque_nm=self.max_torque_nm,
                    interlock_active_high=self.interlock_active_high,
                    task_period_ms=self.task_period_ms,
                )
                self.is_mocking = False
                self.is_connected = True
                return
            except Exception as e:
                logger.warning(f"Failed to load SIL DLL ({e}). Auto-switching to Virtual C-Runtime.")

        logger.info("Using Virtual C-Runtime simulation for SIL execution.")
        self.c_runtime = VirtualCRuntime(
            max_torque_nm=self.max_torque_nm,
            interlock_active_high=self.interlock_active_high,
            task_period_ms=self.task_period_ms,
        )
        self.is_mocking = True
        self.is_connected = True

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply dynamic runtime configurations."""
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config.update(config)

    def start(self) -> None:
        """Starts SIL simulation execution."""
        self.is_running = True

    def stop(self) -> None:
        """Stops SIL simulation execution."""
        self.is_running = False
        if not self.is_mocking and self.dll_handle:
            if hasattr(self.dll_handle, "EV_Controller_terminate"):
                try:
                    self.dll_handle.EV_Controller_terminate()
                except Exception:
                    pass

    def disconnect(self) -> None:
        self.stop()
        self.dll_handle = None
        self.c_runtime = None
        self.is_connected = False

    def read_signal(self, signal_name: str) -> float:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name

        if not self.is_mocking and self.dll_handle:
            try:
                if signal_name in ("Motor_Torque", "motor_torque_nm", "torque", "EV_Controller_Y.Target_Torque_Out"):
                    if hasattr(self.dll_handle, "get_output_torque"):
                        self.dll_handle.get_output_torque.restype = ctypes.c_double
                        return float(self.dll_handle.get_output_torque())
            except Exception as e:
                logger.warning(f"DLL read_signal failed for '{signal_name}' ({e}). Falling back to Virtual C-Runtime.")
                self.is_mocking = True

        if self.c_runtime:
            val = self.c_runtime.read_var(signal_name)
            if val == 0.0 and resolved != signal_name:
                val = self.c_runtime.read_var(resolved)
            return val
        return 0.0

    def write_signal(self, signal_name: str, value: float) -> None:
        resolved = self.resolve_signal(signal_name) if hasattr(self, "resolve_signal") else signal_name

        if not self.is_mocking and self.dll_handle:
            try:
                if signal_name in ("Throttle_Input", "accel_pedal_pos", "accelerator", "EV_Controller_U.Throttle_Pedal_In"):
                    if hasattr(self.dll_handle, "set_input_throttle"):
                        self.dll_handle.set_input_throttle.argtypes = [ctypes.c_double]
                        self.dll_handle.set_input_throttle(ctypes.c_double(value))
                elif signal_name in ("Brake_Interlock", "hv_interlock", "drive_enable", "EV_Controller_U.HV_Interlock_State"):
                    if hasattr(self.dll_handle, "set_input_interlock"):
                        self.dll_handle.set_input_interlock.argtypes = [ctypes.c_double]
                        self.dll_handle.set_input_interlock(ctypes.c_double(value))
            except Exception as e:
                logger.warning(f"DLL write_signal failed for '{signal_name}' ({e}). Falling back to Virtual C-Runtime.")
                self.is_mocking = True

        if self.c_runtime:
            self.c_runtime.write_var(signal_name, value)
            if resolved != signal_name:
                self.c_runtime.write_var(resolved, value)

    # Shorthand aliases for TestPlatform contract
    def read(self, signal: str) -> float:
        return self.read_signal(signal)

    def write(self, signal: str, value: float) -> None:
        self.write_signal(signal, value)

    def capture(self, signals: List[str]) -> Dict[str, List[float]]:
        """Captures snapshot of specified signals."""
        return {sig: [self.read(sig)] for sig in signals}

    def step(self, duration_ms: float) -> None:
        if not self.is_mocking and self.dll_handle:
            try:
                if hasattr(self.dll_handle, "EV_Controller_step"):
                    self.dll_handle.EV_Controller_step()
            except Exception:
                self.is_mocking = True

        if self.c_runtime:
            self.c_runtime.step(duration_ms)


# Backwards compatibility aliases
MatlabSilAdapter = MatlabSILPlatform
MatlabSILPlatformAdapter = MatlabSILPlatform
