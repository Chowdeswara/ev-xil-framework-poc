"""SIL (Software-in-the-Loop) Test Profile Execution Runner."""

import pytest
from tests.common.test_acceleration import run_acceleration_test
from tests.common.test_interlock import run_interlock_test
from tests.common.test_zero_accel import run_zero_accel_test


def test_sil_acceleration(sil_adapter, signal_recorder):
    """SIL execution profile test for 50% throttle acceleration demand against virtual C-runtime."""
    actual_torque = run_acceleration_test(sil_adapter, signal_recorder)
    assert actual_torque == 175.0  # 50% of max_torque_nm (350.0) in C-code execution


def test_sil_interlock_shutdown(sil_adapter, signal_recorder):
    """SIL execution profile test for HV interlock trip safety shutdown."""
    run_interlock_test(sil_adapter, signal_recorder)


def test_sil_zero_throttle(sil_adapter, signal_recorder):
    """SIL execution profile test for 0% zero throttle input demand."""
    run_zero_accel_test(sil_adapter, signal_recorder)
