"""Core module exports for ev_xil framework."""

from ev_xil.core.platform import PlatformAdapter
from ev_xil.core.requirement import Requirement, traced_to
from ev_xil.core.measurement import SignalRecorder
from ev_xil.core.verdict import (
    VerdictError,
    assert_within_tolerance,
    assert_in_range,
    assert_response_time,
)
from ev_xil.core.testcase import XiLTestCase
from ev_xil.core.runner import XiLTestRunner

__all__ = [
    "PlatformAdapter",
    "Requirement",
    "traced_to",
    "SignalRecorder",
    "VerdictError",
    "assert_within_tolerance",
    "assert_in_range",
    "assert_response_time",
    "XiLTestCase",
    "XiLTestRunner",
]
