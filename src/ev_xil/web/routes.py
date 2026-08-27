"""FastAPI routes for the EV XiL REST API.

Endpoints:
  GET  /api/health             — Health check: confirms server + framework are alive
  POST /api/simulate           — Run live XiL simulation, returns telemetry + equivalence matrix
  POST /api/run-robot-suite    — Trigger Robot Framework test suite subprocess
  GET  /api/test-results       — Return latest test results from results/ JSON files
"""

import json
import logging
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse

from ev_xil.web.models import (
    SimulationRequest,
    SimulationResponse,
    RobotRunResponse,
    TestResultsResponse,
    TestResultRecord,
    HealthResponse,
)
from ev_xil.web.simulation_engine import run_simulation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Root project directory: src/ev_xil/web/ → go up 4 levels
_ROOT_DIR = Path(__file__).parent.parent.parent.parent
_RESULTS_DIR = _ROOT_DIR / "results"
_ROBOT_OUTPUT_DIR = _RESULTS_DIR / "robot_logs"
_VENV_PYTHON = _ROOT_DIR / ".venv" / "Scripts" / "python.exe"


def _get_python_executable() -> str:
    """Returns the path to the virtual environment Python if available, else sys.executable."""
    if _VENV_PYTHON.exists():
        return str(_VENV_PYTHON)
    return sys.executable


# ---------------------------------------------------------------------------
# GET /api/health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """Returns server health status and available XiL profiles.

    Used by the React dashboard to show the API connection badge.
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        framework="ev-xil",
        profiles_available=["MIL", "SIL", "HIL", "VIL"],
    )


