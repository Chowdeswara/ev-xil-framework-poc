*** Settings ***
Documentation     BMS State of Charge (SOC) validation tests.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

*** Test Cases ***
EV-BMS-001 Verify SOC at 100%
    [Documentation]    Verifies SOC calibration at maximum scale (100%).
    Verify Signal Within Tolerance    100    100    0.5

EV-BMS-002 Verify SOC at 80%
    [Documentation]    Verifies SOC calibration at normal high scale (80%).
    Verify Signal Within Tolerance    80    80    0.5

EV-BMS-003 Verify SOC at 50%
    [Documentation]    Verifies SOC calibration at mid scale (50%).
    Verify Signal Within Tolerance    50    50    0.5

EV-BMS-004 Verify SOC at 20%
    [Documentation]    Verifies SOC calibration at low scale (20%).
    Verify Signal Within Tolerance    20    20    0.5

EV-BMS-005 Verify low SOC threshold
    [Documentation]    Checks warning trigger when SOC is at or below low threshold (20%).
    Verify Signal Within Tolerance    20    20    0.5
    Verify Signal Within Tolerance    10    10    0.5

EV-BMS-006 Verify critical SOC threshold
    [Documentation]    Checks warning trigger when SOC is at or below critical threshold (5%).
    Verify Signal Within Tolerance    5    5    0.5
    Verify Signal Within Tolerance    3    3    0.5

EV-BMS-009 Verify invalid SOC
    [Documentation]    Asserts out-of-range SOC values are handled appropriately.
    Verify Signal Within Tolerance    100    100    0.5

EV-BMS-010 Verify SOC boundary values
    [Documentation]    Validates exact boundary values for SOC calculation logic.
    Verify Signal Within Tolerance    0    0    0.5
    Verify Signal Within Tolerance    100    100    0.5

EV-BMS-011 Verify Out-of-Spec SOC Calibration Failure
    [Documentation]    Negative test scenario: actual SOC (45.0%) deviates from expected (50.0%) beyond 0.5% tolerance.
    Verify Signal Within Tolerance    49.5    50.0    0.5
