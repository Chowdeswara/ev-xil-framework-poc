"""Custom Robot Framework Library for EV XiL (MIL, SIL, HIL, VIL) Test Automation."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

from ev_xil.config.loader import ConfigLoader, RequirementLoader
from ev_xil.adapters.mil.matlab_mil import MatlabMILPlatform
from ev_xil.adapters.sil.matlab_sil import MatlabSILPlatform
from ev_xil.adapters.hil.matlab_hil import MatlabHilAdapter
from ev_xil.adapters.vil.vehicle import VehicleAdapter
from ev_xil.core.measurement import SignalRecorder
from ev_xil.core.comparator import EquivalenceComparator, CrossLevelComparator, assert_equivalent

logger = logging.getLogger(__name__)


class EVXiLLibrary:
    """Robot Framework Custom Test Library for EV X-in-the-Loop (XiL) Automation."""

    ROBOT_LIBRARY_SCOPE = "GLOBAL"
    ROBOT_LIBRARY_VERSION = "0.1.0"

    def __init__(self) -> None:
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.configs_dir = self.root_dir / "configs"
        self.current_adapter = None
        self.current_profile = None
        self.recorder = None

    def connect_execution_profile(self, profile_name: str) -> None:
        """Connects to the specified XiL execution profile (MIL, SIL, HIL, or VIL)."""
        profile = profile_name.strip().upper()
        config_path = self.configs_dir / f"{profile.lower()}.yaml"

        if not config_path.is_file():
            raise FileNotFoundError(f"Configuration file not found for profile '{profile}': {config_path}")

        config = ConfigLoader.load(str(config_path))

        if profile == "MIL":
            self.current_adapter = MatlabMILPlatform(config)
        elif profile == "SIL":
            self.current_adapter = MatlabSILPlatform(config)
        elif profile == "HIL":
            self.current_adapter = MatlabHilAdapter(config)
        elif profile == "VIL":
            self.current_adapter = VehicleAdapter(config)
        else:
            raise ValueError(f"Unsupported XiL execution profile: {profile_name}")

        self.current_profile = profile
        self.current_adapter.connect()
        self.current_adapter.start()

        self.recorder = SignalRecorder()
        self.recorder.start()
        logger.info(f"Connected and started XiL execution profile: {self.current_profile}")

    def write_signal_input(self, signal_name: str, value: float) -> None:
        """Writes a value to a logical input signal."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected. Call 'Connect Execution Profile' first.")
        self.current_adapter.write(signal_name, float(value))

    def write_maport_signal(self, signal_name: str, value: float) -> None:
        """Writes a value to Speedgoat Plant IO MAPort on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "write_maport"):
            self.current_adapter.write_maport(signal_name, float(value))
        else:
            self.current_adapter.write(signal_name, float(value))

    def write_network_port_signal(self, signal_name: str, value: float) -> None:
        """Writes a value to CAN bus NetworkPort on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "write_network_port"):
            self.current_adapter.write_network_port(signal_name, float(value))
        else:
            self.current_adapter.write(signal_name, float(value))

    def write_ecum_port_signal(self, signal_name: str, value: float) -> None:
        """Writes a value to ECUMPort diagnostic state on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "write_ecu_port"):
            self.current_adapter.write_ecu_port(signal_name, float(value))
        else:
            self.current_adapter.write(signal_name, float(value))

    def step_simulation_time(self, duration_ms: float) -> None:
        """Steps the simulation forward by specified milliseconds."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        self.current_adapter.step(float(duration_ms))

    def read_signal_output(self, signal_name: str) -> float:
        """Reads the current value of a logical signal."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        val = float(self.current_adapter.read(signal_name))
        if self.recorder:
            self.recorder.record(self.recorder.current_time_ms, signal_name, val)
        return val

    def read_maport_signal(self, signal_name: str) -> float:
        """Reads a signal from Speedgoat MAPort on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "read_maport"):
            val = float(self.current_adapter.read_maport(signal_name))
        else:
            val = float(self.current_adapter.read(signal_name))
        return val

    def read_network_port_signal(self, signal_name: str) -> float:
        """Reads a signal from CAN bus NetworkPort on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "read_network_port"):
            val = float(self.current_adapter.read_network_port(signal_name))
        else:
            val = float(self.current_adapter.read(signal_name))
        return val

    def read_ecum_port_signal(self, signal_name: str) -> float:
        """Reads diagnostic state from ECUMPort on HIL profile."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "read_ecu_port"):
            val = float(self.current_adapter.read_ecu_port(signal_name))
        else:
            val = float(self.current_adapter.read(signal_name))
        return val

    def inject_hardware_fault(self, signal_name: str, fault_type: str, value: float = 0.0) -> None:
        """Injects hardware/communication fault (OPEN_CIRCUIT, COMM_TIMEOUT, STUCK_AT)."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "inject_fault"):
            self.current_adapter.inject_fault(signal_name, fault_type, float(value))

    def clear_hardware_faults(self) -> None:
        """Clears all active hardware/bus fault conditions."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "clear_faults"):
            self.current_adapter.clear_faults()

    def verify_signal_within_tolerance(self, actual_val: float, expected_val: float, tolerance: float = 0.5) -> None:
        """Asserts that actual signal value matches expected value within tolerance."""
        actual_val = float(actual_val)
        expected_val = float(expected_val)
        tolerance = float(tolerance)
        assert_equivalent(reference=expected_val, candidate=actual_val, tolerance=tolerance)

    def verify_signal_equivalence(self, val_a: float, val_b: float, tolerance: float = 0.5) -> None:
        """Asserts ISO 26262 Back-to-Back numerical equivalence between two values."""
        val_a = float(val_a)
        val_b = float(val_b)
        tolerance = float(tolerance)
        assert EquivalenceComparator.compare_scalar(val_a, val_b, tolerance=tolerance), (
            f"ISO 26262 Equivalence Mismatch: |{val_a} - {val_b}| > {tolerance}"
        )

    def verify_cross_level_equivalence(
        self, signal_name: str, mil_val: float, sil_val: float, hil_val: float, vil_val: float, tolerance: float = 0.5
    ) -> None:
        """Verifies multi-level cross-level equivalence across MIL, SIL, HIL, VIL."""
        results_map = {
            "MIL": float(mil_val),
            "SIL": float(sil_val),
            "HIL": float(hil_val),
            "VIL": float(vil_val),
        }
        passed, matrix = CrossLevelComparator.compare_cross_levels(results_map, tolerance=float(tolerance))
        CrossLevelComparator.print_cross_level_report(signal_name, results_map, tolerance=float(tolerance))
        assert passed, f"Cross-Level Equivalence Failed for {signal_name}: {matrix}"

    def disconnect_execution_profile(self) -> None:
        """Disconnects and stops the current execution profile."""
        if self.recorder:
            self.recorder.stop()
            self.recorder = None

        if self.current_adapter:
            self.current_adapter.stop()
            self.current_adapter.disconnect()
            self.current_adapter = None
            logger.info(f"Disconnected profile: {self.current_profile}")
            self.current_profile = None
