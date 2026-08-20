/* 
 * Production C Code Generated from Simulink EV_Controller.slx
 * EV Motor Controller SIL (Software-in-the-Loop) C Implementation
 */

#include <stdio.h>
#include <stdint.h>

/* ExtU_EV_Controller_T: Input Structure */
typedef struct {
    double Throttle_Pedal_In;    /* 0.0 to 100.0 % */
    double HV_Interlock_State;   /* 1.0 = Closed/OK, 0.0 = Open/Fault */
} ExtU_EV_Controller_T;

/* ExtY_EV_Controller_T: Output Structure */
typedef struct {
    double Target_Torque_Out;   /* Motor Torque demand in Nm */
    double Fault_Status;        /* 0.0 = OK, 1.0 = Interlock Fault */
} ExtY_EV_Controller_T;

/* Global External Inputs and Outputs */
ExtU_EV_Controller_T EV_Controller_U;
ExtY_EV_Controller_T EV_Controller_Y;

/* Configuration Parameters */
static const double MAX_TORQUE_NM = 350.0;

/* 
 * Model initialize function
 */
void EV_Controller_initialize(void) {
    EV_Controller_U.Throttle_Pedal_In = 0.0;
    EV_Controller_U.HV_Interlock_State = 1.0;
    EV_Controller_Y.Target_Torque_Out = 0.0;
    EV_Controller_Y.Fault_Status = 0.0;
}

/* 
 * Model step function executed periodically (10ms task)
 */
void EV_Controller_step(void) {
    double throttle = EV_Controller_U.Throttle_Pedal_In;
    double interlock = EV_Controller_U.HV_Interlock_State;

    if (interlock < 0.5) {
        /* Safety Shutdown: HV Interlock Open */
        EV_Controller_Y.Target_Torque_Out = 0.0;
        EV_Controller_Y.Fault_Status = 1.0;
    } else {
        /* Normal Drive Mode: Calculate Proportional Torque */
        if (throttle < 0.0) throttle = 0.0;
        if (throttle > 100.0) throttle = 100.0;

        EV_Controller_Y.Target_Torque_Out = (throttle / 100.0) * MAX_TORQUE_NM;
        EV_Controller_Y.Fault_Status = 0.0;
    }
}

/* 
 * Model terminate function
 */
void EV_Controller_terminate(void) {
    /* Cleanup */
}

/* C-Interface Getters and Setters for Python ctypes binding */
void set_input_throttle(double val) {
    EV_Controller_U.Throttle_Pedal_In = val;
}

void set_input_interlock(double val) {
    EV_Controller_U.HV_Interlock_State = val;
}

double get_output_torque(void) {
    return EV_Controller_Y.Target_Torque_Out;
}

double get_output_fault(void) {
    return EV_Controller_Y.Fault_Status;
}
