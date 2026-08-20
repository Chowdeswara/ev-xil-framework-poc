# EV XiL Test Automation Framework (`ev-xil`)

`ev-xil` is a modular, scalable automotive X-in-the-Loop (XiL) test automation framework designed for Electric Vehicle (EV) Powertrain and Motor Control Unit (MCU) software verification. It supports seamlessly running identical test suites across **MIL** (Model-in-the-Loop), **SIL** (Software-in-the-Loop), **HIL** (Hardware-in-the-Loop), and **VIL** (Vehicle-in-the-Loop) test environments.

---

## 🌟 Key Features

- **Platform Abstraction Layer (`PlatformAdapter` / `TestPlatform`)**: Standardized API for reading/writing signals and stepping simulation hardware/software across MIL/SIL/HIL/VIL profiles.
- **Logical-to-Physical Signal Mapping**: Test cases interact with standardized logical signals (`Throttle_Input`, `Brake_Interlock`, `Motor_Torque`, `Vehicle_Speed`), abstracted away from physical Simulink block paths, C structures, or CAN signals.
- **ASAM XIL 2.1 Multi-Port Architecture**: Standardized signal routing across **MAPort** (Plant IO), **NetworkPort** (CAN bus), and **ECUMPort** (Diagnostic DTCs & ECU state).
- **ISO 26262 Requirements Traceability & B2B Equivalence**: `@traced_to` decorator, `Requirement` data model, declarative `requirements.yaml`, and `EquivalenceComparator` / `CrossLevelComparator` engines.
- **Timeseries Measurement Recording**: Built-in `SignalRecorder` for logging microsecond/millisecond signal traces during test execution.
- **Automotive Verdict Assertion Engine**: Custom verdict assertions (`assert_within_tolerance`, `assert_equivalent`, `assert_response_time`).
- **Multi-Format Result Exporters**: Generates JSON test reports, JUnit XML for CI/CD integration, and MDF (ASAM Measurement Data Format) / CSV timeseries data.

---

## 📁 Repository Structure

```
ev-xil-framework/
├── pyproject.toml
├── README.md
├── configs/
│   ├── mil.yaml
│   ├── sil.yaml
│   ├── hil.yaml
│   ├── vil.yaml
│   └── requirements.yaml
├── src/
│   └── ev_xil/
│       ├── __init__.py
│       ├── core/
│       │   ├── platform.py
│       │   ├── comparator.py
│       │   ├── requirement.py
│       │   ├── measurement.py
│       │   ├── verdict.py
│       │   ├── runner.py
│       │   └── testcase.py
│       ├── adapters/
│       │   ├── mil/
│       │   │   └── matlab_mil.py
│       │   ├── sil/
│       │   │   └── matlab_sil.py
│       │   ├── hil/
│       │   │   └── matlab_hil.py
│       │   └── vil/
│       │       └── vehicle.py
│       ├── results/
│       │   ├── json_writer.py
│       │   ├── junit_writer.py
│       │   └── mdf_writer.py
│       └── config/
│           └── loader.py
├── models/
│   └── ev_controller/
│       ├── ev_controller_sil.c
│       └── build_sil_dll.py
├── scripts/
│   ├── run_full_xil_suite.py
│   ├── test_cross_level_comparison.py
│   ├── test_mil_sil_equivalence.py
│   ├── run_mil_demo.py
│   ├── run_sil_demo.py
│   ├── run_hil_demo.py
│   └── run_vil_demo.py
├── tests/
│   ├── conftest.py
│   ├── common/
│   │   ├── test_acceleration.py
│   │   ├── test_interlock.py
│   │   └── test_zero_accel.py
│   ├── equivalence/
│   │   ├── test_mil_vs_sil.py
│   │   └── test_cross_level.py
│   └── profiles/
│       ├── test_mil.py
│       ├── test_sil.py
│       ├── test_hil.py
│       └── test_vil.py
└── results/
```

---

## 🚀 Getting Started

### Installation

```bash
pip install -e .
```

### Running Tests

Run all 24 tests across default profiles using pytest:

```bash
pytest -v
```

Run tests specifically for a single execution profile or marker:

```bash
pytest -m equivalence -v
pytest -m hil -v
pytest -m vil -v
```
