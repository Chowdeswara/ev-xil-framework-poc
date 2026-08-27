"""EV XiL Simulation Engine — Core orchestrator bridging FastAPI routes to XiL platform adapters.

Responsibilities:
  - Accept a SimulationRequest from the REST API
  - Spin up the requested profile(s): MIL, SIL, HIL, VIL, or ALL
  - Run a time-stepped simulation recording torque + speed telemetry
  - Apply fault injection for HIL profile (or simulate via interlock for others)
  - Run CrossLevelComparator to build the equivalence matrix
  - Return a fully populated SimulationResponse
"""

import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from ev_xil.config.loader import ConfigLoader
from ev_xil.adapters.mil.matlab_mil import MatlabMILPlatform
from ev_xil.adapters.sil.matlab_sil import MatlabSILPlatform
from ev_xil.adapters.hil.matlab_hil import MatlabHilAdapter
from ev_xil.adapters.vil.vehicle import VehicleAdapter
from ev_xil.core.comparator import CrossLevelComparator
from ev_xil.web.models import (
    SimulationRequest,
    SimulationResponse,
    TelemetrySeries,
    EquivalenceRow,
)

logger = logging.getLogger(__name__)

# Locate configs directory relative to this file: src/ev_xil/web/ → ../../configs/
_CONFIGS_DIR = Path(__file__).parent.parent.parent.parent / "configs"

# Number of time steps per simulation run
_SIMULATION_STEPS = 20
_STEP_SIZE_MS = 10.0

# Throttle ramp-up: at step 10/20, increase throttle to simulate acceleration event
_THROTTLE_RAMP_STEP = 10

# Equivalence tolerance (km/h and Nm)
_EQUIVALENCE_TOLERANCE = 0.5

# Mapping: profile name → (adapter class, config filename)
_PROFILE_MAP = {
    "MIL": (MatlabMILPlatform, "mil.yaml"),
    "SIL": (MatlabSILPlatform, "sil.yaml"),
    "HIL": (MatlabHilAdapter, "hil.yaml"),
    "VIL": (VehicleAdapter, "vil.yaml"),
}

# Signals to apply fault injection on (used for non-HIL profiles)
_INTERLOCK_SIGNAL = "Brake_Interlock"
_THROTTLE_SIGNAL = "Throttle_Input"
_TORQUE_SIGNAL = "Motor_Torque"
_SPEED_SIGNAL = "Vehicle_Speed"
_FAULT_SIGNAL = "fault_status"
_DTC_SIGNAL = "ECU_DiagnosticStatus"


def _resolve_profiles(profile: str) -> List[str]:
    """Returns the list of profile keys to run based on request."""
    profile = profile.strip().upper()
    if profile == "ALL":
        return ["MIL", "SIL", "HIL", "VIL"]
    if profile in _PROFILE_MAP:
        return [profile]
    raise ValueError(f"Unknown profile: '{profile}'. Must be one of: ALL, MIL, SIL, HIL, VIL")


