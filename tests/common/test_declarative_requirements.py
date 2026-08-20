"""Declarative Requirements Evaluation Test Suite."""

import pytest
from ev_xil.core.requirement import traced_to


def test_declarative_requirements_eval_mil(mil_adapter, requirements_map, signal_recorder):
    """Evaluates declarative ISO 26262 YAML requirements against MIL adapter."""
    if not requirements_map:
        pytest.skip("No requirements.yaml loaded")

    req_accel = requirements_map["acceleration"]
    req_interlock = requirements_map["drive_interlock"]
    req_zero = requirements_map["zero_throttle"]

    # Step 1: Drive Enable & 80% Throttle Demand (Accelerate within timeout window)
    mil_adapter.write_signal("Brake_Interlock", 1.0)
    mil_adapter.write_signal("Throttle_Input", 80.0)
    mil_adapter.step(200.0)  # 200ms acceleration simulation time

    speed_val = mil_adapter.read_signal(req_accel.signal)
    signal_recorder.record(200.0, req_accel.signal, speed_val)
    req_accel.evaluate(speed_val)  # Verifies Vehicle_Speed >= 40.0 km/h

    # Step 2: Trip Drive Interlock (0.0)
    mil_adapter.write_signal("Brake_Interlock", 0.0)
    mil_adapter.step(10.0)

    torque_val = mil_adapter.read_signal(req_interlock.signal)
    signal_recorder.record(210.0, req_interlock.signal, torque_val)
    req_interlock.evaluate(torque_val)  # Verifies Motor_Torque == 0.0 Nm

    # Step 3: Zero Throttle
    mil_adapter.write_signal("Brake_Interlock", 1.0)
    mil_adapter.write_signal("Throttle_Input", 0.0)
    mil_adapter.step(10.0)

    zero_torque = mil_adapter.read_signal(req_zero.signal)
    signal_recorder.record(220.0, req_zero.signal, zero_torque)
    req_zero.evaluate(zero_torque)  # Verifies Motor_Torque == 0.0 Nm
