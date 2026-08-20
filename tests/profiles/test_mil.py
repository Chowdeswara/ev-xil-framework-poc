"""MIL (Model-in-the-Loop) Test Profile Execution Runner."""

import pytest
from tests.common.test_acceleration import run_acceleration_test
from tests.common.test_interlock import run_interlock_test
from tests.common.test_zero_accel import run_zero_accel_test


def test_mil_acceleration(mil_adapter, signal_recorder):
    """MIL execution profile test for 50% throttle acceleration demand."""
    actual_torque = run_acceleration_test(mil_adapter, signal_recorder)
    assert actual_torque == 175.0  # 50% of max_torque_nm (350.0)


def test_mil_interlock_shutdown(mil_adapter, signal_recorder):
    """MIL execution profile test for HV interlock trip safety shutdown."""
    run_interlock_test(mil_adapter, signal_recorder)


def test_mil_zero_throttle(mil_adapter, signal_recorder):
    """MIL execution profile test for 0% zero throttle input demand."""
    run_zero_accel_test(mil_adapter, signal_recorder)
