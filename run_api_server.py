#!/usr/bin/env python
"""EV XiL API Server Startup Script.

Run this script from the project root to start the FastAPI server:

    python run_api_server.py

The server will be available at:
    API:    http://127.0.0.1:8001
    Docs:   http://127.0.0.1:8001/docs
    Health: http://127.0.0.1:8001/api/health
"""

import sys
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure src/ is on the Python path so ev_xil package is importable
# without needing 'pip install -e .' to be run in advance.
# ---------------------------------------------------------------------------
_ROOT_DIR = Path(__file__).parent.resolve()
_SRC_DIR = _ROOT_DIR / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))


def main():
    try:
        import uvicorn
    except ImportError:
        print(
            "\n[ERROR] uvicorn is not installed.\n"
            "Install it with:\n\n"
            "    pip install fastapi uvicorn[standard]\n\n"
            "Or install all requirements:\n\n"
            "    pip install -r requirements.txt\n"
        )
        sys.exit(1)

    print("=" * 70)
    print("  [EV XiL] Test Automation API Server")
    print("=" * 70)
    print(f"  Root dir : {_ROOT_DIR}")
    print(f"  Src path : {_SRC_DIR}")
    print(f"  API URL  : http://127.0.0.1:8001")
    print(f"  Docs     : http://127.0.0.1:8001/docs")
    print(f"  Health   : http://127.0.0.1:8001/api/health")
    print("=" * 70)
    print()

    uvicorn.run(
        "ev_xil.web.app:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=[str(_SRC_DIR)],
        log_level="info",
    )


if __name__ == "__main__":
    main()
