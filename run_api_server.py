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

    # Dynamically bind host and port from environment variables for cloud deployments (like Render)
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8001))
    
    # Disable reload in production to optimize container resources
    is_prod = os.environ.get("RENDER") is not None
    reload_enabled = not is_prod

    print("=" * 70)
    print("  [EV XiL] Test Automation API Server")
    print("=" * 70)
    print(f"  Root dir : {_ROOT_DIR}")
    print(f"  Src path : {_SRC_DIR}")
    print(f"  API URL  : http://{host}:{port}")
    print(f"  Docs     : http://{host}:{port}/docs")
    print(f"  Health   : http://{host}:{port}/api/health")
    print("=" * 70)
    print()

    uvicorn.run(
        "ev_xil.web.app:app",
        host=host,
        port=port,
        reload=reload_enabled,
        reload_dirs=[str(_SRC_DIR)] if reload_enabled else None,
        log_level="info",
    )


if __name__ == "__main__":
    main()
