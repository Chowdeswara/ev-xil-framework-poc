"""Base XiL TestCase Structure."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from ev_xil.core.platform import PlatformAdapter
from ev_xil.core.measurement import SignalRecorder


class XiLTestCase(ABC):
    """Base class encapsulating setup, execution, verdict evaluation, and teardown for XiL tests."""

    def __init__(self, name: str, adapter: PlatformAdapter) -> None:
        self.name: str = name
        self.adapter: PlatformAdapter = adapter
        self.recorder: SignalRecorder = SignalRecorder()
        self.passed: bool = False
        self.verdict_message: str = "NOT_EXECUTED"
        self.execution_info: Dict[str, Any] = {}

    def setup(self) -> None:
        """Pre-test setup: Connect adapter and start recorder."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        self.recorder.start()

    @abstractmethod
    def execute(self) -> None:
        """Main test sequence implementation."""
        pass

    @abstractmethod
    def evaluate_verdict(self) -> None:
        """Post-execution assertion and verdict evaluation logic."""
        pass

    def teardown(self) -> None:
        """Post-test cleanup: Stop recorder and disconnect adapter if needed."""
        self.recorder.stop()

    def run(self) -> bool:
        """Runs full test lifecycle: setup -> execute -> evaluate_verdict -> teardown."""
        try:
            self.setup()
            self.execute()
            self.evaluate_verdict()
            self.passed = True
            self.verdict_message = "PASSED"
        except Exception as e:
            self.passed = False
            self.verdict_message = f"FAILED: {str(e)}"
            raise e
        finally:
            self.teardown()
        return self.passed