def _run_single_profile(
    profile_key: str,
    throttle_pct: float,
    interlock_state: float,
    fault_type: str,
    duration_ms: float,
    bms_temp: float = 25.0,
    bms_soc: float = 80.0,
) -> Tuple[TelemetrySeries, Dict[str, Dict[str, float]]]:
    """Runs a complete simulation for a single XiL profile and returns telemetry data.

    Args:
        profile_key: One of MIL, SIL, HIL, VIL
        throttle_pct: Initial accelerator pedal position (0–100%)
        interlock_state: HV Safety Interlock — 1.0 = CLOSED, 0.0 = OPEN
        fault_type: Fault injection type — NONE | OPEN_CIRCUIT | COMM_TIMEOUT | STUCK_AT
        duration_ms: Duration of each simulation step in ms

    Returns:
        TelemetrySeries with timestamps, torque[], speed[], final values, dtc, fault
    """
    adapter_cls, config_file = _PROFILE_MAP[profile_key]
    config_path = _CONFIGS_DIR / config_file

    if not config_path.is_file():
        logger.warning(f"Config file not found: {config_path}. Using default adapter config.")
        config = None
    else:
        config = ConfigLoader.load(str(config_path))
        # Force mock_mode=True for the API server — we never want the API to
        # attempt real MATLAB Engine or CAN hardware connections, which would
        # hang or error. The adapters' StatefulMockEngine / VirtualCRuntime /
        # ASAMXILMockPort / RealVehicleEnvironmentMock provide full-fidelity
        # simulation without external dependencies.
        if hasattr(config, "backend_settings") and isinstance(config.backend_settings, dict):
            config.backend_settings["mock_mode"] = True


    adapter = adapter_cls(config)

    timestamps: List[str] = []
    torque_series: List[float] = []
    speed_series: List[float] = []

    # Calculate step size for even distribution across duration_ms
    # We run _SIMULATION_STEPS steps, each of step_ms duration
    step_ms = max(10.0, duration_ms / _SIMULATION_STEPS)
    sim_time_ms = 0.0

    can_bus_signals: Dict[str, Dict[str, float]] = {}
    with adapter:
        adapter.start()

        # Write initial signal conditions
        adapter.write(_INTERLOCK_SIGNAL, interlock_state)
        adapter.write(_THROTTLE_SIGNAL, throttle_pct)

        # Write BMS Temperature and SOC if it's HIL and has restbus
        if profile_key == "HIL" and hasattr(adapter, "restbus") and adapter.restbus:
            adapter.restbus.set_signal("BMS", "Temperature", bms_temp)
            adapter.restbus.set_signal("BMS", "SOC", bms_soc)
            adapter.restbus.set_signal("MCU", "Actual_Torque", (throttle_pct / 100.0) * 350.0)

        # Apply fault injection for HIL adapter
        if fault_type != "NONE" and hasattr(adapter, "restbus") and adapter.restbus:
            if fault_type == "BMS_TIMEOUT":
                adapter.restbus.inject_timeout("BMS", True)
            elif fault_type == "MCU_TIMEOUT":
                adapter.restbus.inject_timeout("MCU", True)
            elif fault_type == "TCU_TIMEOUT":
                adapter.restbus.inject_timeout("TCU", True)
            elif fault_type == "BMS_CRC_FAULT":
                adapter.restbus.inject_crc_counter_fault("BMS", True)
            elif fault_type == "OPEN_CIRCUIT":
                if hasattr(adapter, "inject_fault"):
                    adapter.inject_fault("Brake_Interlock", "OPEN_CIRCUIT")
            elif fault_type == "COMM_TIMEOUT":
                if hasattr(adapter, "inject_fault"):
                    adapter.inject_fault("CAN_BUS", "COMM_TIMEOUT")
        elif fault_type != "NONE" and fault_type in ("OPEN_CIRCUIT", "COMM_TIMEOUT"):
            # For non-HIL profiles: simulate fault by forcing interlock open
            adapter.write(_INTERLOCK_SIGNAL, 0.0)
        elif fault_type == "STUCK_AT":
            adapter.write(_INTERLOCK_SIGNAL, 0.0)

        for step_idx in range(1, _SIMULATION_STEPS + 1):
            adapter.step(step_ms)
            sim_time_ms += step_ms

            # Mid-simulation throttle ramp: increase throttle at step 10 for dynamics
            if step_idx == _THROTTLE_RAMP_STEP and fault_type == "NONE" and interlock_state >= 0.5:
                ramped_throttle = min(100.0, throttle_pct * 1.4)
                adapter.write(_THROTTLE_SIGNAL, ramped_throttle)
                if profile_key == "HIL" and hasattr(adapter, "restbus") and adapter.restbus:
                    adapter.restbus.set_signal("MCU", "Actual_Torque", (ramped_throttle / 100.0) * 350.0)

            torque_val = round(adapter.read(_TORQUE_SIGNAL), 4)
            speed_val = round(adapter.read(_SPEED_SIGNAL), 4)

            timestamps.append(f"{sim_time_ms:.0f}ms")
            torque_series.append(torque_val)
            speed_series.append(speed_val)

        adapter.stop()

        # Read final state signals
        final_torque = round(adapter.read(_TORQUE_SIGNAL), 4)
        final_speed = round(adapter.read(_SPEED_SIGNAL), 4)

        # DTC and fault status — HIL has dedicated ECU diagnostic signals
        dtc_status = 0.0
        fault_status = 0.0
        if hasattr(adapter, "read_ecu_port"):
            try:
                dtc_status = adapter.read_ecu_port("ECU_DiagnosticStatus")
            except Exception:
                dtc_status = adapter.read(_DTC_SIGNAL) if _DTC_SIGNAL in getattr(
                    getattr(adapter, "mock_port", None), "signals", {}
                ) else 0.0
        else:
            dtc_status = adapter.read(_DTC_SIGNAL) if hasattr(adapter, "_signal_map") else 0.0

        fault_status = adapter.read(_FAULT_SIGNAL) if torque_series else 0.0

        # Read CAN bus signals state at final step
        if profile_key == "HIL" and hasattr(adapter, "restbus") and adapter.restbus:
            for node in ["BMS", "ABS", "Cluster", "MCU", "TCU"]:
                can_bus_signals[node] = {}
                for sig in adapter.restbus.signals[node].keys():
                    can_bus_signals[node][sig] = adapter.restbus.get_signal(node, sig)

    telemetry_series = TelemetrySeries(
        timestamps=timestamps,
        torque=torque_series,
        speed=speed_series,
        final_torque=final_torque,
        final_speed=final_speed,
        dtc_status=dtc_status,
        fault_status=fault_status,
    )
    return telemetry_series, can_bus_signals


