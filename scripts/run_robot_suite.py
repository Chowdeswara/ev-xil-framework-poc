"""Master Robot Framework Execution Script for EV XiL Test Automation."""

import sys
import os
import subprocess
from pathlib import Path

# Add src/ to python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


def get_python_executable():
    root_dir = Path(__file__).parent.parent
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def run_robot_tests():
    root_dir = Path(__file__).parent.parent
    robot_dir = root_dir / "tests" / "robot"
    output_dir = root_dir / "results" / "robot_logs"
    output_dir.mkdir(parents=True, exist_ok=True)

    py_exe = get_python_executable()

    print("==========================================================================")
    print("       EV XiL Framework — Robot Framework Automation Suite Execution")
    print("==========================================================================")

    cmd = [
        py_exe,
        "-m",
        "robot",
        "--outputdir",
        str(output_dir),
        "--name",
        "EV_XiL_Robot_Master_Suite",
        str(robot_dir),
    ]

    print(f"Executing: {' '.join(cmd)}\n")

    res = subprocess.run(cmd, text=True)

    print("==========================================================================")
    print(f"Robot Framework Execution Completed with Return Code: {res.returncode}")
    print(f"Interactive Log HTML:    {output_dir / 'log.html'}")
    print(f"Executive Report HTML:  {output_dir / 'report.html'}")
    print("==========================================================================")

    return res.returncode


if __name__ == "__main__":
    sys.exit(run_robot_tests())
