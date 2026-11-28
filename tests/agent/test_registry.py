from dataclasses import replace

import pytest

from mm.agent import AGENT_NAMES, InventorySkewMarketMaker, NaiveMarketMaker, make_agent
from mm.config import load_config

AGENT = load_config().agent


def test_registry_builds_the_named_agent_from_its_section():
    assert isinstance(make_agent(replace(AGENT, type="naive")), NaiveMarketMaker)
    assert "naive" in AGENT_NAMES


def test_unknown_agent_type_error_lists_valid_names():
    with pytest.raises(ValueError, match="unknown agent type 'naiv'; known: naive, skew, kalman"):
        make_agent(replace(AGENT, type="naiv"))


def test_registry_builds_the_skew_agent():
    assert "skew" in AGENT_NAMES
    assert isinstance(make_agent(replace(AGENT, type="skew")), InventorySkewMarketMaker)
