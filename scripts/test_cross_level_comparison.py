"""Cross-Level (MIL vs SIL vs HIL vs VIL) Result Comparison Engine."""

import sys
import logging
from pathlib import Path

# Add src/ to python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Suppress log noise for clean console reporting
logging.getLogger("ev_xil").setLevel(logging.ERROR)

from ev_xil.config.loader import ConfigLoader
from ev_xil.adapters.mil.matlab_mil import MatlabMILPlatform
from ev_xil.adapters.sil.matlab_sil import MatlabSILPlatform
from ev_xil.adapters.hil.matlab_hil import MatlabHilAdapter
from ev_xil.adapters.vil.vehicle import VehicleAdapter
from ev_xil.core.comparator import CrossLevelComparator
from ev_xil.results.json_writer import export_to_json


def run_tc_ev_001_on_profile(adapter_cls, config_filename: str):
    root_dir = Path(__file__).parent.parent
    config_path = root_dir / "configs" / config_filename
    config = ConfigLoader.load(str(config_path))
    adapter = adapter_cls(config)

    with adapter:
        adapter.start()
        adapter.write("Brake_Interlock", 1.0)
        adapter.write("Throttle_Input", 50.0)
        adapter.step(200.0)
        t_val = adapter.read("Motor_Torque")
        v_val = adapter.read("Vehicle_Speed")
        adapter.stop()

    return t_val, v_val


def main():
    root_dir = Path(__file__).parent.parent
    results_dir = root_dir / "results"

    print("\n[1/4] Running MIL Profile...")
    mil_trq, mil_spd = run_tc_ev_001_on_profile(MatlabMILPlatform, "mil.yaml")

    print("[2/4] Running SIL Profile...")
    sil_trq, sil_spd = run_tc_ev_001_on_profile(MatlabSILPlatform, "sil.yaml")

    print("[3/4] Running HIL Profile...")
    hil_trq, hil_spd = run_tc_ev_001_on_profile(MatlabHilAdapter, "hil.yaml")

    print("[4/4] Running VIL Profile...")
    vil_trq, vil_spd = run_tc_ev_001_on_profile(VehicleAdapter, "vil.yaml")

    torque_map = {"MIL": mil_trq, "SIL": sil_trq, "HIL": hil_trq, "VIL": vil_trq}
    speed_map = {"MIL": mil_spd, "SIL": sil_spd, "HIL": hil_spd, "VIL": vil_spd}

    CrossLevelComparator.print_cross_level_report("Motor_Torque (Nm)", torque_map, tolerance=0.5)
    CrossLevelComparator.print_cross_level_report("Vehicle_Speed (km/h)", speed_map, tolerance=0.5)

    passed_trq, trq_matrix = CrossLevelComparator.compare_cross_levels(torque_map, tolerance=0.5)
    passed_spd, spd_matrix = CrossLevelComparator.compare_cross_levels(speed_map, tolerance=0.5)

    report_payload = {
        "signal_torque": torque_map,
        "torque_comparison": trq_matrix,
        "signal_speed": speed_map,
        "speed_comparison": spd_matrix,
        "overall_verdict": "PASSED" if (passed_trq and passed_spd) else "FAILED",
    }

    report_file = results_dir / "cross_level_comparison_report.json"
    export_to_json(report_payload, str(report_file))
    print(f"Exported Cross-Level Verification Report to: {report_file}")


if __name__ == "__main__":
    main()
