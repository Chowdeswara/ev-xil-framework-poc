"""XiL Test Runner Engine."""

from typing import List, Dict, Any
from ev_xil.core.testcase import XiLTestCase


class XiLTestRunner:
    """Test runner for executing collections of XiL test cases."""

    def __init__(self) -> None:
        self.results: List[Dict[str, Any]] = []

    def run_test(self, test_case: XiLTestCase) -> bool:
        """Executes a single XiLTestCase and logs execution details."""
        success = False
        error_msg = None
        try:
            success = test_case.run()
        except Exception as exc:
            error_msg = str(exc)

        record = {
            "test_name": test_case.name,
            "passed": success,
            "verdict": test_case.verdict_message,
            "error": error_msg,
            "measurement": test_case.recorder.to_dict(),
        }
        self.results.append(record)
        return success

    def run_suite(self, test_cases: List[XiLTestCase]) -> bool:
        """Executes a list of XiLTestCases. Returns True if all passed."""
        all_passed = True
        for tc in test_cases:
            passed = self.run_test(tc)
            if not passed:
                all_passed = False
        return all_passed
