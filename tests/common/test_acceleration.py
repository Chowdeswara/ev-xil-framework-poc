"""Common Test Case: Acceleration demand & motor torque response verification."""

import pytest
from ev_xil.core.requirement import traced_to, Requirement
from ev_xil.core.verdict import assert_within_tolerance, assert_in_range
from ev_xil.core.platform import PlatformAdapter
from ev_xil.core.measurement import SignalRecorder


REQ_ACCEL = Requirement(
    req_id="REQ-EV-ACCEL-001",
    description="Motor controller shall demand torque proportional to accelerator pedal input in Drive mode.",
    asil_level="ASIL-C",
)


@traced_to(REQ_ACCEL)
def run_acceleration_test(adapter: PlatformAdapter, recorder: SignalRecorder) -> float:
    """Executes acceleration test sequence across any XiL platform adapter."""
    # Active interlock & zero brake
    adapter.write_signal("Brake_Interlock", 1.0)
    adapter.write_signal("hv_interlock", 1.0)
    adapter.write_signal("gear_selector", 1.0)
    adapter.write_signal("brake_pedal_pos", 0.0)
    adapter.step(10.0)

    # 50% Throttle / Accel Pedal demand
    throttle_pct = 50.0
    adapter.write_signal("Throttle_Input", throttle_pct)
    adapter.write_signal("accel_pedal_pos", throttle_pct)
    adapter.step(20.0)

    # Read output torque (supports canonical Throttle_Input/Motor_Torque or accel_pedal_pos/motor_torque_nm)
    actual_torque = adapter.read_signal("Motor_Torque")
    if actual_torque == 0.0:
        actual_torque = adapter.read_signal("motor_torque_nm")

    recorder.record(20.0, "Throttle_Input", throttle_pct)
    recorder.record(20.0, "Motor_Torque", actual_torque)

    # Torque should be positive and proportional (e.g. 50% of 350 Nm = 175 Nm or 50% of 300 Nm = 150 Nm)
    assert actual_torque > 0.0, f"Expected positive torque output, got {actual_torque}"
    assert_in_range(actual_torque, 100.0, 350.0, signal_name="Motor_Torque")

    return actual_torque


def test_acceleration_mil(mil_adapter, signal_recorder):
    run_acceleration_test(mil_adapter, signal_recorder)
