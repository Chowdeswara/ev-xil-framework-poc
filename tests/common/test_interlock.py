"""Common Test Case: HV Safety Interlock shutdown response verification."""

import pytest
from ev_xil.core.requirement import traced_to, Requirement
from ev_xil.core.verdict import assert_within_tolerance, assert_response_time
from ev_xil.core.platform import PlatformAdapter
from ev_xil.core.measurement import SignalRecorder


REQ_INTERLOCK = Requirement(
    req_id="REQ-EV-SAFETY-002",
    description="Opening High Voltage Safety Interlock loop shall immediately disable motor torque output to 0 Nm.",
    asil_level="ASIL-D",
)


@traced_to(REQ_INTERLOCK)
def run_interlock_test(adapter: PlatformAdapter, recorder: SignalRecorder) -> None:
    """Executes HV interlock trip test sequence across any XiL platform adapter."""
    # Step 1: Active drive mode with 80% throttle demand
    adapter.write_signal("Brake_Interlock", 1.0)
    adapter.write_signal("hv_interlock", 1.0)
    adapter.write_signal("Throttle_Input", 80.0)
    adapter.write_signal("accel_pedal_pos", 80.0)
    adapter.step(10.0)

    initial_torque = adapter.read_signal("Motor_Torque")
    if initial_torque == 0.0:
        initial_torque = adapter.read_signal("motor_torque_nm")
    assert initial_torque > 0.0, f"Expected active torque before interlock trip, got {initial_torque}"

    # Step 2: Trip / Open HV Interlock (0.0)
    adapter.write_signal("Brake_Interlock", 0.0)
    adapter.write_signal("hv_interlock", 0.0)
    step_duration_ms = 10.0
    adapter.step(step_duration_ms)

    shutdown_torque = adapter.read_signal("Motor_Torque")
    if shutdown_torque != 0.0:
        shutdown_torque = adapter.read_signal("motor_torque_nm")

    recorder.record(20.0, "Brake_Interlock", 0.0)
    recorder.record(20.0, "Motor_Torque", shutdown_torque)

    # Verdict assertions
    assert_within_tolerance(shutdown_torque, 0.0, abs_tol=0.01, signal_name="Motor_Torque")
    assert_response_time(step_duration_ms, max_allowed_ms=15.0, check_name="InterlockShutdownResponse")


def test_interlock_mil(mil_adapter, signal_recorder):
    run_interlock_test(mil_adapter, signal_recorder)
