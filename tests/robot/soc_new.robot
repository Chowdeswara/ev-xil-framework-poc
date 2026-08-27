*** Settings ***
Documentation     BMS State of Charge (SOC) & HIL CAN Bus Dynamic Verification Suite.
...               This suite dynamically reads the latest simulation run parameters, expected
...               measurements, and CAN signals from the backend API response (saved on disk),
...               and executes multiple verification test cases.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py
Library           Collections

*** Variables ***
${TOLERANCE}         0.5

*** Test Cases ***
TC-01 Verify Dynamic Telemetry (Torque and Speed)
    [Documentation]    Verifies that the final motor torque and vehicle speed outputs match
    ...                the telemetry values recorded in the simulation API response.
    ${sim_data}=    Load Latest Simulation Result
    
    # Extract inputs and expected values
    ${profile}=     Get From Dictionary    ${sim_data}    profile
    ${inputs}=      Get From Dictionary    ${sim_data}    inputs
    ${throttle}=    Get From Dictionary    ${inputs}      throttle_pct
    ${interlock}=   Get From Dictionary    ${inputs}      interlock_state
    ${duration}=    Get From Dictionary    ${inputs}      duration_ms
    ${soc}=         Get From Dictionary    ${inputs}      bms_soc
    ${temp}=        Get From Dictionary    ${inputs}      bms_temp
    
    ${measurement}=      Get From Dictionary    ${sim_data}       measurement
    ${expected_speed}=   Get From Dictionary    ${measurement}    final_speed_kmh
    ${expected_torque}=  Get From Dictionary    ${measurement}    final_torque_nm
    
    Connect Execution Profile    ${profile}
    
    # Apply inputs
    Write Signal Input    SOC            ${soc}
    Write Signal Input    Temperature    ${temp}
    
    Run Keyword If    '${profile}' == 'HIL'    Run HIL Telemetry Run    ${throttle}    ${interlock}    ${duration}    ${soc}    ${temp}
    ...    ELSE    Step Simulation Time    ${duration}
    
    # Read and assert speed/torque
    ${actual_speed}=     Read Signal Output    Vehicle_Speed
    ${actual_torque}=    Read Signal Output    Motor_Torque
    
    Verify Signal Within Tolerance    ${actual_speed}     ${expected_speed}     1.0
    Verify Signal Within Tolerance    ${actual_torque}    ${expected_torque}    1.0
    
    Disconnect Execution Profile

TC-02 Verify VCU Diagnostics and DTC Status
    [Documentation]    Verifies that the diagnostic trouble codes (DTCs) and fault statuses
    ...                match the expected values logged in the simulation run.
    ${sim_data}=    Load Latest Simulation Result
    
    ${profile}=     Get From Dictionary    ${sim_data}    profile
    ${inputs}=      Get From Dictionary    ${sim_data}    inputs
    ${soc}=         Get From Dictionary    ${inputs}      bms_soc
    ${temp}=        Get From Dictionary    ${inputs}      bms_temp
    
    ${measurement}=      Get From Dictionary    ${sim_data}       measurement
    ${expected_dtc}=     Get From Dictionary    ${measurement}    dtc_status
    ${expected_fault}=   Get From Dictionary    ${measurement}    fault_active
    
    Connect Execution Profile    ${profile}
    
    Write Signal Input    SOC            ${soc}
    Write Signal Input    Temperature    ${temp}
    Step Simulation Time    10.0
    
    # Read actual values dynamically based on HIL vs MIL/SIL profile
    ${actual_dtc}=       Run Keyword If    '${profile}' == 'HIL'    Read Signal Output    ECU_DiagnosticStatus
    ...    ELSE    Read Signal Output    DTC
    
    ${actual_fault}=     Run Keyword If    '${profile}' == 'HIL'    Read Signal Output    fault_status
    ...    ELSE    Read Signal Output    Battery_Fault
    
    # Verify DTC registration
    Run Keyword If    '${profile}' == 'HIL'    Verify Signal Within Tolerance    ${actual_dtc}    ${expected_dtc}    0.1
    ...    ELSE    Verify MIL DTC    ${actual_dtc}    ${expected_dtc}
    
    # Verify fault status
    ${expected_fault_num}=    Convert To Number    ${expected_fault}
    Verify Signal Within Tolerance    ${actual_fault}    ${expected_fault_num}    0.1
    
    Disconnect Execution Profile

TC-03 Verify CAN Bus Restbus Node Signals
    [Documentation]    Asserts that the active CAN signals sent by nodes (BMS, MCU, ABS, TCU)
    ...                on the CAN bus match the logged values in the HIL simulation response.
    ${sim_data}=    Load Latest Simulation Result
    
    ${profile}=     Get From Dictionary    ${sim_data}    profile
    # Skip if not running in HIL since CAN Restbus is only active in HIL mode
    Pass Execution If    '${profile}' != 'HIL'    Skipping Restbus verification on non-HIL profile
    
    ${inputs}=      Get From Dictionary    ${sim_data}    inputs
    ${throttle}=    Get From Dictionary    ${inputs}      throttle_pct
    ${interlock}=   Get From Dictionary    ${inputs}      interlock_state
    ${duration}=    Get From Dictionary    ${inputs}      duration_ms
    ${soc}=         Get From Dictionary    ${inputs}      bms_soc
    ${temp}=        Get From Dictionary    ${inputs}      bms_temp
    
    ${measurement}=      Get From Dictionary    ${sim_data}       measurement
    ${expected_can}=     Get From Dictionary    ${measurement}    can_bus_signals
    
    Connect Execution Profile    HIL
    
    Run HIL Telemetry Run    ${throttle}    ${interlock}    ${duration}    ${soc}    ${temp}
    
    # Verify specific CAN signals dynamically from node registry
    ${has_mcu}=    Evaluate    "MCU" in ${expected_can}
    Run Keyword If    ${has_mcu}    Verify MCU CAN Signals    ${expected_can}
    
    ${has_bms}=    Evaluate    "BMS" in ${expected_can}
    Run Keyword If    ${has_bms}    Verify BMS CAN Signals    ${expected_can}
    
    Disconnect Execution Profile

