"""Signal Measurement and Timeseries Recorder."""

from typing import Dict, List, Any, Optional
import time


class SignalRecorder:
    """Records timeseries signal data (timestamps and float values) during test execution."""

    def __init__(self) -> None:
        self.is_recording: bool = False
        self.timestamps: List[float] = []
        self.signals: Dict[str, List[float]] = {}
        self._start_time: float = 0.0

    def start(self) -> None:
        """Starts timeseries recording and resets buffers."""
        self.clear()
        self.is_recording = True
        self._start_time = time.time()

    def stop(self) -> None:
        """Stops recording."""
        self.is_recording = False

    def record(self, timestamp: float, signal_name: str, value: float) -> None:
        """Records a single signal value at a given timestamp (ms or s)."""
        if not self.is_recording:
            return

        if timestamp not in self.timestamps:
            self.timestamps.append(timestamp)

        if signal_name not in self.signals:
            self.signals[signal_name] = []
        self.signals[signal_name].append(float(value))

    def record_sample(self, timestamp: float, sample_dict: Dict[str, float]) -> None:
        """Records multiple signal values at a single timestamp."""
        if not self.is_recording:
            return

        self.timestamps.append(float(timestamp))
        for sig_name, val in sample_dict.items():
            if sig_name not in self.signals:
                self.signals[sig_name] = []
            self.signals[sig_name].append(float(val))

    def get_signal_trace(self, signal_name: str) -> List[float]:
        """Returns recorded float series for a given signal."""
        return self.signals.get(signal_name, [])

    def get_timestamps(self) -> List[float]:
        """Returns recorded timestamps."""
        return self.timestamps

    def clear(self) -> None:
        """Clears all recorded data."""
        self.timestamps.clear()
        self.signals.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Exports recorded measurement data into a dictionary structure."""
        return {
            "timestamps": self.timestamps,
            "signals": {sig: list(vals) for sig, vals in self.signals.items()},
            "signal_count": len(self.signals),
            "sample_count": len(self.timestamps),
        }
