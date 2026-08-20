*** Settings ***
Documentation     MIL (Model-in-the-Loop) Execution Profile Robot Framework Suite.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

Test Setup        Connect Execution Profile    MIL
Test Teardown     Disconnect Execution Profile

*** Test Cases ***
TC-MIL-001 Verify 50% Throttle Acceleration Demand
    [Documentation]    Verifies motor torque response (175.0 Nm) under 50% pedal acceleration demand.
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${torque}=    Read Signal Output    Motor_Torque
    ${speed}=     Read Signal Output    Vehicle_Speed
    Verify Signal Within Tolerance    ${torque}    175.0    0.5

TC-MIL-002 Verify HV Interlock Safety Shutdown
    [Documentation]    Verifies torque is immediately cut to 0.0 Nm when HV interlock is tripped.
    Write Signal Input    Throttle_Input     80.0
    Write Signal Input    Brake_Interlock    0.0
    Step Simulation Time  10.0
    ${torque}=    Read Signal Output    Motor_Torque
    Verify Signal Within Tolerance    ${torque}    0.0    0.1

TC-MIL-003 Verify Zero Throttle Coasting
    [Documentation]    Verifies zero torque output when pedal input is at 0%.
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     0.0
    Step Simulation Time  10.0
    ${torque}=    Read Signal Output    Motor_Torque
    Verify Signal Within Tolerance    ${torque}    0.0    0.1
