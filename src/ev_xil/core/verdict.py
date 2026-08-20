"""Automotive Verdict Assertion Engine."""

from typing import Optional, Union


class VerdictError(AssertionError):
    """Custom exception raised when a XiL test assertion or safety check fails."""

    def __init__(self, message: str, signal_name: str = "", actual: Optional[float] = None) -> None:
        super().__init__(message)
        self.signal_name = signal_name
        self.actual = actual


def assert_within_tolerance(
    actual: float,
    expected: float,
    abs_tol: Optional[float] = None,
    rel_tol: Optional[float] = None,
    signal_name: str = "Signal",
) -> None:
    """Asserts that actual signal value is within specified absolute or relative tolerance of expected value.
    
    Raises:
        VerdictError if value is out of tolerance.
    """
    diff = abs(actual - expected)
    passed = True
    msg_parts = []

    if abs_tol is not None:
        if diff > abs_tol:
            passed = False
            msg_parts.append(f"diff {diff:.4f} > abs_tol {abs_tol}")

    if rel_tol is not None and expected != 0:
        rel_diff = diff / abs(expected)
        if rel_diff > rel_tol:
            passed = False
            msg_parts.append(f"rel_diff {rel_diff:.4f} > rel_tol {rel_tol}")

    if abs_tol is None and rel_tol is None:
        # Default exact match if neither provided
        if diff != 0:
            passed = False
            msg_parts.append(f"actual {actual} != expected {expected}")

    if not passed:
        reason = ", ".join(msg_parts)
        err_msg = (
            f"Verdict FAILED for [{signal_name}]: Actual={actual}, Expected={expected} ({reason})"
        )
        raise VerdictError(err_msg, signal_name=signal_name, actual=actual)


def assert_in_range(
    actual: float,
    min_val: float,
    max_val: float,
    signal_name: str = "Signal",
) -> None:
    """Asserts that actual signal value lies within [min_val, max_val] inclusive.
    
    Raises:
        VerdictError if value is outside min/max range.
    """
    if not (min_val <= actual <= max_val):
        err_msg = (
            f"Verdict FAILED for [{signal_name}]: Actual={actual} is outside allowed range [{min_val}, {max_val}]"
        )
        raise VerdictError(err_msg, signal_name=signal_name, actual=actual)


def assert_response_time(
    elapsed_ms: float,
    max_allowed_ms: float,
    check_name: str = "ResponseTime",
) -> None:
    """Asserts that a system response time check completed within max_allowed_ms.
    
    Raises:
        VerdictError if elapsed response time exceeds threshold.
    """
    if elapsed_ms > max_allowed_ms:
        err_msg = (
            f"Verdict FAILED for [{check_name}]: Elapsed={elapsed_ms:.2f}ms exceeded max allowed response time {max_allowed_ms:.2f}ms"
        )
        raise VerdictError(err_msg, signal_name=check_name, actual=elapsed_ms)
