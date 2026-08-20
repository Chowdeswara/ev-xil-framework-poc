% Automated C-Code Generation Script for EV_Controller.slx
% Uses Simulink Coder (grt.tlc) or Embedded Coder (ert.tlc) to generate production C code (.c/.h)

function generate_c_code()
    modelName = 'EV_Controller';

    % Ensure model is open
    if ~bdIsLoaded(modelName)
        open_system(modelName);
    end

    % Set Fixed-Step solver required for C code generation
    set_param(modelName, 'SolverType', 'Fixed-step');
    set_param(modelName, 'Solver', 'FixedStepDiscrete');
    set_param(modelName, 'FixedStep', '0.01');

    % Check if Embedded Coder license is installed and active
    hasEmbeddedCoder = license('test', 'Embedded_Coder') || license('test', 'RTW_Embedded_Coder');

    if hasEmbeddedCoder
        try
            set_param(modelName, 'SystemTargetFile', 'ert.tlc');
            fprintf('Using Embedded Coder target (ert.tlc)\n');
        catch
            set_param(modelName, 'SystemTargetFile', 'grt.tlc');
            fprintf('Fallback to Simulink Coder target (grt.tlc)\n');
        end
    else
        set_param(modelName, 'SystemTargetFile', 'grt.tlc');
        fprintf('Embedded Coder not licensed. Using standard Simulink Coder target (grt.tlc)\n');
    end

    set_param(modelName, 'GenerateReport', 'on');

    fprintf('Generating C-code for model %s...\n', modelName);
    
    % Trigger Code Generation (Equivalent to Ctrl+B)
    slbuild(modelName);

    fprintf('Successfully generated C code for %s!\n', modelName);
end
