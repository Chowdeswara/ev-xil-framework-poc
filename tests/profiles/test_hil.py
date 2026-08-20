"""HIL (Hardware-in-the-Loop) Test Profile Execution Runner with ASAM XIL MAPort & Fault Injection Verification."""

import pytest
from tests.common.test_acceleration import run_acceleration_test
from tests.common.test_interlock import run_interlock_test
from tests.common.test_zero_accel import run_zero_accel_test
from ev_xil.core.verdict import assert_within_tolerance
from ev_xil.core.requirement import traced_to, Requirement


REQ_FAULT_INJECTION = Requirement(
    req_id="REQ-EV-SAFETY-004",
    description="HIL electrical fault injection (OPEN_CIRCUIT) on safety interlock shall force zero torque output.",
    asil_level="ASIL-D",
)

REQ_CAN_TIMEOUT = Requirement(
    req_id="REQ-EV-SAFETY-005",
    description="HIL CAN bus communication timeout fault (COMM_TIMEOUT) shall force immediate safe torque shutdown.",
    asil_level="ASIL-D",
)


@pytest.mark.hil
def test_hil_acceleration(hil_adapter, signal_recorder):
    """HIL execution profile test for 50% throttle acceleration demand across CAN bus."""
    actual_torque = run_acceleration_test(hil_adapter, signal_recorder)
    assert actual_torque == 175.0  # 50% of max_torque_nm (350.0)


@pytest.mark.hil
def test_hil_interlock_shutdown(hil_adapter, signal_recorder):
    """HIL execution profile test for HV interlock trip safety shutdown."""
    run_interlock_test(hil_adapter, signal_recorder)


@pytest.mark.hil
def test_hil_zero_throttle(hil_adapter, signal_recorder):
    """HIL execution profile test for 0% zero throttle input demand."""
    run_zero_accel_test(hil_adapter, signal_recorder)


@pytest.mark.hil
def test_tc_ev_001_hil_acceleration(hil_adapter, signal_recorder):
    """TC_EV_001 HIL Multi-Port Acceleration Test across MAPort and NetworkPort (CAN)."""
    with hil_adapter:
        hil_adapter.start()
        # Set plant inputs via MAPort
        hil_adapter.write_maport("Throttle_Input", 80.0)
        hil_adapter.write_maport("Brake_Interlock", 1.0)
        hil_adapter.step(200.0)

        # Read feedback via NetworkPort (CAN)
        trq_can = hil_adapter.read_network_port("TorqueRequest_CAN")
        spd_can = hil_adapter.read_network_port("VehicleSpeed_CAN")
        ecu_st = hil_adapter.read_ecu_port("ECU_State")

        assert trq_can == 280.0, f"Expected 280.0 Nm on TorqueRequest_CAN, got {trq_can}"
        assert spd_can >= 40.0, f"Expected >= 40.0 km/h on VehicleSpeed_CAN, got {spd_can}"
        assert ecu_st == 1.0, f"Expected ECU_State == 1.0 (RUNNING), got {ecu_st}"
        hil_adapter.stop()


@pytest.mark.hil
def test_tc_ev_002_hil_interlock_diagnostic(hil_adapter, signal_recorder):
    """TC_EV_002 HIL Multi-Port Safety Interlock Trip & Diagnostic DTC Test across ECUMPort."""
    with hil_adapter:
        hil_adapter.start()
        hil_adapter.write_maport("Throttle_Input", 80.0)
        hil_adapter.write_maport("Brake_Interlock", 1.0)
        hil_adapter.step(10.0)

        # Inject electrical OPEN_CIRCUIT fault on HV Interlock pin
        hil_adapter.inject_fault("Brake_Interlock", "OPEN_CIRCUIT")
        hil_adapter.step(10.0)

        trq_can = hil_adapter.read_network_port("TorqueRequest_CAN")
        ecu_st = hil_adapter.read_ecu_port("ECU_State")
        dtc = hil_adapter.read_ecu_port("ECU_DiagnosticStatus")

        assert trq_can == 0.0, f"Expected 0.0 Nm on interlock trip, got {trq_can}"
        assert ecu_st == 0.0, f"Expected ECU_State == 0.0 (SHUTDOWN), got {ecu_st}"
        assert dtc == 53249.0, f"Expected DTC 0xD001 (53249.0) registered, got {dtc}"

        hil_adapter.clear_faults()
        hil_adapter.stop()


@pytest.mark.hil
@traced_to(REQ_FAULT_INJECTION)
def test_hil_fault_injection_open_circuit(hil_adapter, signal_recorder):
    """HIL electrical fault injection test verifying OPEN_CIRCUIT on interlock safety response."""
    # Step 1: Normal 80% throttle demand
    hil_adapter.write("Brake_Interlock", 1.0)
    hil_adapter.write("Throttle_Input", 80.0)
    hil_adapter.step(10.0)

    initial_torque = hil_adapter.read("Motor_Torque")
    assert initial_torque == 280.0  # 80% of 350 Nm

    # Step 2: Inject OPEN_CIRCUIT fault on Brake_Interlock channel
    hil_adapter.inject_fault("Brake_Interlock", "OPEN_CIRCUIT")
    hil_adapter.step(10.0)

    fault_torque = hil_adapter.read("Motor_Torque")
    signal_recorder.record(20.0, "Motor_Torque_Fault", fault_torque)

    # Verify zero torque output under injected open circuit fault
    assert_within_tolerance(fault_torque, 0.0, abs_tol=0.01, signal_name="Motor_Torque_Fault")

    # Cleanup
    hil_adapter.clear_faults()


@pytest.mark.hil
@traced_to(REQ_CAN_TIMEOUT)
def test_hil_can_timeout_fault(hil_adapter, signal_recorder):
    """HIL CAN bus communication timeout fault test verifying safe shutdown when CAN heartbeat is lost."""
    # Step 1: Normal 80% throttle demand over CAN bus
    hil_adapter.write("Brake_Interlock", 1.0)
    hil_adapter.write("Throttle_Input", 80.0)
    hil_adapter.step(10.0)

    initial_torque = hil_adapter.read("Motor_Torque")
    assert initial_torque == 280.0

    # Step 2: Inject COMM_TIMEOUT fault (simulating lost CAN heartbeat / cable disconnect)
    hil_adapter.inject_fault("CAN_BUS", "COMM_TIMEOUT")
    hil_adapter.step(10.0)

    timeout_torque = hil_adapter.read("Motor_Torque")
    fault_status = hil_adapter.read("fault_status")

    # Verify immediate safe shutdown: Motor Torque dropped to 0.0 Nm & fault_status == 1.0
    assert_within_tolerance(timeout_torque, 0.0, abs_tol=0.01, signal_name="Motor_Torque_CommTimeout")
    assert fault_status == 1.0, f"Expected fault_status == 1.0 on COMM_TIMEOUT, got {fault_status}"

    # Cleanup
    hil_adapter.clear_faults()
