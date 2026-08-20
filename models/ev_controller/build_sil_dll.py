"""Compiles ev_controller_sil.c into build/ev_controller_sil.dll for SIL testing."""

import os
import sys
import glob
import subprocess
from pathlib import Path


def find_gcc_compiler():
    """Searches system PATH and common MATLAB MinGW installation directories for gcc.exe."""
    # 1. Check system PATH first
    try:
        res = subprocess.run(["gcc", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0:
            return "gcc"
    except FileNotFoundError:
        pass

    # 2. Search MATLAB Support Packages for MinGW gcc.exe
    possible_patterns = [
        r"C:\ProgramData\MATLAB\SupportPackages\*\32bit\minGW*\bin\gcc.exe",
        r"C:\ProgramData\MATLAB\SupportPackages\*\bin\gcc.exe",
        r"C:\ProgramData\mathworks\supportpackages\*\bin\gcc.exe",
        r"C:\mingw64\bin\gcc.exe",
        r"C:\msys64\mingw64\bin\gcc.exe",
    ]

    for pattern in possible_patterns:
        matches = glob.glob(pattern)
        if matches and os.path.exists(matches[0]):
            return matches[0]

    return None


def compile_sil_dll():
    root_dir = Path(__file__).parent.parent.parent
    c_source = root_dir / "models" / "ev_controller" / "ev_controller_sil.c"
    build_dir = root_dir / "build"
    build_dir.mkdir(exist_ok=True)
    output_dll = build_dir / "ev_controller_sil.dll"

    print(f"Building SIL Shared Library DLL from: {c_source}")

    gcc_path = find_gcc_compiler()
    if gcc_path:
        gcc_cmd = [gcc_path, "-shared", "-o", str(output_dll), str(c_source), "-fPIC"]
        try:
            res = subprocess.run(gcc_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode == 0 and output_dll.exists():
                print(f"Successfully compiled SIL DLL using MinGW GCC ({gcc_path}): {output_dll}")
                return str(output_dll)
            else:
                print(f"Compilation warning/error: {res.stderr}")
        except Exception as e:
            print(f"Failed to invoke compiler at {gcc_path}: {e}")

    # Check for MSVC cl compiler
    cl_cmd = ["cl", "/LD", str(c_source), f"/Fe{output_dll}"]
    try:
        res = subprocess.run(cl_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode == 0 and output_dll.exists():
            print(f"Successfully compiled SIL DLL using MSVC cl: {output_dll}")
            return str(output_dll)
    except FileNotFoundError:
        pass

    print("Note: Neither GCC nor MSVC cl compiler was found on system PATH. SIL Platform will automatically use Virtual C-Runtime fallback.")
    return None


if __name__ == "__main__":
    compile_sil_dll()
