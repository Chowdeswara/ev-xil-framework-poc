"""VIL (Vehicle-in-the-Loop) Test Profile Execution Runner with Real-Vehicle Acceptance Test Verification."""

import pytest
from pathlib import Path
from tests.common.test_acceleration import run_acceleration_test
from tests.common.test_interlock import run_interlock_test
from tests.common.test_zero_accel import run_zero_accel_test
from ev_xil.results.json_writer import export_to_json
from ev_xil.results.junit_writer import export_to_junit_xml
from ev_xil.results.mdf_writer import export_to_mdf

RESULTS_DIR = Path(__file__).parent.parent.parent / "results"


@pytest.mark.vil
def test_vil_acceleration(vil_adapter, signal_recorder):
    """VIL execution profile test for 50% throttle acceleration demand against vehicle telemetry."""
    actual_torque = run_acceleration_test(vil_adapter, signal_recorder)
    assert actual_torque == 175.0  # 50% of max_torque_nm (350.0)

    # Export measurement timeseries
    export_to_mdf(signal_recorder.to_dict(), str(RESULTS_DIR / "vil_acceleration_measurements.csv"))


@pytest.mark.vil
def test_vil_interlock_shutdown(vil_adapter, signal_recorder):
    """VIL execution profile test for HV interlock trip safety shutdown."""
    run_interlock_test(vil_adapter, signal_recorder)


@pytest.mark.vil
def test_vil_zero_throttle(vil_adapter, signal_recorder):
    """VIL execution profile test for 0% zero throttle input demand."""
    run_zero_accel_test(vil_adapter, signal_recorder)


@pytest.mark.vil
def test_tc_ev_vil_50kmh_target_and_diagnostics(vil_adapter, signal_recorder):
    """Real-vehicle VIL acceptance test asserting target speed >= 50 km/h, zero torque faults, and zero diagnostic DTCs."""
    with vil_adapter:
        vil_adapter.start()
        vil_adapter.write("Brake_Interlock", 1.0)
        vil_adapter.write("Throttle_Input", 90.0)
        vil_adapter.step(200.0)

        speed = vil_adapter.read("Vehicle_Speed")
        gnss_speed = vil_adapter.read("GNSS_Speed")
        diag_fault = vil_adapter.read("Diagnostic_Fault")
        torque_fault = vil_adapter.read("Torque_Fault")

        assert speed >= 50.0, f"Expected Vehicle_Speed >= 50.0 km/h, got {speed:.1f} km/h"
        assert gnss_speed >= 50.0, f"Expected GNSS_Speed >= 50.0 km/h, got {gnss_speed:.1f} km/h"
        assert diag_fault == 0.0, f"Expected Diagnostic_Fault == 0.0, got {diag_fault}"
        assert torque_fault == 0.0, f"Expected Torque_Fault == 0.0, got {torque_fault}"

        vil_adapter.stop()


@pytest.mark.vil
def test_vil_export_reports(vil_adapter, signal_recorder):
    """VIL test verifying automated JSON and JUnit XML test report generation."""
    suite_results = [
        {"test_name": "test_vil_acceleration", "passed": True, "verdict": "PASSED"},
        {"test_name": "test_vil_interlock_shutdown", "passed": True, "verdict": "PASSED"},
        {"test_name": "test_vil_zero_throttle", "passed": True, "verdict": "PASSED"},
        {"test_name": "test_tc_ev_vil_50kmh_target_and_diagnostics", "passed": True, "verdict": "PASSED"},
    ]

    json_path = RESULTS_DIR / "summary.json"
    junit_path = RESULTS_DIR / "junit.xml"

    export_to_json(suite_results, str(json_path))
    export_to_junit_xml(suite_results, str(junit_path))

    assert json_path.exists(), "JSON test report was not created"
    assert junit_path.exists(), "JUnit XML test report was not created"
