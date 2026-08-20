"""Unified EV XiL Automation Suite Execution Script (MIL, SIL, HIL, VIL)."""

import sys
import time
from pathlib import Path

# Add src/ to python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from ev_xil.config.loader import ConfigLoader, RequirementLoader
from ev_xil.adapters.mil.matlab_mil import MatlabMILPlatform
from ev_xil.adapters.sil.matlab_sil import MatlabSILPlatform
from ev_xil.adapters.hil.matlab_hil import MatlabHilAdapter
from ev_xil.adapters.vil.vehicle import VehicleAdapter
from ev_xil.core.measurement import SignalRecorder
from ev_xil.results.json_writer import export_to_json
from ev_xil.results.junit_writer import export_to_junit_xml
from ev_xil.results.mdf_writer import export_to_mdf


def run_profile(profile_name: str, adapter_cls, config_file: str, req_map: dict):
    root_dir = Path(__file__).parent.parent
    config_path = root_dir / "configs" / config_file
    config = ConfigLoader.load(str(config_path))

    adapter = adapter_cls(config)
    recorder = SignalRecorder()

    recorder.start()
    with adapter:
        adapter.start()

        # Step 1: Nominal Throttle
        adapter.write("Brake_Interlock", 1.0)
        adapter.write("Throttle_Input", 50.0)
        adapter.step(100.0)

        torque_50 = adapter.read("Motor_Torque")
        speed_50 = adapter.read("Vehicle_Speed")
        recorder.record(100.0, "Motor_Torque", torque_50)
        recorder.record(100.0, "Vehicle_Speed", speed_50)

        # Step 2: High Throttle
        adapter.write("Throttle_Input", 80.0)
        adapter.step(100.0)

        torque_80 = adapter.read("Motor_Torque")
        speed_80 = adapter.read("Vehicle_Speed")
        recorder.record(200.0, "Motor_Torque", torque_80)
        recorder.record(200.0, "Vehicle_Speed", speed_80)

        adapter.stop()

    recorder.stop()

    accel_req = req_map.get("acceleration")
    accel_passed = True
    if accel_req:
        accel_passed = accel_req.evaluate(speed_80)

    verdict = "PASSED" if (torque_50 == 175.0 and torque_80 == 280.0 and accel_passed) else "FAILED"

    return {
        "profile": profile_name,
        "test_name": f"TC_EV_001_{profile_name.upper()}_Acceleration",
        "passed": verdict == "PASSED",
        "verdict": verdict,
        "torque_50pct": torque_50,
        "torque_80pct": torque_80,
        "final_speed": speed_80,
        "recorder": recorder,
    }


def main():
    root_dir = Path(__file__).parent.parent
    req_file = root_dir / "configs" / "requirements.yaml"
    results_dir = root_dir / "results"
    results_dir.mkdir(exist_ok=True)

    req_map = RequirementLoader.load(str(req_file))

    print("==========================================================================")
    print("      EV XiL Framework: Unified Master Suite (MIL -> SIL -> HIL -> VIL)")
    print("==========================================================================")

    profiles = [
        ("MIL", MatlabMILPlatform, "mil.yaml"),
        ("SIL", MatlabSILPlatform, "sil.yaml"),
        ("HIL", MatlabHilAdapter, "hil.yaml"),
        ("VIL", VehicleAdapter, "vil.yaml"),
    ]

    suite_results = []
    print(f" Profile | Test Status | Torque (50%) | Torque (80%) | Speed (km/h) | Verdict")
    print("--------------------------------------------------------------------------")

    for profile_name, adapter_cls, cfg_name in profiles:
        res = run_profile(profile_name, adapter_cls, cfg_name, req_map)
        suite_results.append(res)

        print(
            f" {res['profile']:7} | Executed    | {res['torque_50pct']:10.1f} Nm | "
            f"{res['torque_80pct']:10.1f} Nm | {res['final_speed']:10.1f}   | {res['verdict']}"
        )

        # Export individual MDF/CSV measurement file
        mdf_path = results_dir / f"{profile_name.lower()}_suite_measurements.csv"
        export_to_mdf(res["recorder"].to_dict(), str(mdf_path))

    print("--------------------------------------------------------------------------")

    # Export Suite-level Summary JSON and JUnit XML
    json_summary = results_dir / "master_xil_suite_summary.json"
    junit_summary = results_dir / "master_xil_suite_junit.xml"

    serializable_results = [
        {
            "test_name": r["test_name"],
            "profile": r["profile"],
            "passed": r["passed"],
            "verdict": r["verdict"],
            "final_speed": r["final_speed"],
        }
        for r in suite_results
    ]

    export_to_json(serializable_results, str(json_summary))
    export_to_junit_xml(serializable_results, str(junit_summary))

    all_passed = all(r["passed"] for r in suite_results)
    print(f" Master XiL Suite Status: {'100% PASSED' if all_passed else 'FAILED'}")
    print(f" Summary JSON:  {json_summary}")
    print(f" JUnit XML:     {junit_summary}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
