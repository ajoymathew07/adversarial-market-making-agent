"""v6 competitive agent (decision 13): v5 plus a base half-spread narrowed by its volume share."""

import tomllib
from dataclasses import replace
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from mm.agent import AGENT_NAMES, AdaptiveMarketMaker, Observation, OwnFill, Trade, make_agent
from mm.agent.competition import VolumeShare, competitive_base
from mm.config import (
    DEFAULT_CONFIG_PATH,
    CompetitionConfig,
    CompetitiveConfig,
    SimConfig,
    build_config,
    load_config,
    scenario_names,
)
from mm.eval.recording import RecordingAgent
from mm.simulation import run_episode
from mm.types import Side

CONFIG = load_config()
# The tests' own settings, so they do not depend on the tuned values in the config file.
UNDERCUT = CompetitionConfig(share_halflife=50.0, undercut_per_share=4.0, min_half_spread=2)


def competitive_config(
    competition: CompetitionConfig = UNDERCUT,
    scenario: str = "base",
    n_steps: int = 1000,
    seed: int = 4,
) -> SimConfig:
    config = replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)
    competitive = CompetitiveConfig(final=config.agent.final, competition=competition)
    return replace(config, agent=replace(config.agent, type="competitive", competitive=competitive))


def recorded(config: SimConfig) -> RecordingAgent:
    agent = RecordingAgent(make_agent(config))
    run_episode(config, agent)
    return agent


@pytest.mark.parametrize("scenario", ["no_informed", "base", "toxic", "vs_v1", "realistic_mix"])
def test_competitive_agent_with_zero_undercut_equals_v5(scenario):
    config = competitive_config(replace(UNDERCUT, undercut_per_share=0.0), scenario)
    v5 = replace(config, agent=replace(config.agent, type="final"))
    assert run_episode(config) == run_episode(v5)


def test_undercut_changes_the_quotes_against_a_tighter_rival():
    off = competitive_config(replace(UNDERCUT, undercut_per_share=0.0), "vs_v1")
    assert run_episode(competitive_config(scenario="vs_v1")) != run_episode(off)


def test_share_is_one_before_any_trade():
    assert VolumeShare(50.0).value == 1.0


def test_share_drops_when_public_trades_exceed_own_fills_and_recovers():
    share = VolumeShare(10.0)
    for _ in range(50):
        share.update(own_lots=5, public_lots=5)
    assert share.value == pytest.approx(1.0)
    for _ in range(50):
        share.update(own_lots=1, public_lots=5)
    low = share.value
    assert low < 0.3
    for _ in range(100):
        share.update(own_lots=5, public_lots=5)
    assert share.value > 0.95 > low


@pytest.mark.parametrize("scenario", ["no_informed", "base", "toxic"])
def test_share_is_exactly_one_when_alone_so_the_base_never_moves(scenario):
    agent = recorded(competitive_config(scenario=scenario))
    assert set(agent.share) == {1.0}
    assert set(agent.effective_base) == {CONFIG.agent.final.base_half_spread}


def test_share_falls_and_the_base_narrows_against_a_tighter_rival():
    agent = recorded(competitive_config(scenario="vs_v1"))
    assert min(agent.share) < 0.5
    assert min(agent.effective_base) < CONFIG.agent.final.base_half_spread


@given(
    base=st.integers(1, 10),
    share=st.floats(0.0, 1.0),
    undercut=st.floats(0.0, 20.0),
    floor=st.integers(1, 10),
)
def test_effective_base_stays_between_the_minimum_and_the_base(base, share, undercut, floor):
    floor = min(floor, base)
    config = CompetitionConfig(50.0, undercut, floor)
    assert floor <= competitive_base(base, share, config) <= base


def test_effective_base_in_a_full_episode_stays_in_range():
    config = competitive_config(scenario="vs_v1")
    agent = recorded(config)
    base = config.agent.competitive.final.base_half_spread
    assert set(agent.effective_base) <= set(range(UNDERCUT.min_half_spread, base + 1))
    assert min(agent.half_spreads) >= UNDERCUT.min_half_spread


def observations() -> list[Observation]:
    """A fixed observation stream with fills and public trades, ours a third of the volume."""
    stream = []
    for step in range(300):
        fills = (OwnFill(Side.BUY, 9999, 1),) if step % 3 == 1 else ()
        trades = (Trade(10000, 1),) * (1 + step % 2) + tuple(Trade(f.price, 1) for f in fills)
        posted = None if step == 0 else 9995
        stream.append(
            Observation(step, 0, 0, fills, trades, 10000, posted, None if step == 0 else 10005)
        )
    return stream


def test_agent_reads_no_market_parameters_or_competitor_identity():
    # Same agent sections, very different market and competitor: identical quotes.
    config = competitive_config(scenario="vs_v1")
    other = load_config(scenario="toxic")
    market = replace(
        other.market,
        competitor="kalman_tuned",
        noise=replace(other.market.noise, rate=3.0),
        true_value=replace(other.market.true_value, sigma=4.0),
    )
    changed = replace(config, market=market, seed=99)
    agents = [make_agent(c) for c in (config, changed)]
    for obs in observations():
        assert agents[0].quote(obs) == agents[1].quote(obs)


@pytest.mark.parametrize("scenario", scenario_names())
def test_invariant_monitor_passes_a_full_episode_in_every_scenario(scenario):
    config = competitive_config(scenario=scenario, n_steps=CONFIG.n_steps, seed=1000)
    result = run_episode(config)  # the monitor halts the run on any violation
    assert len(result.steps) == CONFIG.n_steps
    if result.competitor is not None:
        assert len(result.competitor.steps) == CONFIG.n_steps


def test_registry_builds_the_competitive_agent():
    assert "competitive" in AGENT_NAMES
    assert isinstance(make_agent(competitive_config()), AdaptiveMarketMaker)


def test_competitive_section_repeats_v5s_knobs():
    assert CONFIG.agent.competitive.final == CONFIG.agent.final


def raw_config() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


def test_unknown_key_in_the_competitive_section_is_rejected_by_name():
    raw = raw_config()
    raw["agent"]["competitive"]["d"] = 1
    with pytest.raises(ValueError, match="unknown config key 'agent.competitive.d'"):
        build_config(raw)


@pytest.mark.parametrize("key", list(raw_config()["agent"]["competitive"]))
def test_missing_key_in_the_competitive_section_is_rejected_by_name(key):
    raw = raw_config()
    del raw["agent"]["competitive"][key]
    with pytest.raises(ValueError, match=f"missing config key 'agent.competitive.{key}'"):
        build_config(raw)


def test_competitive_min_half_spread_must_be_an_integer():
    raw = raw_config()
    raw["agent"]["competitive"]["min_half_spread"] = 2.0
    with pytest.raises(ValueError, match="'agent.competitive.min_half_spread' must be an integer"):
        build_config(raw)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("share_halflife", 0.0, "share_halflife must be > 0"),
        ("undercut_per_share", -1.0, "undercut_per_share must be >= 0"),
        ("min_half_spread", 0, "min_half_spread must be >= 1"),
        ("min_half_spread", 9, "min_half_spread must be <= base_half_spread"),
        ("base_half_spread", 0, "half_spread must be >= 1"),
    ],
)
def test_competitive_config_rejects_out_of_range_values(key, value, message):
    raw = raw_config()
    raw["agent"]["competitive"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)
