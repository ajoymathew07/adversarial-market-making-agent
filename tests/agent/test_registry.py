from dataclasses import replace

import pytest

from mm.agent import AGENT_NAMES, NaiveMarketMaker, make_agent
from mm.config import load_config

AGENT = load_config().agent


def test_registry_builds_the_named_agent_from_its_section():
    agent = make_agent(AGENT)
    assert isinstance(agent, NaiveMarketMaker)
    assert "naive" in AGENT_NAMES


def test_unknown_agent_type_error_lists_valid_names():
    with pytest.raises(ValueError, match="unknown agent type 'naiv'; known: naive"):
        make_agent(replace(AGENT, type="naiv"))
