import dataclasses
from dataclasses import replace

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mm.agent import Observation, OwnFill, Quote, Trade
from mm.config import SimConfig, load_config, scenario_names
from mm.simulation import run_episode
from mm.types import Side

SHORT = 300


def config(scenario: str = "base", seed: int = 0, n_steps: int = SHORT) -> SimConfig:
    return replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)


def test_same_seed_gives_identical_results():
    assert run_episode(config(seed=7)) == run_episode(config(seed=7))


def test_different_seed_gives_different_results():
    assert run_episode(config(seed=7)) != run_episode(config(seed=8))


def test_observation_exposes_no_true_value_or_taker_kind():
    names = {f.name for f in dataclasses.fields(Observation)}
    assert names == {
        "step",
        "position",
        "cash",
        "own_fills",
        "last_step_trades",
        "last_trade_price",
        "posted_bid",
        "posted_ask",
    }
    assert {f.name for f in dataclasses.fields(OwnFill)} == {"side", "price", "size"}
    assert {f.name for f in dataclasses.fields(Trade)} == {"price", "size"}


@pytest.mark.parametrize("scenario", scenario_names())
def test_every_scenario_runs_without_invariant_violation(scenario):
    result = run_episode(config(scenario, n_steps=1000))
    assert len(result.steps) == 1000


def test_final_pnl_marks_inventory_at_final_true_value():
    cfg = config()
    result = run_episode(cfg)
    expected = result.final_cash + result.final_position * result.path[cfg.n_steps]
    assert result.final_pnl == pytest.approx(expected)
    assert result.final_position == result.steps[-1].position
    assert result.final_cash == result.steps[-1].cash


def test_toxic_scenario_produces_informed_fills():
    result = run_episode(config("toxic"))
    assert any(fill.taker_kind == "informed" for fill in result.fills)


def test_first_observation_centres_on_initial_value():
    seen: list[Observation] = []

    class Recorder:
        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            return Quote(obs.last_trade_price - 2, 5, obs.last_trade_price + 2, 5, 0.0)

    run_episode(config(n_steps=50), agent=Recorder())
    assert seen[0].last_trade_price == load_config().instrument.initial_price_ticks
    assert seen[0].own_fills == ()


def test_observation_reports_previous_step_fills_from_agent_side():
    seen: list[Observation] = []

    class Recorder:
        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            return Quote(obs.last_trade_price - 2, 5, obs.last_trade_price + 2, 5, 0.0)

    result = run_episode(config(n_steps=200), agent=Recorder())
    fill = result.fills[0]
    obs = seen[fill.step + 1]
    assert OwnFill(fill.side, fill.price, fill.size) in obs.own_fills
    assert Trade(fill.price, fill.size) in obs.last_step_trades


def test_observation_reports_previous_step_posted_quotes_after_the_gate():
    seen: list[Observation] = []

    class Recorder:
        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            return Quote(obs.last_trade_price - 1, 5, obs.last_trade_price + 1, 5, 0.0)

    cfg = config(n_steps=300)
    cfg = replace(cfg, risk=replace(cfg.risk, position_limit=5))
    result = run_episode(cfg, agent=Recorder())
    assert (seen[0].posted_bid, seen[0].posted_ask) == (None, None)
    for t in range(1, cfg.n_steps):
        previous = result.steps[t - 1]
        assert (seen[t].posted_bid, seen[t].posted_ask) == (previous.bid_price, previous.ask_price)
    # At the limit the position clip drops a side; the next observation shows it as None.
    drops = [
        e
        for e in result.gate_events
        if e.event.detail.endswith("clipped to 0") and e.step < cfg.n_steps - 1
    ]
    assert drops
    for entry in drops:
        obs = seen[entry.step + 1]
        assert (obs.posted_bid if entry.event.side is Side.BUY else obs.posted_ask) is None


def test_step_record_logs_the_agents_fair_value():
    class Reporter:
        def quote(self, obs: Observation) -> Quote:
            return Quote(None, 0, None, 0, fair_value=obs.step + 0.5)

    result = run_episode(config(n_steps=10), agent=Reporter())
    assert [step.fair_value for step in result.steps] == [t + 0.5 for t in range(10)]


def test_gate_rejections_are_logged_and_never_reach_the_book():
    class Crosser:
        def quote(self, obs: Observation) -> Quote:
            return Quote(obs.last_trade_price, 5, obs.last_trade_price, 5, 0.0)

    result = run_episode(config(n_steps=20), agent=Crosser())
    assert len(result.gate_events) == 40
    assert result.fills == []
    assert all(step.bid_price is None and step.ask_price is None for step in result.steps)


@settings(max_examples=25, deadline=None)
@given(
    seed=st.integers(min_value=0, max_value=10_000),
    position_limit=st.integers(min_value=1, max_value=20),
    quote_size=st.integers(min_value=1, max_value=10),
    half_spread=st.integers(min_value=1, max_value=5),
    informed_share=st.floats(min_value=0.0, max_value=0.4),
)
def test_position_never_exceeds_limit(
    seed, position_limit, quote_size, half_spread, informed_share
):
    base = load_config()
    cfg = replace(
        base,
        market=replace(base.market, informed=replace(base.market.informed, share=informed_share)),
        agent=replace(
            base.agent,
            naive=replace(base.agent.naive, half_spread=half_spread, quote_size=quote_size),
        ),
        risk=replace(base.risk, position_limit=position_limit),
        n_steps=200,
        seed=seed,
    )
    result = run_episode(cfg)
    assert all(abs(step.position) <= position_limit for step in result.steps)
