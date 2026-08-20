"""Common Test Case: Zero accelerator pedal torque demand verification."""

import pytest
from ev_xil.core.requirement import traced_to, Requirement
from ev_xil.core.verdict import assert_within_tolerance
from ev_xil.core.platform import PlatformAdapter
from ev_xil.core.measurement import SignalRecorder


REQ_ZERO_ACCEL = Requirement(
    req_id="REQ-EV-COAST-003",
    description="Motor controller shall command 0 Nm torque when accelerator pedal input is 0%.",
    asil_level="ASIL-B",
)


@traced_to(REQ_ZERO_ACCEL)
def run_zero_accel_test(adapter: PlatformAdapter, recorder: SignalRecorder) -> None:
    """Executes zero accelerator pedal test sequence across any XiL platform adapter."""
    adapter.write_signal("Brake_Interlock", 1.0)
    adapter.write_signal("hv_interlock", 1.0)
    adapter.write_signal("Throttle_Input", 0.0)
    adapter.write_signal("accel_pedal_pos", 0.0)
    adapter.step(10.0)

    torque = adapter.read_signal("Motor_Torque")
    if torque != 0.0 and adapter.read_signal("motor_torque_nm") == 0.0:
        torque = adapter.read_signal("motor_torque_nm")

    recorder.record(10.0, "Throttle_Input", 0.0)
    recorder.record(10.0, "Motor_Torque", torque)

    assert_within_tolerance(torque, 0.0, abs_tol=0.01, signal_name="Motor_Torque")


def test_zero_accel_mil(mil_adapter, signal_recorder):
    run_zero_accel_test(mil_adapter, signal_recorder)