def _build_equivalence_matrix(
    telemetry: Dict[str, TelemetrySeries],
) -> Tuple[List[EquivalenceRow], float, str]:
    """Compares final signal values across all available profiles using CrossLevelComparator.

    Returns:
        (equivalence_matrix rows, max_error_delta, overall_verdict)
    """
    available_profiles = list(telemetry.keys())
    rows: List[EquivalenceRow] = []
    global_max_delta = 0.0

    signals_to_compare = [
        ("Motor_Torque", "final_torque"),
        ("Vehicle_Speed", "final_speed"),
    ]

    for signal_name, telemetry_field in signals_to_compare:
        level_values: Dict[str, float] = {}
        for profile in ["MIL", "SIL", "HIL", "VIL"]:
            if profile in telemetry:
                level_values[profile] = getattr(telemetry[profile], telemetry_field)
            else:
                level_values[profile] = 0.0

        # CrossLevelComparator: pairwise comparison across sequential profile pairs
        all_passed, matrix = CrossLevelComparator.compare_cross_levels(
            {p: v for p, v in level_values.items() if p in available_profiles},
            tolerance=_EQUIVALENCE_TOLERANCE,
        )

        # Compute overall max delta for this signal across all pairs
        max_delta = max((item["error"] for item in matrix), default=0.0)
        global_max_delta = max(global_max_delta, max_delta)

        row = EquivalenceRow(
            signal_name=signal_name,
            MIL=level_values.get("MIL", 0.0),
            SIL=level_values.get("SIL", 0.0),
            HIL=level_values.get("HIL", 0.0),
            VIL=level_values.get("VIL", 0.0),
            delta=round(max_delta, 6),
            tolerance=_EQUIVALENCE_TOLERANCE,
            passed=all_passed,
        )
        rows.append(row)

    overall_verdict = "PASSED" if all(r.passed for r in rows) else "FAILED"
    return rows, round(global_max_delta, 6), overall_verdict


