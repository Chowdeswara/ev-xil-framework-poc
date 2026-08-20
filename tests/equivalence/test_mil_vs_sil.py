"""Back-to-Back Equivalence Test Suite between MIL and SIL Execution Profiles."""

import pytest
from pathlib import Path
from ev_xil.config.loader import RequirementLoader
from ev_xil.core.comparator import EquivalenceComparator, assert_equivalent


@pytest.mark.equivalence
def test_mil_vs_sil_tc_ev_001_equivalence(mil_adapter, sil_adapter):
    """TC_EV_001 B2B Equivalence Test: 50% throttle acceleration demand on MIL vs SIL."""
    root_dir = Path(__file__).parent.parent.parent
    req_path = root_dir / "configs" / "requirements.yaml"
    eq_reqs = RequirementLoader.load_equivalence(str(req_path))
    speed_req = eq_reqs.get("speed")
    tolerance = speed_req.tolerance if speed_req else 0.5

    # 1. Execute TC_EV_001 stimulus on MIL adapter (Reference)
    with mil_adapter:
        mil_adapter.start()
        mil_adapter.write("Brake_Interlock", 1.0)
        mil_adapter.write("Throttle_Input", 50.0)
        mil_adapter.step(200.0)
        mil_speed = mil_adapter.read("Vehicle_Speed")
        mil_torque = mil_adapter.read("Motor_Torque")
        mil_adapter.stop()

    # 2. Execute TC_EV_001 stimulus on SIL adapter (Candidate)
    with sil_adapter:
        sil_adapter.start()
        sil_adapter.write("Brake_Interlock", 1.0)
        sil_adapter.write("Throttle_Input", 50.0)
        sil_adapter.step(200.0)
        sil_speed = sil_adapter.read("Vehicle_Speed")
        sil_torque = sil_adapter.read("Motor_Torque")
        sil_adapter.stop()

    # 3. Print formatted Equivalence Result matching spec
    print("\n")
    EquivalenceComparator.print_equivalence_result(
        signal_name="VehicleSpeed",
        ref_name="MIL",
        ref_val=mil_speed,
        cand_name="SIL",
        cand_val=sil_speed,
        tolerance=tolerance,
    )

    # 4. Assert Equivalence (|MIL_Speed - SIL_Speed| <= 0.5 km/h)
    assert_equivalent(reference=mil_speed, candidate=sil_speed, tolerance=tolerance)