def _generate_simulation_reports(request: SimulationRequest, response: SimulationResponse) -> str:
    """Generates a styled HTML simulation report and a cached JSON result file.

    Returns:
        The relative or absolute URL to the generated HTML report.
    """
    try:
        from datetime import datetime
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
        formatted_time = datetime.now().isoformat()

        # 1. Generate JSON result file for test aggregation
        sim_name = f"HIL Live Simulation (Throttle: {request.throttle_pct}%, Fault: {request.fault_type})"
        report_filename = f"sim_report_{timestamp_str}.html"
        report_url = f"http://127.0.0.1:8001/api/results/sim_reports/{report_filename}"

        # Get final telemetry values safely
        final_speed = 0.0
        final_torque = 0.0
        if response.telemetry:
            profile_key = "HIL" if "HIL" in response.telemetry else next(iter(response.telemetry.keys()))
            final_speed = response.telemetry[profile_key].final_speed
            final_torque = response.telemetry[profile_key].final_torque

        json_record = {
            "test_name": sim_name,
            "passed": not response.fault_active and (response.verdict == "PASSED"),
            "verdict": response.verdict,
            "profile": request.profile,
            "timestamp": formatted_time,
            "inputs": {
                "throttle_pct": request.throttle_pct,
                "interlock_state": request.interlock_state,
                "bms_temp": request.bms_temp,
                "bms_soc": request.bms_soc,
                "fault_type": request.fault_type,
                "duration_ms": request.duration_ms
            },
            "measurement": {
                "final_speed_kmh": round(final_speed, 2),
                "final_torque_nm": round(final_torque, 2),
                "dtc_status": response.dtc_status,
                "fault_active": response.fault_active,
                "max_error_delta": response.max_error_delta,
                "can_bus_signals": response.can_bus_signals,
            },
            "report_url": report_url
        }

        # Write JSON record to _RESULTS_DIR
        _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        json_filename = f"sim_results_{timestamp_str}.json"
        json_path = _RESULTS_DIR / json_filename
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([json_record], f, indent=2)

        # 2. Generate a premium styled HTML report
        reports_dir = _RESULTS_DIR / "sim_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / report_filename

        # Build equivalence rows HTML
        eq_rows_html = ""
        for row in response.equivalence_matrix:
            row_class = "pass" if row.passed else "fail"
            eq_rows_html += f"""
            <tr class="{row_class}">
                <td style="font-weight: 600;">{row.signal_name}</td>
                <td>{row.MIL:.2f}</td>
                <td>{row.SIL:.2f}</td>
                <td>{row.HIL:.2f}</td>
                <td>{row.VIL:.2f}</td>
                <td style="font-family: monospace;">{row.delta:.4f}</td>
                <td>{row.tolerance:.2f}</td>
                <td><span class="status-badge {row_class}">{"PASSED" if row.passed else "FAILED"}</span></td>
            </tr>
            """

        # Build telemetry data signals table
        telemetry_html = ""
        if response.telemetry:
            for profile, series in response.telemetry.items():
                telemetry_html += f"""
                <div class="card">
                    <h3>📊 {profile} Profile Final Telemetry</h3>
                    <table style="width: 100%;">
                        <tr><th>Metric</th><th style="text-align: right;">Value</th></tr>
                        <tr><td>Final Torque</td><td class="metric-value">{series.final_torque:.2f} Nm</td></tr>
                        <tr><td>Final Speed</td><td class="metric-value">{series.final_speed:.2f} km/h</td></tr>
                        <tr><td>DTC Status</td><td class="metric-value">{int(series.dtc_status)} ({"NO_DTC" if series.dtc_status == 0 else hex(int(series.dtc_status))})</td></tr>
                        <tr><td>Fault Status</td><td class="metric-value">{"FAULT ACTIVE" if series.fault_status > 0.5 else "NORMAL"}</td></tr>
                    </table>
                </div>
                """

        # Build HTML content
        verdict_class = "pass" if (response.verdict == "PASSED") else "fail"
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>EV XiL HIL Simulation Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;800&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-page: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --border-card: rgba(255, 255, 255, 0.08);
            --text-main: #f8fafc;
            --text-sub: #94a3b8;
            --accent-green: #10b981;
            --accent-pink: #f43f5e;
            --accent-cyan: #06b6d4;
            --radius-card: 16px;
        }}

        body {{
            background: var(--bg-page);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 40px;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 24px;
            margin-bottom: 32px;
        }}

        h1 {{
            font-size: 28px;
            font-weight: 800;
            margin: 0;
            background: linear-gradient(135deg, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .timestamp {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-sub);
            font-size: 14px;
        }}

        .verdict-banner {{
            padding: 24px;
            border-radius: var(--radius-card);
            text-align: center;
            font-size: 24px;
            font-weight: 800;
            margin-bottom: 32px;
            letter-spacing: 1px;
            border: 1px solid transparent;
        }}

        .verdict-banner.pass {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border-color: rgba(16, 185, 129, 0.25);
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.15);
        }}

        .verdict-banner.fail {{
            background: rgba(244, 63, 94, 0.1);
            color: var(--accent-pink);
            border-color: rgba(244, 63, 94, 0.25);
            box-shadow: 0 0 15px rgba(244, 63, 94, 0.15);
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 32px;
        }}

        .card {{
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-card);
            border-radius: var(--radius-card);
            padding: 24px;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }}

        .card h2, .card h3 {{
            margin-top: 0;
            font-size: 18px;
            font-weight: 700;
            border-bottom: 1px solid var(--border-card);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        th {{
            color: var(--text-sub);
            text-align: left;
            padding: 12px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid var(--border-card);
        }}

        td {{
            padding: 12px;
            font-size: 14px;
            border-bottom: 1px solid var(--border-card);
        }}

        .status-badge {{
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
        }}

        .status-badge.pass {{
            background: rgba(16, 185, 129, 0.1);
            color: var(--accent-green);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .status-badge.fail {{
            background: rgba(244, 63, 94, 0.1);
            color: var(--accent-pink);
            border: 1px solid rgba(244, 63, 94, 0.3);
        }}

        .metric-label {{
            color: var(--text-sub);
            font-weight: 500;
        }}

        .metric-value {{
            font-family: 'JetBrains Mono', monospace;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>EV XiL HIL Simulation Report</h1>
                <p style="margin: 4px 0 0 0; color: var(--text-sub);">Interactive Hardware-in-the-Loop Verification Run</p>
            </div>
            <div class="timestamp">Run Date: {formatted_time}</div>
        </header>

        <div class="verdict-banner {verdict_class}">
            OVERALL VERDICT: {response.verdict}
        </div>

        <div class="grid-2">
            <div class="card">
                <h2>📥 Input Configuration</h2>
                <table>
                    <tr><td class="metric-label">Execution Profile</td><td class="metric-value">{request.profile}</td></tr>
                    <tr><td class="metric-label">Throttle Command</td><td class="metric-value">{request.throttle_pct:.1f}%</td></tr>
                    <tr><td class="metric-label">HV Safety Interlock</td><td class="metric-value">{"CLOSED (SAFE)" if request.interlock_state == 1.0 else "OPEN (TRIPPED)"}</td></tr>
                    <tr><td class="metric-label">Fault Injected</td><td class="metric-value" style="color: {"var(--accent-pink)" if request.fault_type != "NONE" else "inherit"}">{request.fault_type}</td></tr>
                    <tr><td class="metric-label">BMS SOC</td><td class="metric-value">{request.bms_soc:.1f}%</td></tr>
                    <tr><td class="metric-label">BMS Temperature</td><td class="metric-value">{request.bms_temp:.1f}°C</td></tr>
                    <tr><td class="metric-label">Simulation Duration</td><td class="metric-value">{request.duration_ms:.1f} ms</td></tr>
                </table>
            </div>

            <div class="card">
                <h2>⚡ Simulation Verification Summary</h2>
                <table>
                    <tr><td class="metric-label">DTC Registered</td><td class="metric-value">{int(response.dtc_status)} ({"NO_DTC" if response.dtc_status == 0 else hex(int(response.dtc_status))})</td></tr>
                    <tr><td class="metric-label">Fault Active</td><td class="metric-value" style="color: {"var(--accent-pink)" if response.fault_active else "var(--accent-green)"}">{"TRUE" if response.fault_active else "FALSE"}</td></tr>
                    <tr><td class="metric-label">Max Cross-Level Delta</td><td class="metric-value">{response.max_error_delta:.4f}</td></tr>
                </table>
            </div>
        </div>

        <div class="card" style="margin-bottom: 32px;">
            <h2>📈 ISO 26262 Equivalence Verification Matrix</h2>
            <table>
                <thead>
                    <tr>
                        <th>Signal Name</th>
                        <th>MIL</th>
                        <th>SIL</th>
                        <th>HIL</th>
                        <th>VIL</th>
                        <th>Max Delta</th>
                        <th>Tolerance</th>
                        <th>Verdict</th>
                    </tr>
                </thead>
                <tbody>
                    {eq_rows_html}
                </tbody>
            </table>
        </div>

        <div class="grid-2">
            {telemetry_html}
        </div>
    </div>
</body>
</html>
"""
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        logger.info(f"Generated HTML report: {report_path}")
        return report_url

    except Exception as e:
        logger.exception(f"Failed to generate simulation reports: {e}")
        return ""


# ---------------------------------------------------------------------------
# POST /api/simulate
# ---------------------------------------------------------------------------

@router.post("/simulate", response_model=SimulationResponse, tags=["Simulation"])
def simulate(request: SimulationRequest) -> SimulationResponse:
    """Runs a live EV XiL simulation across the requested profiles.

    Accepts signal inputs (throttle, interlock, fault injection, duration) and
    returns per-profile telemetry time-series plus the ISO 26262 cross-level
    equivalence verification matrix.

    Args:
        request: SimulationRequest with profile, throttle_pct, interlock_state,
                 fault_type, and duration_ms.

    Returns:
        SimulationResponse with telemetry, equivalence_matrix, verdict, and max_error_delta.

    Raises:
        HTTPException 422: If request validation fails (handled by FastAPI automatically).
        HTTPException 500: If an unexpected server-side error occurs.
    """
    logger.info(
        f"[POST /api/simulate] profile={request.profile}, "
        f"throttle={request.throttle_pct}%, interlock={request.interlock_state}, "
        f"fault={request.fault_type}, duration={request.duration_ms}ms"
    )

    try:
        response = run_simulation(request)
        
        # Generate simulation HTML and JSON report files
        if response.success:
            report_url = _generate_simulation_reports(request, response)
            response.report_url = report_url

        logger.info(
            f"[POST /api/simulate] Completed — verdict={response.verdict}, "
            f"max_delta={response.max_error_delta}, report_url={response.report_url}"
        )
        return response
    except Exception as exc:
        logger.exception(f"[POST /api/simulate] Unexpected error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Simulation engine error: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# POST /api/run-robot-suite
# ---------------------------------------------------------------------------

def _parse_xml_to_json_report(xml_path: Path, json_path: Path, is_robot: bool) -> None:
    """Parses test XML outputs (Robot output.xml or Pytest junit-xml) and saves them as standard JSON records."""
    if not xml_path.exists():
        logger.warning(f"Test XML report not found: {xml_path}")
        return

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        records = []

        if is_robot:
            for test in root.iter("test"):
                test_name = test.get("name", "Unknown")
                status_elem = test.find("status")
                passed = False
                verdict = "UNKNOWN"
                timestamp = ""
                if status_elem is not None:
                    passed = status_elem.get("status") == "PASS"
                    verdict = "PASS" if passed else "FAIL"
                    timestamp = status_elem.get("starttime", "")

                # Infer profile from test name or tags
                profile = None
                name_upper = test_name.upper()
                for p in ["MIL", "SIL", "HIL", "VIL"]:
                    if p in name_upper:
                        profile = p
                        break
                if not profile and ("BMS" in name_upper or "SOC" in name_upper):
                    profile = "HIL"

                records.append({
                    "test_name": test_name,
                    "passed": passed,
                    "verdict": verdict,
                    "profile": profile,
                    "timestamp": timestamp,
                    "measurement": None,
                })
        else:
            for tc in root.iter("testcase"):
                test_name = tc.get("name", "Unknown")
                classname = tc.get("classname", "")
                failed = tc.find("failure") is not None or tc.find("error") is not None
                passed = not failed
                verdict = "PASS" if passed else "FAIL"

                profile = None
                name_upper = f"{test_name}_{classname}".upper()
                for p in ["MIL", "SIL", "HIL", "VIL"]:
                    if p in name_upper:
                        profile = p
                        break

                records.append({
                    "test_name": test_name,
                    "passed": passed,
                    "verdict": verdict,
                    "profile": profile,
                    "timestamp": None,
                    "measurement": None,
                })

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)
        logger.info(f"Successfully generated JSON test report: {json_path}")

    except Exception as e:
        logger.exception(f"Failed to parse XML report {xml_path}: {e}")


@router.post("/run-robot-suite", response_model=RobotRunResponse, tags=["Testing"])
def run_robot_suite() -> RobotRunResponse:
    """Triggers the Robot Framework EV XiL test suite execution as a subprocess.

    Runs robot tests from tests/robot/ directory (if it exists) or falls back
    to the pytest suite. Returns the return code, report URL, log URL, and stdout.

    Returns:
        RobotRunResponse with success status, return code, report/log URLs, and stdout.
    """
    logger.info("[POST /api/run-robot-suite] Starting Robot Framework suite execution...")

    _ROBOT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    py_exe = _get_python_executable()

    # Check if robot test directory exists, fall back to pytest
    robot_test_dir = _ROOT_DIR / "tests" / "robot"
    use_robot = robot_test_dir.is_dir() and any(robot_test_dir.glob("*.robot"))

    if use_robot:
        cmd = [
            py_exe, "-m", "robot",
            "--outputdir", str(_ROBOT_OUTPUT_DIR),
            "--name", "EV_XiL_Robot_Master_Suite",
            str(robot_test_dir),
        ]
    else:
        # Fall back: run pytest suite and generate a summary
        logger.info("[POST /api/run-robot-suite] No .robot files found, running pytest suite.")
        cmd = [
            py_exe, "-m", "pytest",
            str(_ROOT_DIR / "tests"),
            "-v",
            "--tb=short",
            "--no-header",
            f"--junit-xml={str(_RESULTS_DIR / 'pytest_results.xml')}",
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(_ROOT_DIR),
        )
        stdout_combined = (result.stdout or "") + (result.stderr or "")
        success = result.returncode == 0

        # Parse test results XML output into JSON for the UI dashboard
        if use_robot:
            _parse_xml_to_json_report(
                xml_path=_ROBOT_OUTPUT_DIR / "output.xml",
                json_path=_RESULTS_DIR / "robot_results.json",
                is_robot=True,
            )
        else:
            _parse_xml_to_json_report(
                xml_path=_RESULTS_DIR / "pytest_results.xml",
                json_path=_RESULTS_DIR / "pytest_results.json",
                is_robot=False,
            )

        report_url = ""
        log_url = ""

        if use_robot and (_ROBOT_OUTPUT_DIR / "report.html").exists():
            report_url = f"http://127.0.0.1:8001/api/results/robot_logs/report.html"
            log_url = f"http://127.0.0.1:8001/api/results/robot_logs/log.html"
        else:
            report_url = "http://127.0.0.1:8001/api/test-results"
            log_url = "http://127.0.0.1:8001/api/test-results"

        logger.info(
            f"[POST /api/run-robot-suite] Completed — return_code={result.returncode}, "
            f"success={success}"
        )

        return RobotRunResponse(
            success=success,
            return_code=result.returncode,
            report_url=report_url,
            log_url=log_url,
            stdout=stdout_combined[:5000],  # Truncate to avoid payload bloat
        )

    except subprocess.TimeoutExpired:
        logger.error("[POST /api/run-robot-suite] Execution timed out after 120s")
        return RobotRunResponse(
            success=False,
            return_code=-1,
            report_url="",
            log_url="",
            stdout="Execution timed out after 120 seconds.",
        )
    except Exception as exc:
        logger.exception(f"[POST /api/run-robot-suite] Unexpected error: {exc}")
        raise HTTPException(
            status_code=500,
            detail=f"Robot suite execution error: {str(exc)}",
        )


# ---------------------------------------------------------------------------
# GET /api/test-results
# ---------------------------------------------------------------------------

@router.get("/test-results", response_model=TestResultsResponse, tags=["Testing"])
async def get_test_results() -> TestResultsResponse:
    """Returns the latest cached test results from the results/ directory.

    Scans results/*.json files produced by previous pytest/robot runs and
    aggregates them into a structured response for the React dashboard.

    Returns:
        TestResultsResponse with all test records, counts, and pass/fail summary.
    """
    logger.info("[GET /api/test-results] Loading test results from results/ directory...")

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    all_records: list = []

    # Scan all JSON result files in results/
    json_files = list(_RESULTS_DIR.glob("*.json"))
    logger.info(f"[GET /api/test-results] Found {len(json_files)} result file(s).")

    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                for item in data:
                    record = _parse_result_record(item)
                    if record:
                        all_records.append(record)
            elif isinstance(data, dict):
                record = _parse_result_record(data)
                if record:
                    all_records.append(record)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"[GET /api/test-results] Skipping invalid result file {json_file}: {exc}")

    passed = sum(1 for r in all_records if r.passed)
    failed = len(all_records) - passed

    return TestResultsResponse(
        success=True,
        results=all_records,
        total=len(all_records),
        passed_count=passed,
        failed_count=failed,
    )


def _parse_result_record(item: dict) -> Optional[TestResultRecord]:
    """Safely parses a raw dict from a results JSON file into a TestResultRecord."""
    try:
        return TestResultRecord(
            test_name=item.get("test_name", item.get("name", "Unknown")),
            passed=bool(item.get("passed", item.get("success", False))),
            verdict=str(item.get("verdict", "UNKNOWN")),
            profile=item.get("profile"),
            timestamp=item.get("timestamp"),
            measurement=item.get("measurement"),
            report_url=item.get("report_url"),
        )
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Static file serving for Robot HTML reports
# ---------------------------------------------------------------------------

@router.get("/results/{file_path:path}", include_in_schema=False)
async def serve_result_file(file_path: str):
    """Serves static Robot Framework HTML report files."""
    full_path = _RESULTS_DIR / file_path
    if full_path.is_file():
        return FileResponse(str(full_path))
    raise HTTPException(status_code=404, detail=f"Result file not found: {file_path}")
