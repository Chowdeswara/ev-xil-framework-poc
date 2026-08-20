"""JSON Result Exporter."""

import json
from pathlib import Path
from typing import Dict, Any, List


def export_to_json(results_data: List[Dict[str, Any]], output_path: str) -> None:
    """Exports test suite execution results and measurement data to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)
