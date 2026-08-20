*** Settings ***
Documentation     BMS State of Charge (SOC) validation tests.
Resource          ../../resources/bms_keywords.robot

*** Test Cases ***
EV-BMS-001 Verify SOC at 100%
    [Documentation]    Verifies SOC calibration at maximum scale (100%).
    Verify BMS SOC Level    100

EV-BMS-002 Verify SOC at 80%
    [Documentation]    Verifies SOC calibration at normal high scale (80%).
    Verify BMS SOC Level    80

EV-BMS-003 Verify SOC at 50%
    [Documentation]    Verifies SOC calibration at mid scale (50%).
    Verify BMS SOC Level    50

EV-BMS-004 Verify SOC at 20%
    [Documentation]    Verifies SOC calibration at low scale (20%).
    Verify BMS SOC Level    20

EV-BMS-005 Verify low SOC threshold
    [Documentation]    Checks warning trigger when SOC is at or below low threshold (20%).
    Verify SOC Thresholds    20    WARNING_LOW
    Verify SOC Thresholds    10    WARNING_LOW

EV-BMS-006 Verify critical SOC threshold
    [Documentation]    Checks warning trigger when SOC is at or below critical threshold (5%).
    Verify SOC Thresholds    5     CRITICAL_LOW
    Verify SOC Thresholds    3     CRITICAL_LOW

EV-BMS-007 Verify SOC increase during charging
    [Documentation]    Confirms SOC increments during charging state.
    Verify SOC Change During State    50    Charging    5    AC

EV-BMS-008 Verify SOC decrease during discharge
    [Documentation]    Confirms SOC decrements under driving/discharge.
    Verify SOC Change During State    50    Discharging    5

EV-BMS-009 Verify invalid SOC
    [Documentation]    Asserts out-of-range SOC values are handled appropriately.
    # Out of boundary checks (SOC cannot be > 100% or < 0% initially)
    Verify SOC Boundaries    150
    Verify SOC Boundaries    -10

EV-BMS-010 Verify SOC boundary values
    [Documentation]    Validates exact boundary values for SOC calculation logic.
    Verify BMS SOC Level    0
    Verify BMS SOC Level    100
