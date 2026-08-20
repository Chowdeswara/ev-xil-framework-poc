*** Settings ***
Documentation     ISO 26262 Back-to-Back (B2B) Equivalence & Cross-Level Matrix Robot Suite.
Library           ../../src/ev_xil/robot/EVXiLLibrary.py

*** Test Cases ***
TC-EQ-001 MIL vs SIL Back-to-Back Equivalence Verification
    [Documentation]    Executes TC_EV_001 on MIL and SIL and asserts |MIL_Speed - SIL_Speed| <= 0.5 km/h.
    # 1. Execute MIL
    Connect Execution Profile    MIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${mil_trq}=    Read Signal Output    Motor_Torque
    ${mil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 2. Execute SIL
    Connect Execution Profile    SIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${sil_trq}=    Read Signal Output    Motor_Torque
    ${sil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 3. Verify ISO 26262 B2B Equivalence
    Verify Signal Equivalence    ${mil_trq}    ${sil_trq}    0.5
    Verify Signal Equivalence    ${mil_spd}    ${sil_spd}    0.5

TC-EQ-002 Cross-Level Equivalence Verification Across MIL SIL HIL VIL
    [Documentation]    Executes 50% throttle across all 4 profiles and verifies cross-level numerical consistency.
    # 1. MIL
    Connect Execution Profile    MIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${mil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 2. SIL
    Connect Execution Profile    SIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${sil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 3. HIL
    Connect Execution Profile    HIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${hil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 4. VIL
    Connect Execution Profile    VIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    Throttle_Input     50.0
    Step Simulation Time  200.0
    ${vil_spd}=    Read Signal Output    Vehicle_Speed
    Disconnect Execution Profile

    # 5. Verify Cross-Level Consistency
    Verify Cross Level Equivalence    Vehicle_Speed    ${mil_spd}    ${sil_spd}    ${hil_spd}    ${vil_spd}    0.5