TC-04 Verify Functional Safety Interlock Logic
    [Documentation]    Checks that VCU safety shutdown behaves exactly as expected when the safety loop link is opened.
    ${sim_data}=    Load Latest Simulation Result
    
    ${inputs}=      Get From Dictionary    ${sim_data}    inputs
    ${interlock}=   Get From Dictionary    ${inputs}      interlock_state
    
    # Skip if interlock was closed during this simulation run
    Pass Execution If    ${interlock} == 1.0    Skipping Interlock check because safety loop was closed in simulation
    
    ${profile}=     Get From Dictionary    ${sim_data}    profile
    ${measurement}=      Get From Dictionary    ${sim_data}       measurement
    ${expected_torque}=  Get From Dictionary    ${measurement}    final_torque_nm
    ${expected_dtc}=     Get From Dictionary    ${measurement}    dtc_status
    
    Connect Execution Profile    ${profile}
    
    # Explicitly verify VCU shutdown when interlock is open (0.0)
    Write Signal Input    SOC    50.0
    Run Keyword If    '${profile}' == 'HIL'    Write MAPort Signal    Brake_Interlock    0.0
    ...    ELSE    Write Signal Input    Brake_Interlock    0.0
    
    Step Simulation Time    10.0
    
    ${actual_torque}=    Read Signal Output    Motor_Torque
    ${actual_state}=     Read Signal Output    ECU_State
    
    Verify Signal Within Tolerance    ${actual_torque}    0.0    0.01
    Verify Signal Within Tolerance    ${actual_state}     0.0    0.01
    
    Disconnect Execution Profile

*** Keywords ***
Run HIL Telemetry Run
    [Arguments]    ${throttle}    ${interlock}    ${duration}    ${soc}    ${temp}
    Write MAPort Signal    Throttle_Input     ${throttle}
    Write MAPort Signal    Brake_Interlock    ${interlock}
    
    # Initialize restbus signals matching inputs
    Set Restbus Signal     BMS    SOC            ${soc}
    Set Restbus Signal     BMS    Temperature    ${temp}
    
    ${initial_mcu_trq}=    Evaluate    (${throttle} / 100.0) * 350.0
    Set Restbus Signal     MCU    Actual_Torque  ${initial_mcu_trq}
    
    # If safety interlock is closed, perform the mid-simulation throttle ramp matching the engine logic
    ${has_interlock}=    Evaluate    ${interlock} >= 0.5
    Run Keyword If    ${has_interlock}    Run HIL With Ramped Throttle    ${throttle}    ${duration}
    ...    ELSE    Step Simulation Time    ${duration}

Run HIL With Ramped Throttle
    [Arguments]    ${throttle}    ${duration}
    ${half_duration}=    Evaluate    ${duration} / 2.0
    Step Simulation Time    ${half_duration}
    
    ${ramped_throttle}=    Evaluate    min(100.0, ${throttle} * 1.4)
    Write MAPort Signal    Throttle_Input     ${ramped_throttle}
    
    # Update ramped restbus actual torque
    ${ramped_mcu_trq}=    Evaluate    (${ramped_throttle} / 100.0) * 350.0
    Set Restbus Signal     MCU    Actual_Torque  ${ramped_mcu_trq}
    
    Step Simulation Time    ${half_duration}

Verify MCU CAN Signals
    [Arguments]    ${expected_can}
    ${mcu_node}=    Get From Dictionary    ${expected_can}    MCU
    ${expected_mcu_trq}=    Get From Dictionary    ${mcu_node}    Actual_Torque
    ${actual_mcu_trq}=      Get Restbus Signal     MCU    Actual_Torque
    Verify Signal Within Tolerance    ${actual_mcu_trq}    ${expected_mcu_trq}    1.0

Verify BMS CAN Signals
    [Arguments]    ${expected_can}
    ${bms_node}=    Get From Dictionary    ${expected_can}    BMS
    ${expected_bms_soc}=    Get From Dictionary    ${bms_node}    SOC
    ${actual_bms_soc}=      Get Restbus Signal     BMS    SOC
    Verify Signal Within Tolerance    ${actual_bms_soc}    ${expected_bms_soc}    1.0

Verify MIL DTC
    [Arguments]    ${actual_dtc}    ${expected_dtc}
    Run Keyword If    ${expected_dtc} == 0    Should Be Equal    ${actual_dtc}    None
    ...    ELSE    Should Not Be Equal    ${actual_dtc}    None
