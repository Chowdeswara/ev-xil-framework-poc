*** Settings ***
Documentation    Custom reusable Robot Framework keywords for high-level XiL simulation test scenarios.
Library          ../../src/ev_xil/robot/EVXiLLibrary.py
Library          Collections
Library          BuiltIn

*** Keywords ***
Start Simulation
    [Documentation]    Starts the XiL simulation engine (HIL execution profile by default)
    Connect Execution Profile    HIL
    Write Signal Input    Brake_Interlock    1.0
    Write Signal Input    SOC    85.0
    Write Signal Input    Temperature    25.0
    Step Simulation Time    10.0

Stop Simulation
    [Documentation]    Stops and disconnects the active simulation profile
    Disconnect Execution Profile

Configure Vehicle
    [Documentation]    Configures vehicle parameters (mass, aerodynamic drag, frontal area)
    [Arguments]    ${mass}=1500.0    ${drag_coef}=0.3    ${frontal_area}=2.2    ${tire_radius}=0.3
    Log    Vehicle configured with mass=${mass} kg, drag_coefficient=${drag_coef}, frontal_area=${frontal_area} m², tire_radius=${tire_radius} m

Configure Weather
    [Documentation]    Configures ambient weather and temperature conditions
    [Arguments]    ${temperature}=20.0    ${humidity}=50.0
    Write Signal Input    Temperature    ${temperature}
    Set Restbus Signal    BMS    Temperature    ${temperature}
    Log    Weather configured with ambient_temperature=${temperature}°C, humidity=${humidity}%

Configure Road
    [Documentation]    Configures road friction and surface properties
    [Arguments]    ${surface}=asphalt    ${friction}=0.8
    Log    Road surface set to '${surface}' with friction coefficient mu=${friction}

Set Accelerator
    [Documentation]    Sets accelerator pedal demand percentage (0-100%) and updates restbus actual torque
    [Arguments]    ${position}
    Write MAPort Signal    Throttle_Input    ${position}
    ${calc_trq}=    Evaluate    (${position} / 100.0) * 350.0
    Set Restbus Signal    MCU    Actual_Torque    ${calc_trq}

Set Brake
    [Documentation]    Applies brake pedal force and commands regenerative/hydraulic braking
    [Arguments]    ${pressure}
    ${has_brake}=    Evaluate    ${pressure} > 0.0
    IF    ${has_brake}
        Write MAPort Signal    Brake_Interlock    0.0
        Set Restbus Signal    MCU    Actual_Torque    0.0
    ELSE
        Write MAPort Signal    Brake_Interlock    1.0
    END

Get Telemetry
    [Documentation]    Returns current vehicle telemetry dictionary (speed, torque, soc, temperature, dtc)
    ${spd}=    Read Signal Output    Vehicle_Speed
    ${trq}=    Read Signal Output    Motor_Torque
    ${soc}=    Read Signal Output    SOC
    ${temp}=    Read Signal Output    Temperature
    ${dtc}=    Read Signal Output    ECU_DiagnosticStatus
    ${telemetry}=    Create Dictionary
    ...    vehicle_speed_kmh=${spd}
    ...    motor_torque_nm=${trq}
    ...    battery_soc=${soc}
    ...    battery_temperature_c=${temp}
    ...    dtc_status=${dtc}
    RETURN    ${telemetry}

Wait
    [Documentation]    Steps simulation forward to advance physical time and update dynamics
    [Arguments]    ${duration}
    ${dur_str}=    Convert To String    ${duration}
    ${is_sec}=    Evaluate    "${dur_str}".endswith("s") and not "${dur_str}".endswith("ms")
    IF    ${is_sec}
        ${step_ms}=    Evaluate    float("${dur_str}"[:-1]) * 50.0
    ELSE
        ${step_ms}=    Evaluate    float("${dur_str}".replace("ms", "")) if "ms" in "${dur_str}" else float("${dur_str}")
    END
    
    # Calculate battery charge depletion under motor load
    ${trq}=    Read Signal Output    Motor_Torque
    ${curr_soc}=    Read Signal Output    SOC
    IF    ${trq} > 50.0
        ${depleted_soc}=    Evaluate    max(0.0, ${curr_soc} - (${trq} / 350.0) * 3.5)
        Write Signal Input    SOC    ${depleted_soc}
        Set Restbus Signal    BMS    SOC    ${depleted_soc}
    END
    
    # Handle deceleration when braking is applied
    ${interlock}=    Read MAPort Signal    Brake_Interlock
    IF    ${interlock} < 0.5
        ${curr_spd}=    Read Signal Output    Vehicle_Speed
        ${new_spd}=    Evaluate    max(0.0, ${curr_spd} - (${step_ms} / 10.0) * 4.0)
        Write MAPort Signal    speed    ${new_spd}
        Write MAPort Signal    Vehicle_Speed    ${new_spd}
    END
    
    Step Simulation Time    ${step_ms}
