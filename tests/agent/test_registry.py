from dataclasses import replace

import pytest

from mm.agent import (
    AGENT_NAMES,
    CalibrationMarketMaker,
    InventorySkewMarketMaker,
    NaiveMarketMaker,
    make_agent,
)
from mm.config import load_config

CONFIG = load_config()


def of_type(name: str):
    return replace(CONFIG, agent=replace(CONFIG.agent, type=name))


def test_registry_builds_the_named_agent_from_its_section():
    assert isinstance(make_agent(of_type("naive")), NaiveMarketMaker)
    assert "naive" in AGENT_NAMES


def test_unknown_agent_type_error_lists_valid_names():
    message = "unknown agent type 'naiv'; known: naive, skew, kalman, toxicity, calibration"
    with pytest.raises(ValueError, match=message):
        make_agent(of_type("naiv"))


def test_registry_builds_the_skew_agent():
    assert "skew" in AGENT_NAMES
    assert isinstance(make_agent(of_type("skew")), InventorySkewMarketMaker)


def test_registry_builds_the_calibration_agent():
    assert isinstance(make_agent(of_type("calibration")), CalibrationMarketMaker)
