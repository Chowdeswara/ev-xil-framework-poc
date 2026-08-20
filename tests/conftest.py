"""Pytest fixtures for EV XiL automation test framework."""

import pytest
from pathlib import Path
from ev_xil.config.loader import ConfigLoader, RequirementLoader, PlatformConfig
from ev_xil.adapters.mil.matlab_mil import MatlabMilAdapter
from ev_xil.adapters.sil.matlab_sil import MatlabSilAdapter
from ev_xil.adapters.hil.matlab_hil import MatlabHilAdapter
from ev_xil.adapters.vil.vehicle import VehicleVilAdapter
from ev_xil.core.measurement import SignalRecorder


CONFIG_DIR = Path(__file__).parent.parent / "configs"


@pytest.fixture
def requirements_map():
    req_file = CONFIG_DIR / "requirements.yaml"
    if req_file.exists():
        return RequirementLoader.load(str(req_file))
    return {}


@pytest.fixture
def mil_config() -> PlatformConfig:
    return ConfigLoader.load(str(CONFIG_DIR / "mil.yaml"))


@pytest.fixture
def sil_config() -> PlatformConfig:
    return ConfigLoader.load(str(CONFIG_DIR / "sil.yaml"))


@pytest.fixture
def hil_config() -> PlatformConfig:
    return ConfigLoader.load(str(CONFIG_DIR / "hil.yaml"))


@pytest.fixture
def vil_config() -> PlatformConfig:
    return ConfigLoader.load(str(CONFIG_DIR / "vil.yaml"))


@pytest.fixture
def mil_adapter(mil_config: PlatformConfig):
    adapter = MatlabMilAdapter(mil_config)
    adapter.connect()
    yield adapter
    adapter.disconnect()


@pytest.fixture
def sil_adapter(sil_config: PlatformConfig):
    adapter = MatlabSilAdapter(sil_config)
    adapter.connect()
    yield adapter
    adapter.disconnect()


@pytest.fixture
def hil_adapter(hil_config: PlatformConfig):
    adapter = MatlabHilAdapter(hil_config)
    adapter.connect()
    yield adapter
    adapter.disconnect()


@pytest.fixture
def vil_adapter(vil_config: PlatformConfig):
    adapter = VehicleVilAdapter(vil_config)
    adapter.connect()
    yield adapter
    adapter.disconnect()


@pytest.fixture
def signal_recorder():
    recorder = SignalRecorder()
    recorder.start()
    yield recorder
    recorder.stop()
