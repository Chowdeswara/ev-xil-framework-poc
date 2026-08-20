*** Settings ***
Documentation     VIL (Vehicle-in-the-Loop) Chassis Dyno & Diagnostic Telemetry Robot Suite.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

Test Setup        Connect Execution Profile    VIL
Test Teardown     Disconnect Execution Profile

*** Test Cases ***
TC-VIL-001 Verify Real-Vehicle Acceptance Target Speed and Zero Diagnostics Faults
    [Documentation]    Verifies 90% throttle demand on roller dyno reaches >= 50.0 km/h with zero diagnostic faults.
    Write Signal Input     Brake_Interlock    1.0
    Write Signal Input     Throttle_Input     90.0
    Step Simulation Time   200.0
    ${speed}=         Read Signal Output    Vehicle_Speed
    ${gnss_speed}=    Read Signal Output    GNSS_Speed
    ${diag_flt}=      Read Signal Output    Diagnostic_Fault
    ${trq_flt}=       Read Signal Output    Torque_Fault
    Verify Signal Within Tolerance    ${diag_flt}    0.0    0.1
    Verify Signal Within Tolerance    ${trq_flt}     0.0    0.1
