*** Settings ***
Documentation     BMS Cell and Pack Voltage validation tests.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

*** Test Cases ***
EV-BMS-011 Verify normal cell voltage
    [Documentation]    Ensures calculated cell voltage matches expected value at 50% SOC (nominal).
    Connect Execution Profile    MIL
    Write Signal Input    SOC    50
    Step Simulation Time    10
    ${volts}=    Read Signal Output    Cell_Voltage
    Verify Signal Within Tolerance    ${volts}    3.6    0.01
    Disconnect Execution Profile

EV-BMS-012 Verify minimum cell voltage
    [Documentation]    Ensures cell voltage maps correctly at minimum safe capacity (0% SOC).
    Connect Execution Profile    MIL
    Write Signal Input    SOC    0
    Step Simulation Time    10
    ${volts}=    Read Signal Output    Cell_Voltage
    Verify Signal Within Tolerance    ${volts}    3.0    0.01
    Disconnect Execution Profile

EV-BMS-013 Verify maximum cell voltage
    [Documentation]    Ensures cell voltage maps correctly at maximum capacity (100% SOC).
    Connect Execution Profile    MIL
    Write Signal Input    SOC    100
    Step Simulation Time    10
    ${volts}=    Read Signal Output    Cell_Voltage
    Verify Signal Within Tolerance    ${volts}    4.2    0.01
    Disconnect Execution Profile

EV-BMS-014 Verify over-voltage detection
    [Documentation]    Verifies pack triggers warning status when cell voltage exceeds safe limit.
    Connect Execution Profile    MIL
    Write Signal Input    SOC    105
    Step Simulation Time    10
    ${status}=    Read Signal Output    Pack_Voltage_Status
    Should Be Equal    ${status}    OVER_VOLTAGE
    Disconnect Execution Profile

EV-BMS-015 Verify under-voltage detection
    [Documentation]    Verifies pack triggers warning status when cell voltage drops below safe limit.
    Connect Execution Profile    MIL
    Write Signal Input    SOC    -15
    Step Simulation Time    10
    ${status}=    Read Signal Output    Pack_Voltage_Status
    Should Be Equal    ${status}    UNDER_VOLTAGE
    Disconnect Execution Profile