def run_simulation(request: SimulationRequest) -> SimulationResponse:
    """Main entry point: orchestrates a full XiL simulation run.

    Called by POST /api/simulate route. Runs each requested profile, collects
    telemetry, builds the equivalence matrix, and returns a SimulationResponse.

    Args:
        request: SimulationRequest from the FastAPI route

    Returns:
        SimulationResponse with telemetry, equivalence matrix, and verdict
    """
    try:
        profiles = _resolve_profiles(request.profile)
    except ValueError as e:
        return SimulationResponse(
            success=False,
            inputs=request,
            telemetry={},
            equivalence_matrix=[],
            verdict="ERROR",
            max_error_delta=0.0,
            error_message=str(e),
        )

    telemetry: Dict[str, TelemetrySeries] = {}
    can_bus_signals: Dict[str, Dict[str, float]] = {}

    for profile_key in profiles:
        logger.info(f"[SimulationEngine] Running {profile_key} profile simulation...")
        try:
            result, can_signals = _run_single_profile(
                profile_key=profile_key,
                throttle_pct=request.throttle_pct,
                interlock_state=request.interlock_state,
                fault_type=request.fault_type,
                duration_ms=request.duration_ms,
                bms_temp=request.bms_temp,
                bms_soc=request.bms_soc,
            )
            telemetry[profile_key] = result
            if profile_key == "HIL":
                can_bus_signals = can_signals
            logger.info(
                f"[SimulationEngine] {profile_key} complete — "
                f"final_torque={result.final_torque:.2f} Nm, "
                f"final_speed={result.final_speed:.2f} km/h, "
                f"fault={result.fault_status}"
            )
        except Exception as exc:
            logger.error(f"[SimulationEngine] {profile_key} profile failed: {exc}", exc_info=True)
            # Continue other profiles even if one fails; fill with zeros
            telemetry[profile_key] = TelemetrySeries(
                timestamps=[f"{i*10}ms" for i in range(1, _SIMULATION_STEPS + 1)],
                torque=[0.0] * _SIMULATION_STEPS,
                speed=[0.0] * _SIMULATION_STEPS,
                final_torque=0.0,
                final_speed=0.0,
                dtc_status=0.0,
                fault_status=1.0,
            )

    # Build equivalence matrix only when multiple profiles were run
    if len(telemetry) >= 2:
        equivalence_matrix, max_error_delta, verdict = _build_equivalence_matrix(telemetry)
    else:
        # Single profile — no cross-level comparison possible
        single_profile = next(iter(telemetry.values()))
        equivalence_matrix = [
            EquivalenceRow(
                signal_name="Motor_Torque",
                MIL=single_profile.final_torque if "MIL" in telemetry else 0.0,
                SIL=single_profile.final_torque if "SIL" in telemetry else 0.0,
                HIL=single_profile.final_torque if "HIL" in telemetry else 0.0,
                VIL=single_profile.final_torque if "VIL" in telemetry else 0.0,
                delta=0.0,
                tolerance=_EQUIVALENCE_TOLERANCE,
                passed=True,
            ),
            EquivalenceRow(
                signal_name="Vehicle_Speed",
                MIL=single_profile.final_speed if "MIL" in telemetry else 0.0,
                SIL=single_profile.final_speed if "SIL" in telemetry else 0.0,
                HIL=single_profile.final_speed if "HIL" in telemetry else 0.0,
                VIL=single_profile.final_speed if "VIL" in telemetry else 0.0,
                delta=0.0,
                tolerance=_EQUIVALENCE_TOLERANCE,
                passed=True,
            ),
        ]
        max_error_delta = 0.0

    # Extract diagnostic states from HIL or any profile
    hil_result = telemetry.get("HIL") or next(iter(telemetry.values()))
    dtc_status = hil_result.dtc_status
    fault_active = (hil_result.fault_status >= 0.5) or (dtc_status != 0.0)
    verdict = "PASSED" if not fault_active else "FAILED"

    return SimulationResponse(
        success=True,
        inputs=request,
        telemetry=telemetry,
        equivalence_matrix=equivalence_matrix,
        verdict=verdict,
        max_error_delta=max_error_delta,
        dtc_status=dtc_status,
        fault_active=fault_active,
        can_bus_signals=can_bus_signals,
    )
