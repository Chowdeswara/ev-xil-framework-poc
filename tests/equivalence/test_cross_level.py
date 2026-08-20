"""Cross-Level Result Comparison Test Suite across MIL, SIL, HIL, and VIL Profiles."""

import pytest
from ev_xil.core.comparator import CrossLevelComparator, assert_equivalent


@pytest.mark.equivalence
def test_cross_level_tc_ev_001_comparison(mil_adapter, sil_adapter, hil_adapter, vil_adapter):
    """TC_EV_001 Cross-Level Result Comparison: 50% throttle acceleration demand across MIL, SIL, HIL, VIL."""
    torque_results = {}
    speed_results = {}

    # 1. Run MIL Profile
    with mil_adapter:
        mil_adapter.start()
        mil_adapter.write("Brake_Interlock", 1.0)
        mil_adapter.write("Throttle_Input", 50.0)
        mil_adapter.step(200.0)
        torque_results["MIL"] = mil_adapter.read("Motor_Torque")
        speed_results["MIL"] = mil_adapter.read("Vehicle_Speed")
        mil_adapter.stop()

    # 2. Run SIL Profile
    with sil_adapter:
        sil_adapter.start()
        sil_adapter.write("Brake_Interlock", 1.0)
        sil_adapter.write("Throttle_Input", 50.0)
        sil_adapter.step(200.0)
        torque_results["SIL"] = sil_adapter.read("Motor_Torque")
        speed_results["SIL"] = sil_adapter.read("Vehicle_Speed")
        sil_adapter.stop()

    # 3. Run HIL Profile
    with hil_adapter:
        hil_adapter.start()
        hil_adapter.write("Brake_Interlock", 1.0)
        hil_adapter.write("Throttle_Input", 50.0)
        hil_adapter.step(200.0)
        torque_results["HIL"] = hil_adapter.read("Motor_Torque")
        speed_results["HIL"] = hil_adapter.read("Vehicle_Speed")
        hil_adapter.stop()

    # 4. Run VIL Profile
    with vil_adapter:
        vil_adapter.start()
        vil_adapter.write("Brake_Interlock", 1.0)
        vil_adapter.write("Throttle_Input", 50.0)
        vil_adapter.step(200.0)
        torque_results["VIL"] = vil_adapter.read("Motor_Torque")
        speed_results["VIL"] = vil_adapter.read("Vehicle_Speed")
        vil_adapter.stop()

    # Print Cross-Level Summary Reports
    print("\n")
    CrossLevelComparator.print_cross_level_report("Motor_Torque (Nm)", torque_results, tolerance=0.5)
    CrossLevelComparator.print_cross_level_report("Vehicle_Speed (km/h)", speed_results, tolerance=0.5)

    # 5. Assert Cross-Level Equivalence for Motor Torque (all 175.0 Nm)
    passed_trq, trq_matrix = CrossLevelComparator.compare_cross_levels(torque_results, tolerance=0.5)
    assert passed_trq, f"Motor Torque Cross-Level Comparison Failed: {trq_matrix}"

    # 6. Assert Cross-Level Equivalence for Vehicle Speed
    passed_spd, spd_matrix = CrossLevelComparator.compare_cross_levels(speed_results, tolerance=0.5)
    assert passed_spd, f"Vehicle Speed Cross-Level Comparison Failed: {spd_matrix}"
