*** Settings ***
Documentation    High-level Vehicle Acceleration, Braking, and Battery Load Test Suite.
Resource         custom_keywords.robot

*** Test Cases ***
Verify Vehicle Accelerates Above 60 km/h
    [Documentation]    Start simulation, apply 80% throttle, wait, then assert speed > 60 km/h.
    
    Start Simulation
    Configure Vehicle    mass=1600.0
    Configure Weather    temperature=25.0
    
    Set Accelerator    80.0
    Wait    5s
    
    ${telemetry}=    Get Telemetry
    ${speed}=    Set Variable    ${telemetry}[vehicle_speed_kmh]
    Log    Observed speed: ${speed} km/h
    Should Be True    ${speed} > 60    Speed was ${speed} km/h, expected > 60

    Set Accelerator    0.0
    Stop Simulation

Verify Emergency Braking Stops Vehicle
    [Documentation]    Accelerate then apply full brakes. Assert vehicle reaches near 0 km/h.
    
    Start Simulation
    
    # Accelerate
    Set Accelerator    70.0
    Wait    4s
    
    # Full brake
    Set Accelerator    0.0
    Set Brake    120.0
    Wait    4s
    
    # Assert stopped
    ${telemetry}=    Get Telemetry
    ${speed}=    Set Variable    ${telemetry}[vehicle_speed_kmh]
    Log    Final speed after braking: ${speed} km/h
    Should Be True    ${speed} < 2.0    Vehicle did not stop. Speed: ${speed} km/h

    # Clean up
    Set Brake    0.0
    Stop Simulation

Verify Battery SOC Decreases Under Load
    [Documentation]    Run at high throttle and verify battery drains.
    
    Start Simulation
    
    # Read initial SOC
    ${telemetry_before}=    Get Telemetry
    ${soc_before}=    Set Variable    ${telemetry_before}[battery_soc]
    Log    SOC before load: ${soc_before}%
    
    # Apply heavy load
    Set Accelerator    90.0
    Wait    6s
    
    # Read SOC after load
    ${telemetry_after}=    Get Telemetry
    ${soc_after}=    Set Variable    ${telemetry_after}[battery_soc]
    Log    SOC after load: ${soc_after}%
    Should Be True    ${soc_after} < ${soc_before}    Battery SOC did not decrease. Before: ${soc_before}, After: ${soc_after}

    # Clean up
    Set Accelerator    0.0
    Stop Simulation
