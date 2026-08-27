*** Settings ***
Documentation     BMS Temperature and Thermal Safety verification tests (New).
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

*** Test Cases ***
EV-BMS-016 Verify normal temperature
    [Documentation]    Checks system behavior at room/nominal operating temperature (25 degrees C).
    Connect Execution Profile    MIL
    Write Signal Input    Temperature    25
    Step Simulation Time    10
    ${dtc}=    Read Signal Output    DTC
    ${fault}=    Read Signal Output    Battery_Fault
    Should Be Equal    ${dtc}    None
    Should Be Equal As Numbers    ${fault}    0
    Disconnect Execution Profile

EV-BMS-017 Verify high-temperature detection
    [Documentation]    Ensures system flags high thermal levels exceeding safety threshold (> 55 degrees C).
    Connect Execution Profile    MIL
    Write Signal Input    Temperature    60
    Step Simulation Time    10
    ${dtc}=    Read Signal Output    DTC
    ${fault}=    Read Signal Output    Battery_Fault
    Should Be Equal    ${dtc}    DTC_BAT_002_OVER_TEMP
    Should Be Equal As Numbers    ${fault}    1
    Disconnect Execution Profile

EV-BMS-018 Verify low-temperature detection
    [Documentation]    Ensures system flags low thermal levels below safety threshold (< -25 degrees C).
    Connect Execution Profile    MIL
    Write Signal Input    Temperature    -30
    Step Simulation Time    10
    ${dtc}=    Read Signal Output    DTC
    ${fault}=    Read Signal Output    Battery_Fault
    Should Be Equal    ${dtc}    DTC_BAT_003_UNDER_TEMP
    Should Be Equal As Numbers    ${fault}    1
    Disconnect Execution Profile

EV-BMS-019 Verify temperature sensor failure
    [Documentation]    Injects sensor failure flag and verifies diagnostic code reporting.
    Connect Execution Profile    MIL
    Write Signal Input    Temperature    25
    Write Signal Input    Fault_Injected    1
    Step Simulation Time    10
    ${dtc}=    Read Signal Output    DTC
    ${fault}=    Read Signal Output    Battery_Fault
    Should Be Equal    ${dtc}    DTC_BAT_001_SENSOR_FAILURE
    Should Be Equal As Numbers    ${fault}    1
    Disconnect Execution Profile

EV-BMS-020 Verify thermal protection
    [Documentation]    Verifies that battery charging halts if a thermal error state exists.
    Connect Execution Profile    MIL
    Write Signal Input    SOC    80
    Write Signal Input    Temperature    52
    Write Signal Input    Is_Charging    1
    Step Simulation Time    10
    ${dtc}=    Read Signal Output    DTC
    ${fault}=    Read Signal Output    Battery_Fault
    Should Be Equal    ${dtc}    DTC_CHG_001_OVER_TEMP_CHARGE
    Should Be Equal As Numbers    ${fault}    1
    Disconnect Execution Profile
