*** Settings ***
Documentation     HIL Restbus Simulation and Fault Injection validation tests.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

*** Test Cases ***
TC-RB-001 Verify HIL Restbus Keepalive
    [Documentation]    VCU stays in normal operational mode (ECU_State = 2.0) when restbus is broadcasting.
    Connect Execution Profile    HIL
    Step Simulation Time    50
    ${ecu_st}=    Read Signal Output    ECU_State
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${ecu_st}    2.0    0.01
    Verify Signal Within Tolerance    ${dtc}    0.0    0.01
    Disconnect Execution Profile

TC-RB-002 Verify BMS Communication Timeout Fault Injection
    [Documentation]    VCU transitions to limp mode (ECU_State = 3.0) and logs DTC 81.0 when BMS timeout is active.
    Connect Execution Profile    HIL
    Inject Restbus Timeout    BMS    1
    Step Simulation Time    50
    ${ecu_st}=    Read Signal Output    ECU_State
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${ecu_st}    3.0    0.01
    Verify Signal Within Tolerance    ${dtc}    81.0    0.01
    Disconnect Execution Profile

TC-RB-003 Verify MCU Communication Timeout Fault Injection
    [Documentation]    VCU transitions to limp mode (ECU_State = 3.0) and logs DTC 81.0 when MCU timeout is active.
    Connect Execution Profile    HIL
    Inject Restbus Timeout    MCU    1
    Step Simulation Time    50
    ${ecu_st}=    Read Signal Output    ECU_State
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${ecu_st}    3.0    0.01
    Verify Signal Within Tolerance    ${dtc}    81.0    0.01
    Disconnect Execution Profile

TC-RB-004 Verify TCU Communication Timeout Fault Injection
    [Documentation]    VCU transitions to limp mode (ECU_State = 3.0) and logs DTC 81.0 when TCU timeout is active.
    Connect Execution Profile    HIL
    Inject Restbus Timeout    TCU    1
    Step Simulation Time    50
    ${ecu_st}=    Read Signal Output    ECU_State
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${ecu_st}    3.0    0.01
    Verify Signal Within Tolerance    ${dtc}    81.0    0.01
    Disconnect Execution Profile

TC-RB-005 Verify BMS CRC Checksum Fault Injection
    [Documentation]    VCU transitions to limp mode (ECU_State = 3.0) and logs DTC 81.0 when BMS CRC/checksum corruption is active.
    Connect Execution Profile    HIL
    Inject Restbus CRC Counter Fault    BMS    1
    Step Simulation Time    50
    ${ecu_st}=    Read Signal Output    ECU_State
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    Verify Signal Within Tolerance    ${ecu_st}    3.0    0.01
    Verify Signal Within Tolerance    ${dtc}    81.0    0.01
    Disconnect Execution Profile
