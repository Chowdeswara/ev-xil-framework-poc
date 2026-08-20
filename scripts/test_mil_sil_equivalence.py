"""ISO 26262 Back-to-Back (B2B) Equivalence Testing: MIL vs SIL Data Comparison Engine."""

import sys
import math
import logging
from pathlib import Path

# Add src/ to python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Suppress debug/warning logs for clean terminal output
logging.getLogger("ev_xil").setLevel(logging.ERROR)

from ev_xil.config.loader import ConfigLoader, RequirementLoader
from ev_xil.adapters.mil.matlab_mil import MatlabMILPlatform
from ev_xil.adapters.sil.matlab_sil import MatlabSILPlatform
from ev_xil.core.comparator import EquivalenceComparator, assert_equivalent
from ev_xil.results.json_writer import export_to_json


def run_drive_scenario(adapter_cls, config_file: str):
    root_dir = Path(__file__).parent.parent
    config_path = root_dir / "configs" / config_file
    config = ConfigLoader.load(str(config_path))
    adapter = adapter_cls(config)

    records = []
    sim_time_ms = 0.0

    with adapter:
        adapter.start()
        adapter.write("Brake_Interlock", 1.0)
        adapter.write("Throttle_Input", 50.0)

        for step_idx in range(1, 21):
            adapter.step(10.0)
            sim_time_ms += 10.0

            if step_idx == 6:
                adapter.write("Throttle_Input", 80.0)

            t_val = adapter.read("Motor_Torque")
            v_val = adapter.read("Vehicle_Speed")

            records.append({
                "time_ms": sim_time_ms,
                "torque": t_val,
                "speed": v_val
            })

        adapter.stop()

    return records


def compare_equivalence(mil_data, sil_data, tolerance=0.5):
    print("\n==========================================================================")
    print("      ISO 26262 Back-to-Back (B2B) Equivalence Verification: MIL vs SIL")
    print("==========================================================================")
    print(" Time(ms) | MIL Torque | SIL Torque | Delta Torque | MIL Speed | SIL Speed | Delta Speed")
    print("-----------------------------------------------------------------------------------------")

    max_torque_delta = 0.0
    max_speed_delta = 0.0
    comparison_table = []
    all_equivalent = True

    for mil, sil in zip(mil_data, sil_data):
        t_ms = mil["time_ms"]
        t_mil = mil["torque"]
        t_sil = sil["torque"]
        delta_torque = abs(t_mil - t_sil)

        v_mil = mil["speed"]
        v_sil = sil["speed"]
        delta_speed = abs(v_mil - v_sil)

        if delta_torque > max_torque_delta:
            max_torque_delta = delta_torque
        if delta_speed > max_speed_delta:
            max_speed_delta = delta_speed

        is_step_eq = (delta_torque <= tolerance) and (delta_speed <= tolerance)
        if not is_step_eq:
            all_equivalent = False

        status_str = "EQUIVALENT" if is_step_eq else "MISMATCH"

        comparison_table.append({
            "time_ms": t_ms,
            "mil_torque": t_mil,
            "sil_torque": t_sil,
            "delta_torque": delta_torque,
            "mil_speed": v_mil,
            "sil_speed": v_sil,
            "delta_speed": delta_speed,
            "status": status_str
        })

        print(f"  {t_ms:6.1f}  |   {t_mil:7.1f}  |   {t_sil:7.1f}  |   {delta_torque:8.4f}   |  {v_mil:8.2f} |  {v_sil:8.2f} |   {delta_speed:8.4f}")

    print("-----------------------------------------------------------------------------------------\n")

    # Print requested ISO 26262 Equivalence Result Block
    last_mil = mil_data[-1]["speed"]
    last_sil = sil_data[-1]["speed"]

    print("==================================================")
    EquivalenceComparator.print_equivalence_result(
        signal_name="VehicleSpeed",
        ref_name="MIL",
        ref_val=last_mil,
        cand_name="SIL",
        cand_val=last_sil,
        tolerance=tolerance,
    )
    print("==================================================\n")

    return all_equivalent, comparison_table


def main():
    root_dir = Path(__file__).parent.parent
    results_dir = root_dir / "results"
    req_path = root_dir / "configs" / "requirements.yaml"
    eq_reqs = RequirementLoader.load_equivalence(str(req_path))
    speed_req = eq_reqs.get("speed")
    tolerance = speed_req.tolerance if speed_req else 0.5

    print("[Step 1] Running MIL Simulation Drive Scenario...")
    mil_data = run_drive_scenario(MatlabMILPlatform, "mil.yaml")

    print("[Step 2] Running SIL Simulation Drive Scenario...")
    sil_data = run_drive_scenario(MatlabSILPlatform, "sil.yaml")

    print("[Step 3] Executing Point-by-Point Back-to-Back Comparison...")
    is_eq, comp_table = compare_equivalence(mil_data, sil_data, tolerance=tolerance)

    summary_file = results_dir / "mil_sil_equivalence_report.json"
    export_to_json(comp_table, str(summary_file))
    print(f"Exported Equivalence Verification Report to: {summary_file}")

    assert_equivalent(mil_data[-1]["speed"], sil_data[-1]["speed"], tolerance=tolerance)


if __name__ == "__main__":
    main()
