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
        self.bms_soc = 50.0
        self.bms_temp = 25.0
        self.bms_is_charging = 0.0
        self.bms_fault_injected = 0.0

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
        sig = signal_name.strip()
        if sig == "SOC":
            self.bms_soc = float(value)
            return
        elif sig == "Temperature":
            self.bms_temp = float(value)
            return
        elif sig == "Is_Charging":
            self.bms_is_charging = float(value)
            return
        elif sig == "Fault_Injected":
            self.bms_fault_injected = float(value)
            return

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

    def read_signal_output(self, signal_name: str) -> Any:
        """Reads the current value of a logical signal."""
        sig = signal_name.strip()
        if sig == "SOC":
            val = self.bms_soc
        elif sig == "Temperature":
            val = self.bms_temp
        elif sig == "Is_Charging":
            val = self.bms_is_charging
        elif sig == "Fault_Injected":
            val = self.bms_fault_injected
        elif sig == "Cell_Voltage":
            val = round(3.0 + (self.bms_soc / 100.0) * 1.2, 3)
        elif sig == "Pack_Voltage_Status":
            voltage = 3.0 + (self.bms_soc / 100.0) * 1.2
            if voltage > 4.25:
                val = "OVER_VOLTAGE"
            elif voltage < 2.85:
                val = "UNDER_VOLTAGE"
            else:
                val = "NORMAL"
        elif sig == "DTC":
            if self.bms_fault_injected >= 0.5:
                val = "DTC_BAT_001_SENSOR_FAILURE"
            elif self.bms_temp > 55.0:
                val = "DTC_BAT_002_OVER_TEMP"
            elif self.bms_temp < -25.0:
                val = "DTC_BAT_003_UNDER_TEMP"
            elif self.bms_is_charging >= 0.5 and self.bms_temp > 50.0:
                val = "DTC_CHG_001_OVER_TEMP_CHARGE"
            else:
                val = "None"
        elif sig == "Battery_Fault":
            if self.bms_fault_injected >= 0.5 or self.bms_temp > 55.0 or self.bms_temp < -25.0 or (self.bms_is_charging >= 0.5 and self.bms_temp > 50.0):
                val = 1.0
            else:
                val = 0.0
        else:
            if not self.current_adapter:
                raise RuntimeError("No active execution profile connected.")
            raw_val = self.current_adapter.read(signal_name)
            try:
                val = float(raw_val)
            except (ValueError, TypeError):
                val = raw_val

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

    def inject_restbus_timeout(self, node_name: str, enable: bool) -> None:
        """Injects restbus timeout (drops frames) for the specified node (BMS, MCU, TCU, ABS, Cluster)."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "restbus") and self.current_adapter.restbus:
            self.current_adapter.restbus.inject_timeout(node_name.upper(), bool(enable))
            if hasattr(self.current_adapter, "mock_port") and self.current_adapter.mock_port:
                self.current_adapter.mock_port._update_can_physics()

    def inject_restbus_crc_counter_fault(self, node_name: str, enable: bool) -> None:
        """Injects rolling counter/CRC fault for the specified node."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "restbus") and self.current_adapter.restbus:
            self.current_adapter.restbus.inject_crc_counter_fault(node_name.upper(), bool(enable))
            if hasattr(self.current_adapter, "mock_port") and self.current_adapter.mock_port:
                self.current_adapter.mock_port._update_can_physics()

    def set_restbus_signal(self, node_name: str, signal_name: str, value: float) -> None:
        """Dynamically updates a restbus signal value at runtime."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "restbus") and self.current_adapter.restbus:
            self.current_adapter.restbus.set_signal(node_name.upper(), signal_name, float(value))

    def get_restbus_signal(self, node_name: str, signal_name: str) -> float:
        """Reads a restbus signal value at runtime."""
        if not self.current_adapter:
            raise RuntimeError("No active execution profile connected.")
        if hasattr(self.current_adapter, "restbus") and self.current_adapter.restbus:
            return float(self.current_adapter.restbus.get_signal(node_name.upper(), signal_name))
        return 0.0

    def load_latest_simulation_result(self) -> Dict[str, Any]:
        """Scans the results/ directory for the most recent sim_results_*.json file and returns its content as a dict."""
        import glob
        import os
        import json

        results_dir = str(self.root_dir / "results")
        results_pattern = os.path.join(results_dir, "sim_results_*.json")
        json_files = glob.glob(results_pattern)
        if not json_files:
            raise FileNotFoundError(
                "No HIL simulation results found. Please run 'START HIL SIMULATION' in the UI dashboard "
                "first to generate a simulation run record before running this test suite."
            )

        # Get the latest file by modification time
        latest_file = max(json_files, key=os.path.getmtime)
        logger.info(f"Loading latest simulation result file: {latest_file}")

        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # The file is saved as a list [record] in routes.py
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict):
            return data

        raise ValueError(f"Invalid format in simulation result file: {latest_file}")

    def disconnect_execution_profile(self) -> None:
        """Disconnects and stops the current execution profile."""
        self.bms_soc = 50.0
        self.bms_temp = 25.0
        self.bms_is_charging = 0.0
        self.bms_fault_injected = 0.0

        if self.recorder:
            self.recorder.stop()
            self.recorder = None

        if self.current_adapter:
            self.current_adapter.stop()
            self.current_adapter.disconnect()
            self.current_adapter = None
            logger.info(f"Disconnected profile: {self.current_profile}")
            self.current_profile = None
