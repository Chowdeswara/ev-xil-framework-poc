% Programmatic Creation of EV_Controller.slx Model for MATLAB Simulink MIL Testing
% Run this function in MATLAB to build and save EV_Controller.slx

function create_ev_controller_model()
    modelName = 'EV_Controller';

    % Create new system if not open
    if bdIsLoaded(modelName)
        close_system(modelName, 0);
    end
    new_system(modelName);
    open_system(modelName);

    % Add Inport Blocks
    add_block('simulink/Sources/In1', [modelName, '/Throttle_Pedal_In'], 'Position', [50, 50, 80, 64]);
    add_block('simulink/Sources/In1', [modelName, '/HV_Interlock_State'], 'Position', [50, 120, 80, 134]);

    % Add Gain Block for Max Torque Scaling (350 Nm)
    add_block('simulink/Math Operations/Gain', [modelName, '/Torque_Gain'], 'Position', [150, 45, 190, 69], 'Gain', '3.5');

    % Add Product Block for HV Interlock Safety Gate
    add_block('simulink/Math Operations/Product', [modelName, '/Safety_Gate'], 'Position', [260, 50, 290, 135], 'Inputs', '2');

    % Add Outport Blocks
    add_block('simulink/Sinks/Out1', [modelName, '/Target_Torque_Out'], 'Position', [360, 85, 390, 99]);

    % Connect Ports
    add_line(modelName, 'Throttle_Pedal_In/1', 'Torque_Gain/1');
    add_line(modelName, 'Torque_Gain/1', 'Safety_Gate/1');
    add_line(modelName, 'HV_Interlock_State/1', 'Safety_Gate/2');
    add_line(modelName, 'Safety_Gate/1', 'Target_Torque_Out/1');

    % Save Model to slx file
    save_system(modelName, fullfile(pwd, 'EV_Controller.slx'));
    fprintf('Successfully created and saved EV_Controller.slx!\n');
end
