"""Abstract Base Class for XiL Platform Adapters & TestPlatform Contracts."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type


class PlatformAdapter(ABC):
    """Abstract Base Class for hardware/simulation platform adapters in MIL, SIL, HIL, and VIL test environments."""

    def __init__(self, config: Optional[Any] = None) -> None:
        self.config = config
        self._signal_map: Dict[str, str] = {}
        if config and hasattr(config, "signals"):
            self._signal_map = config.signals or {}
        elif isinstance(config, dict) and "signals" in config:
            self._signal_map = config["signals"] or {}
        self.is_connected: bool = False

    def resolve_signal(self, logical_name: str) -> str:
        """Resolves a standardized logical signal name to its physical channel/block mapping."""
        return self._signal_map.get(logical_name, logical_name)

    @abstractmethod
    def connect(self) -> None:
        """Establishes connection to simulation platform or physical hardware."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Terminates connection to simulation platform or physical hardware."""
        pass

    @abstractmethod
    def read_signal(self, signal_name: str) -> float:
        """Reads the current float value of a logical or physical signal."""
        pass

    @abstractmethod
    def write_signal(self, signal_name: str, value: float) -> None:
        """Writes a float value to a logical or physical signal."""
        pass

    @abstractmethod
    def step(self, duration_ms: float) -> None:
        """Advances simulation or hardware execution by the specified duration in milliseconds."""
        pass

    def read(self, signal_name: str) -> float:
        """Shorthand alias for read_signal."""
        return self.read_signal(signal_name)

    def write(self, signal_name: str, value: float) -> None:
        """Shorthand alias for write_signal."""
        self.write_signal(signal_name, value)

    def capture(self, signals: List[str]) -> Dict[str, List[float]]:
        """Captures snapshot of specified signals."""
        return {sig: [self.read_signal(sig)] for sig in signals}

    def configure(self, config: Dict[str, Any]) -> None:
        """Applies dynamic runtime configuration."""
        if hasattr(self, "config") and isinstance(self.config, dict):
            self.config.update(config)

    def start(self) -> None:
        """Starts simulation execution."""
        pass

    def stop(self) -> None:
        """Stops simulation execution."""
        pass

    def __enter__(self: "PlatformAdapter") -> "PlatformAdapter":
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        self.disconnect()


# TestPlatform contract alias
TestPlatform = PlatformAdapter
