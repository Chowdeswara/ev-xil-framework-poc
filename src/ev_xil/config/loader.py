"""Configuration and requirement loader for platform signal mappings and ISO 26262 requirements."""

import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from pydantic import BaseModel, Field, ConfigDict
from ev_xil.core.requirement import DeclarativeRequirement


class EquivalenceRequirement(BaseModel):
    """Pydantic model representing an equivalence requirement specification."""
    reference: str = Field("MIL", description="Reference profile name")
    candidate: str = Field("SIL", description="Candidate profile name")
    tolerance: float = Field(0.5, description="Maximum allowable numerical error limit")
    unit: Optional[str] = Field(None, description="Engineering unit")


class PlatformConfig(BaseModel):
    """Pydantic model representing a platform YAML configuration."""

    model_config = ConfigDict(extra="allow")

    profile: Optional[str] = Field(None, description="Execution profile: mil, sil, hil, or vil")
    platform_name: Optional[str] = Field(None, description="Platform identifier string")
    test_level: Optional[str] = Field(None, description="Test level name")
    sample_time_ms: Optional[float] = Field(None, description="Simulation sample time in ms")
    step_size_ms: float = Field(10.0, description="Step size in ms")
    timeout_s: float = Field(30.0, description="Execution timeout in seconds")
    model_path: Optional[str] = Field(None, description="Path to model file")
    backend_settings: Dict[str, Any] = Field(default_factory=dict, description="Backend settings for adapter")
    signals: Dict[str, str] = Field(default_factory=dict, description="Logical to physical signal mappings")
    maport: Dict[str, str] = Field(default_factory=dict, description="Speedgoat plant IO MAPort mappings")
    network_port: Dict[str, str] = Field(default_factory=dict, description="CAN NetworkPort mappings")
    ecu_port: Dict[str, str] = Field(default_factory=dict, description="ECUMPort state/diagnostic mappings")
    extra_options: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific metadata/paths")

    @property
    def effective_test_level(self) -> str:
        if self.profile:
            return self.profile.upper()
        if self.test_level:
            return self.test_level.upper()
        return "MIL"

    @property
    def effective_sample_time(self) -> float:
        if self.sample_time_ms is not None:
            return self.sample_time_ms
        return self.step_size_ms


class ConfigLoader:
    """Utility class to load YAML platform configuration files."""

    @staticmethod
    def load(yaml_path: str) -> PlatformConfig:
        """Loads and parses a platform YAML file into a PlatformConfig model."""
        path = Path(yaml_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return PlatformConfig(**data)


class RequirementLoader:
    """Utility class to load declarative ISO 26262 YAML requirements."""

    @staticmethod
    def load(yaml_path: str) -> Dict[str, DeclarativeRequirement]:
        """Loads requirements.yaml into a dictionary of DeclarativeRequirement models."""
        path = Path(yaml_path)
        if not path.is_file():
            raise FileNotFoundError(f"Requirements file not found: {yaml_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        req_dict: Dict[str, DeclarativeRequirement] = {}
        raw_reqs = data.get("requirements", {})
        for key, req_data in raw_reqs.items():
            req_dict[key] = DeclarativeRequirement(**req_data)

        return req_dict

    @staticmethod
    def load_equivalence(yaml_path: str) -> Dict[str, EquivalenceRequirement]:
        """Loads equivalence section from requirements.yaml into a dictionary of EquivalenceRequirement models."""
        path = Path(yaml_path)
        if not path.is_file():
            raise FileNotFoundError(f"Requirements file not found: {yaml_path}")

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        eq_dict: Dict[str, EquivalenceRequirement] = {}
        raw_eqs = data.get("equivalence", {})
        for key, eq_data in raw_eqs.items():
            eq_dict[key] = EquivalenceRequirement(**eq_data)

        return eq_dict
