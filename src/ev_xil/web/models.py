"""Pydantic request/response models for the EV XiL FastAPI server.

These models are designed to match the TypeScript types defined in
ev-xil-ui/src/types/index.ts exactly, ensuring type-safe full-stack contract.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class SimulationRequest(BaseModel):
    """Matches TypeScript SimulationRequest interface."""
    profile: str = Field(
        "ALL",
        description="Execution profile: ALL | MIL | SIL | HIL | VIL",
    )
    throttle_pct: float = Field(
        50.0,
        ge=0.0,
        le=100.0,
        description="Accelerator pedal position in percentage (0–100)",
    )
    interlock_state: float = Field(
        1.0,
        description="HV Safety Interlock state: 1.0 = CLOSED (SAFE), 0.0 = OPEN (TRIPPED)",
    )
    fault_type: str = Field(
        "NONE",
        description="Hardware/bus fault to inject: NONE | OPEN_CIRCUIT | COMM_TIMEOUT | STUCK_AT",
    )
    duration_ms: float = Field(
        200.0,
        ge=10.0,
        le=2000.0,
        description="Simulation step duration in milliseconds",
    )
    bms_temp: float = Field(
        25.0,
        ge=-40.0,
        le=150.0,
        description="Battery Management System temperature in °C",
    )
    bms_soc: float = Field(
        80.0,
        ge=0.0,
        le=100.0,
        description="Battery Management System State of Charge in %",
    )


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class TelemetrySeries(BaseModel):
    """Time-series signal measurements for a single XiL profile.
    Matches TypeScript TelemetrySeries interface.
    """
    timestamps: List[str] = Field(description="List of simulation timestamps (e.g. '10ms', '20ms')")
    torque: List[float] = Field(description="Motor torque values in Nm per time step")
    speed: List[float] = Field(description="Vehicle speed values in km/h per time step")
    final_torque: float = Field(description="Final torque value at end of simulation (Nm)")
    final_speed: float = Field(description="Final vehicle speed at end of simulation (km/h)")
    dtc_status: float = Field(description="Diagnostic Trouble Code status (0 = NO_DTC)")
    fault_status: float = Field(description="Active fault flag (0 = normal, 1 = fault active)")


class EquivalenceRow(BaseModel):
    """Single row in the ISO 26262 Cross-Level Equivalence Verification Matrix.
    Matches TypeScript EquivalenceRow interface.
    """
    signal_name: str = Field(description="Logical signal name (e.g. Motor_Torque, Vehicle_Speed)")
    MIL: float = Field(description="MIL profile measured value")
    SIL: float = Field(description="SIL profile measured value")
    HIL: float = Field(description="HIL profile measured value")
    VIL: float = Field(description="VIL profile measured value")
    delta: float = Field(description="Maximum absolute delta across all profile pairs")
    tolerance: float = Field(description="Allowable equivalence tolerance limit")
    passed: bool = Field(description="True if delta <= tolerance (EQUIVALENT), False otherwise")


class SimulationResponse(BaseModel):
    """Full simulation response returned to the React dashboard.
    Matches TypeScript SimulationResponse interface.
    """
    success: bool = Field(description="True if simulation completed without errors")
    inputs: SimulationRequest = Field(description="Echo of the simulation input parameters")
    telemetry: Dict[str, TelemetrySeries] = Field(
        description="Per-profile telemetry: keys are MIL, SIL, HIL, VIL"
    )
    equivalence_matrix: List[EquivalenceRow] = Field(
        description="ISO 26262 cross-level equivalence verification matrix rows"
    )
    verdict: str = Field(description="Overall suite verdict: PASSED or FAILED")
    max_error_delta: float = Field(description="Maximum cross-level delta error observed")
    error_message: Optional[str] = Field(None, description="Error details if success=False")
    dtc_status: float = Field(0.0, description="DTC code status")
    fault_active: bool = Field(False, description="Whether a fault is active")
    can_bus_signals: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Mapping of CAN nodes to their active signal values"
    )
    report_url: Optional[str] = Field(None, description="URL to the generated HTML simulation report")


class RobotRunResponse(BaseModel):
    """Robot Framework suite execution response.
    Matches TypeScript RobotRunResponse interface.
    """
    success: bool = Field(description="True if Robot suite completed with return code 0")
    return_code: int = Field(description="Process return code from robot execution")
    report_url: str = Field(description="URL to the HTML executive report")
    log_url: str = Field(description="URL to the detailed HTML log")
    stdout: str = Field(description="Combined stdout output from robot execution")


class TestResultRecord(BaseModel):
    """Single historical test result record from results/ folder."""
    test_name: str
    passed: bool
    verdict: str
    profile: Optional[str] = None
    timestamp: Optional[str] = None
    measurement: Optional[Dict[str, Any]] = None
    report_url: Optional[str] = None


class TestResultsResponse(BaseModel):
    """Response for GET /api/test-results — historical test results."""
    success: bool
    results: List[TestResultRecord]
    total: int
    passed_count: int
    failed_count: int


class HealthResponse(BaseModel):
    """Health check response for GET /api/health."""
    status: str = "ok"
    version: str = "0.1.0"
    framework: str = "ev-xil"
    profiles_available: List[str] = ["MIL", "SIL", "HIL", "VIL"]
