"""MDF / Timeseries Exporter for Automotive Signal Measurements."""

from pathlib import Path
from typing import Dict, Any, List
import numpy as np


def export_to_mdf(measurement_data: Dict[str, Any], output_path: str) -> None:
    """Exports recorded timeseries signal measurement data to ASAM MDF or CSV format."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamps = measurement_data.get("timestamps", [])
    signals = measurement_data.get("signals", {})

    if path.suffix.lower() == ".mdf" or path.suffix.lower() == ".mf4":
        try:
            from asammdf import MDF, Signal
            mdf = MDF()
            sig_list = []
            for sig_name, vals in signals.items():
                sig = Signal(samples=np.array(vals), timestamps=np.array(timestamps), name=sig_name)
                sig_list.append(sig)
            mdf.append(sig_list)
            mdf.save(output_path, overwrite=True)
            return
        except ImportError:
            # Fallback to structured text export if asammdf package is not present
            path = path.with_suffix(".csv")

    # CSV / Fallback Export
    with open(path, "w", encoding="utf-8") as f:
        sig_names = list(signals.keys())
        header = ["timestamp_ms"] + sig_names
        f.write(",".join(header) + "\n")

        for idx, ts in enumerate(timestamps):
            row = [str(ts)]
            for sname in sig_names:
                vals = signals[sname]
                row.append(str(vals[idx]) if idx < len(vals) else "0.0")
            f.write(",".join(row) + "\n")
