*** Settings ***
Documentation     SIL (Software-in-the-Loop) Production C-Code Robot Framework Suite.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

Test Setup        Connect Execution Profile    SIL
Test Teardown     Disconnect Execution Profile

*** Test Cases ***
TC-SIL-001 Verify Production C-Code 50% Throttle Acceleration Demand
    [Documentation]    Verifies C-code execution (.dll / .exe) returns 175.0 Nm torque under 50% pedal demand.
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${torque}=    Read Signal Output    Motor_Torque
    ${speed}=     Read Signal Output    Vehicle_Speed
    Verify Signal Within Tolerance    ${torque}    175.0    0.5

TC-SIL-002 Verify Production C-Code Interlock Safety Shutdown
    [Documentation]    Verifies C-code cuts torque to 0.0 Nm when HV interlock is tripped.
    Write Signal Input    Throttle_Input     80.0
    Write Signal Input    Brake_Interlock    0.0
    Step Simulation Time  10.0
    ${torque}=    Read Signal Output    Motor_Torque
    Verify Signal Within Tolerance    ${torque}    0.0    0.1

TC-SIL-003 Verify Production C-Code Zero Throttle Demand
    [Documentation]    Verifies zero torque output when pedal input is at 0%.
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     0.0
    Step Simulation Time  10.0
    ${torque}=    Read Signal Output    Motor_Torque
    Verify Signal Within Tolerance    ${torque}    0.0    0.1
