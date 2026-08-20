"""ISO 26262 Requirement Traceability Models, Declarative Schemas, and Decorators."""

import functools
from typing import List, Union, Callable, Any, Optional, Dict
from pydantic import BaseModel, Field, ConfigDict
from ev_xil.core.verdict import VerdictError, assert_within_tolerance


class Requirement(BaseModel):
    """Model representing an ISO 26262 or functional requirement."""

    model_config = ConfigDict(extra="allow")

    req_id: str = Field(..., description="Unique requirement ID (e.g. EV-REQ-001)")
    description: str = Field(..., description="High-level requirement description")
    asil_level: str = Field("QM", description="ASIL Level (QM, ASIL-A, ASIL-B, ASIL-C, ASIL-D)")


class DeclarativeRequirement(BaseModel):
    """Declarative requirement schema specifying signal thresholds, operators, and timeouts."""

    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Requirement ID e.g. EV-REQ-001")
    title: Optional[str] = Field(None, description="Short title for requirement")
    description: str = Field(..., description="Requirement description")
    signal: str = Field(..., description="Logical signal name to verify")
    operator: str = Field("==", description="Comparison operator (==, >=, <=, >, <, !=)")
    value: float = Field(..., description="Target threshold value")
    unit: Optional[str] = Field(None, description="Physical unit e.g. km/h, Nm")
    timeout_sec: float = Field(0.0, description="Evaluation time limit in seconds")
    asil: str = Field("QM", description="ASIL Level (QM, ASIL-A, ASIL-B, ASIL-C, ASIL-D)")

    @property
    def req_id(self) -> str:
        return self.id

    @property
    def asil_level(self) -> str:
        return self.asil

    def evaluate(self, actual_val: float) -> bool:
        """Evaluates actual signal value against specified operator and target value."""
        actual = float(actual_val)
        target = float(self.value)
        op = self.operator.strip()

        passed = False
        if op == "==":
            passed = abs(actual - target) < 1e-3
        elif op == ">=":
            passed = actual >= target
        elif op == "<=":
            passed = actual <= target
        elif op == ">":
            passed = actual > target
        elif op == "<":
            passed = actual < target
        elif op == "!=":
            passed = abs(actual - target) >= 1e-3
        else:
            raise ValueError(f"Unsupported operator: {self.operator}")

        if not passed:
            err_msg = (
                f"Requirement [{self.id}] FAILED: {self.title or self.description}. "
                f"Signal '{self.signal}' actual={actual}{self.unit or ''} "
                f"expected {op} {target}{self.unit or ''}"
            )
            raise VerdictError(err_msg, signal_name=self.signal, actual=actual)

        return True


def traced_to(*reqs: Union[str, Requirement, DeclarativeRequirement]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator to attach ISO 26262 requirement models or strings to test functions."""

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        existing = getattr(fn, "__requirements__", [])
        new_reqs = list(existing)
        for item in reqs:
            if isinstance(item, (Requirement, DeclarativeRequirement)):
                new_reqs.append(item)
            elif isinstance(item, str):
                new_reqs.append(Requirement(req_id=item, description=f"Traced requirement {item}", asil_level="QM"))
            else:
                raise TypeError(f"Invalid requirement type: {type(item)}")

        setattr(fn, "__requirements__", new_reqs)

        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return fn(*args, **kwargs)

        setattr(wrapper, "__requirements__", new_reqs)
        return wrapper

    return decorator
