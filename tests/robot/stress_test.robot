*** Settings ***
Documentation    Stress testing vehicle behavior under sudden acceleration and braking conditions.
Resource         custom_keywords.robot

*** Test Cases ***
Stress Test Extreme Conditions
    [Documentation]    Test vehicle behavior under sudden acceleration, gravel road, extreme weather, and hard braking.
    
    Start Simulation
    Configure Vehicle    mass=2000.0    drag_coef=0.4
    Configure Weather    temperature=-5.0    humidity=90.0
    Configure Road    surface=gravel    friction=0.3
    
    # Sudden acceleration
    Set Accelerator    100.0
    Wait    4s
    
    ${telemetry}=    Get Telemetry
    Log    Speed after sudden acceleration on gravel: ${telemetry}[vehicle_speed_kmh] km/h
    
    # Sudden brakes
    Set Accelerator    0.0
    Set Brake    150.0
    Wait    3s
    
    ${telemetry_after_brake}=    Get Telemetry
    Log    Speed after hard braking on gravel: ${telemetry_after_brake}[vehicle_speed_kmh] km/h
    Should Be True    ${telemetry_after_brake}[vehicle_speed_kmh] < 20.0    Vehicle failed to stop on gravel
    
    # Clean up
    Set Brake    0.0
    Stop Simulation
