*** Settings ***
Documentation     HIL (Hardware-in-the-Loop) ASAM XIL 2.1 Multi-Port & Fault Injection Robot Suite.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

Test Setup        Connect Execution Profile    HIL
Test Teardown     Disconnect Execution Profile

*** Test Cases ***
TC-HIL-001 Verify Multi-Port MAPort to NetworkPort Acceleration Demand
    [Documentation]    Verifies 80% throttle demand across Speedgoat MAPort -> CAN NetworkPort (280.0 Nm, ECU_State RUNNING).
    Write MAPort Signal    Throttle_Input     80.0
    Write MAPort Signal    Brake_Interlock    1.0
    Step Simulation Time   200.0
    ${trq_can}=    Read NetworkPort Signal    TorqueRequest_CAN
    ${spd_can}=    Read NetworkPort Signal    VehicleSpeed_CAN
    ${ecu_st}=     Read ECUMPort Signal       ECU_State
    Verify Signal Within Tolerance    ${trq_can}    280.0    0.5
    Verify Signal Within Tolerance    ${ecu_st}     1.0      0.1

TC-HIL-002 Verify Interlock Trip Electrical Fault Injection and DTC Registration
    [Documentation]    Injects OPEN_CIRCUIT fault on MAPort HV Interlock pin and asserts DTC 0xD001 registration.
    Write MAPort Signal    Throttle_Input     80.0
    Write MAPort Signal    Brake_Interlock    1.0
    Step Simulation Time   10.0
    Inject Hardware Fault  Brake_Interlock    OPEN_CIRCUIT
    Step Simulation Time   10.0
    ${trq_can}=    Read NetworkPort Signal    TorqueRequest_CAN
    ${ecu_st}=     Read ECUMPort Signal       ECU_State
    ${dtc}=        Read ECUMPort Signal       ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${trq_can}    0.0        0.1
    Verify Signal Within Tolerance    ${ecu_st}     0.0        0.1
    Verify Signal Within Tolerance    ${dtc}        53249.0    0.1
    Clear Hardware Faults

TC-HIL-003 Verify CAN Bus Communication Timeout Fault Shutdown
    [Documentation]    Injects COMM_TIMEOUT fault simulating lost CAN heartbeat cable disconnect.
    Write MAPort Signal    Throttle_Input     80.0
    Write MAPort Signal    Brake_Interlock    1.0
    Step Simulation Time   10.0
    Inject Hardware Fault  CAN_BUS            COMM_TIMEOUT
    Step Simulation Time   10.0
    ${trq_can}=    Read NetworkPort Signal    TorqueRequest_CAN
    ${flt_st}=     Read Signal Output         fault_status
    Verify Signal Within Tolerance    ${trq_can}    0.0    0.1
    Verify Signal Within Tolerance    ${flt_st}     1.0    0.1
    Clear Hardware Faults
