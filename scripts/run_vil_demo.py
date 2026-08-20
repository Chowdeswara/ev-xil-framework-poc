"""Standalone VIL (Vehicle-in-the-Loop) Vehicle Dynamics Physics & Telemetry Demo Script."""

import sys
import time
from pathlib import Path

# Add src/ to python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from ev_xil.config.loader import ConfigLoader, RequirementLoader
from ev_xil.adapters.vil.vehicle import VehicleVilAdapter
from ev_xil.core.measurement import SignalRecorder
from ev_xil.results.json_writer import export_to_json
from ev_xil.results.mdf_writer import export_to_mdf


def main():
    root_dir = Path(__file__).parent.parent
    vil_config_path = root_dir / "configs" / "vil.yaml"
    req_config_path = root_dir / "configs" / "requirements.yaml"
    results_dir = root_dir / "results"
    results_dir.mkdir(exist_ok=True)

    print("==========================================================================")
    print("      EV XiL Framework - VIL (Vehicle-in-the-Loop) Dynamics Demo")
    print("==========================================================================")

    # 1. Load Configurations
    vil_config = ConfigLoader.load(str(vil_config_path))
    req_map = RequirementLoader.load(str(req_config_path))

    print(f"\n[Step 1] Initializing VIL Vehicle Dynamics Physics Engine...")
    print(f"         Curb Mass: {vil_config.backend_settings.get('curb_mass_kg', 1600.0)} kg")
    print(f"         Wheel Radius: {vil_config.backend_settings.get('wheel_radius_m', 0.32)} m")
    print(f"         Drag Coeff (Cd): {vil_config.backend_settings.get('drag_coefficient', 0.28)}")

    adapter = VehicleVilAdapter(vil_config)
    recorder = SignalRecorder()

    with adapter:
        adapter.start()
        recorder.start()
        print("         VIL Vehicle Physics Engine connected & Telemetry Gateway active!")

        print("\n[Step 2] Executing Full Vehicle Dynamics Road Test Simulation...")
        print("--------------------------------------------------------------------------")
        print(" Time(ms) | Throttle(%) | Interlock | Torque (Nm) | Speed (km/h) | Status")
        print("--------------------------------------------------------------------------")

        sim_time_ms = 0.0

        # Acceleration Road Test: 50% throttle demand
        adapter.write("Brake_Interlock", 1.0)
        adapter.write("Throttle_Input", 50.0)

        for step_idx in range(1, 16):
            adapter.step(10.0)
            sim_time_ms += 10.0

            t_val = adapter.read("Motor_Torque")
            v_val = adapter.read("Vehicle_Speed")
            thr_val = adapter.read("Throttle_Input")
            intl_val = adapter.read("Brake_Interlock")

            recorder.record(sim_time_ms, "Throttle_Input", thr_val)
            recorder.record(sim_time_ms, "Brake_Interlock", intl_val)
            recorder.record(sim_time_ms, "Motor_Torque", t_val)
            recorder.record(sim_time_ms, "Vehicle_Speed", v_val)

            print(f"  {sim_time_ms:6.1f}  |    {thr_val:5.1f}   |    {intl_val:3.1f}    |   {t_val:7.1f}   |   {v_val:8.1f}   | Dyno Road Sim")

        print(f"\n---> Evaluating Vehicle Powertrain Torque Response:")
        assert t_val == 175.0, f"Expected 175.0 Nm at 50% throttle, got {t_val}"
        print(f"     PASSED: Vehicle Motor Torque Demand is {t_val:.1f} Nm (50% of 350.0 Nm max)")

        # Safety Shutdown Test
        print("\n--------------------------------------------------------------------------")
        print(" [VIL ROAD EVENT] HV Interlock Safety Shutdown Triggered on Chassis Dyno!")
        print("--------------------------------------------------------------------------")

        adapter.write("Brake_Interlock", 0.0)
        adapter.step(10.0)
        sim_time_ms += 10.0

        t_val = adapter.read("Motor_Torque")
        v_val = adapter.read("Vehicle_Speed")
        thr_val = adapter.read("Throttle_Input")
        intl_val = adapter.read("Brake_Interlock")

        recorder.record(sim_time_ms, "Throttle_Input", thr_val)
        recorder.record(sim_time_ms, "Brake_Interlock", intl_val)
        recorder.record(sim_time_ms, "Motor_Torque", t_val)
        recorder.record(sim_time_ms, "Vehicle_Speed", v_val)

        print(f"  {sim_time_ms:6.1f}  |    {thr_val:5.1f}   |    {intl_val:3.1f}    |   {t_val:7.1f}   |   {v_val:8.1f}   | INTERLOCK TRIP!")

        # Evaluate Requirement EV-REQ-002
        print("\n---> Evaluating Requirement [EV-REQ-002] (HV Interlock Safety Shutdown):")
        req_interlock = req_map["drive_interlock"]
        req_interlock.evaluate(t_val)
        print(f"     PASSED: VIL Safety Shutdown triggered immediate Torque drop to {t_val:.1f} Nm (== {req_interlock.value} Nm)")

        recorder.stop()
        adapter.stop()

    # Export Summary & Measurements
    print("\n[Step 3] Exporting VIL Results & Vehicle Dynamics Telemetry...")
    summary_path = results_dir / "vil_demo_summary.json"
    csv_path = results_dir / "vil_demo_measurements.csv"

    demo_summary = [
        {"test_name": "VIL_Vehicle_Torque_Response_Test", "passed": True, "verdict": "PASSED"},
        {"test_name": "VIL_HV_Interlock_Safety_Test", "passed": True, "verdict": "PASSED", "requirement": "EV-REQ-002"}
    ]

    export_to_json(demo_summary, str(summary_path))
    export_to_mdf(recorder.to_dict(), str(csv_path))

    print(f"         Exported summary: {summary_path}")
    print(f"         Exported measurement CSV: {csv_path}")

    print("\n==========================================================================")
    print("      SUCCESS: VIL Vehicle Dynamics Physics Demo Completed 100% Passed!")
    print("==========================================================================")


if __name__ == "__main__":
    main()
