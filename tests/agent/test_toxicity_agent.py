import inspect
import math
import tomllib
from dataclasses import replace

import pytest

import mm.agent.toxicity as toxicity_module
from mm.agent import (
    AGENT_NAMES,
    KalmanMarketMaker,
    Observation,
    OwnFill,
    Quote,
    ToxicityMarketMaker,
    make_agent,
)
from mm.agent.toxicity import ToxicityScore, widened_half_spread
from mm.config import DEFAULT_CONFIG_PATH, build_config, load_config, scenario_names
from mm.simulation import run_episode
from mm.types import Side

CONFIG = load_config()
SKEW, KALMAN, TOXICITY = CONFIG.agent.skew, CONFIG.agent.kalman, CONFIG.agent.toxicity
TAU = 5
CENTRE = 10000


def score(halflife: float = 10.0, tau: int = TAU) -> ToxicityScore:
    return ToxicityScore(replace(TOXICITY, markout_horizon=tau, ewma_halflife=halflife))


def toxic_score(halflife: float = 10.0) -> ToxicityScore:
    """A score after one 5-lot buy at CENTRE that is marked 4 ticks below the price."""
    s = score(halflife)
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))
    s.update(1 + TAU, (), CENTRE - 4.0)
    return s


def episode_config(scenario: str = "toxic", n_steps: int = 500, seed: int = 3):
    config = replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)
    return replace(config, agent=replace(config.agent, type="toxicity"))


def test_with_zero_widening_v3_quotes_exactly_as_v2():
    config = episode_config()
    no_widening = replace(TOXICITY, widen_per_tick=0.0)
    v2 = run_episode(config, KalmanMarketMaker(SKEW, KALMAN))
    v3 = run_episode(config, ToxicityMarketMaker(SKEW, KALMAN, no_widening))
    assert v3 == v2


def test_buy_followed_by_a_fair_value_fall_gives_negative_markout_and_raises_toxicity():
    s = toxic_score()
    assert s.value > 0
    # One fill from a = 0: a = (1 - d^5) * (-4) with d = 0.5^(1/10).
    assert s.value == pytest.approx(4 * (1 - 0.5**0.5))


def test_sell_followed_by_a_fair_value_rise_raises_toxicity():
    s = score()
    s.update(1, (OwnFill(Side.SELL, CENTRE, 5),), float(CENTRE))
    s.update(1 + TAU, (), CENTRE + 4.0)
    assert s.value == pytest.approx(4 * (1 - 0.5**0.5))


def test_favourable_fills_keep_toxicity_at_zero():
    s = score()
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5), OwnFill(Side.SELL, CENTRE + 4, 5)), float(CENTRE))
    s.update(1 + TAU, (), CENTRE + 2.0)  # bought below and sold above the later fair value
    assert s.pending == 0
    assert s.value == 0.0


def test_pending_fills_are_not_scored_before_the_horizon():
    s = score()
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))  # fill made at step 0
    for now in range(2, TAU):
        s.update(now, (), CENTRE - 10.0)
        assert (s.pending, s.value) == (1, 0.0)
    s.update(TAU, (), CENTRE - 10.0)  # τ steps after the fill
    assert s.pending == 0 and s.value > 0


def test_markout_uses_the_fair_value_at_maturity_not_later():
    s = score()
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))
    s.update(TAU, (), CENTRE - 4.0)
    matured = s.value
    s.update(TAU + 1, (), CENTRE - 40.0)
    assert s.value == matured


def test_toxicity_halves_after_one_halflife_of_break_even_fills():
    halflife = 10.0
    s = toxic_score(halflife)
    before = s.value
    # Two 5-lot fills that break even: 10 lots = one half-life.
    now = 1 + TAU
    s.update(now + 1, (OwnFill(Side.BUY, CENTRE, 5), OwnFill(Side.SELL, CENTRE, 5)), float(CENTRE))
    s.update(now + 1 + TAU, (), float(CENTRE))
    assert s.value == pytest.approx(before / 2)


def test_favourable_fills_bring_toxicity_down_at_least_as_fast_as_the_halflife():
    s = toxic_score(10.0)
    before = s.value
    s.update(TAU + 2, (OwnFill(Side.BUY, CENTRE, 10),), float(CENTRE))
    s.update(2 * TAU + 2, (), CENTRE + 1.0)
    assert s.value < before / 2


@pytest.mark.parametrize("toxicity", [0.0, 0.4, 1.0, 2.6, 10.0, 1e6])
def test_half_spread_stays_between_base_and_max(toxicity):
    config = replace(TOXICITY, widen_per_tick=2.0)
    half = widened_half_spread(SKEW.half_spread, config, toxicity)
    assert SKEW.half_spread <= half <= config.max_half_spread
    expected = min(max(math.floor(SKEW.half_spread + 2.0 * toxicity + 0.5), SKEW.half_spread), 8)
    assert half == expected


def test_widened_quotes_are_symmetric_about_v2s_reservation_price():
    widening = replace(TOXICITY, widen_per_tick=8.0, markout_horizon=TAU)
    v2 = KalmanMarketMaker(SKEW, KALMAN)
    v3 = ToxicityMarketMaker(SKEW, KALMAN, widening)

    def obs(step: int, position: int, fills: tuple[OwnFill, ...] = ()) -> Observation:
        return Observation(step, position, 0, fills, (), CENTRE, None, None)

    for agent in (v2, v3):
        agent.quote(obs(0, 0))
        agent.quote(obs(1, 5, (OwnFill(Side.BUY, CENTRE + 3, 5),)))  # bought above fv
    for step in range(2, 2 + TAU):
        a, b = v2.quote(obs(step, 20)), v3.quote(obs(step, 20))
    assert v3.toxicity > 0
    assert SKEW.half_spread < v3.half_spread <= widening.max_half_spread
    # Same reservation and fair value; v3 is only wider.
    assert a.bid_price is not None and a.ask_price is not None
    assert b.bid_price is not None and b.ask_price is not None
    assert b.bid_price + b.ask_price == a.bid_price + a.ask_price
    assert b.ask_price - b.bid_price == 2 * v3.half_spread
    assert b.fair_value == a.fair_value


def test_toxic_fill_widens_the_quote_by_c_times_toxicity():
    widening = replace(TOXICITY, widen_per_tick=4.0, markout_horizon=1, ewma_halflife=5.0)
    agent = ToxicityMarketMaker(SKEW, KALMAN, widening)
    agent.quote(Observation(0, 0, 0, (), (), CENTRE, None, None))
    # Ten lots bought: v2's filter reads it as taker selling, so its fv falls below the price.
    fills = (OwnFill(Side.BUY, CENTRE, 10),)
    quote = agent.quote(Observation(1, 10, 0, fills, (), CENTRE, CENTRE - 2, CENTRE + 2))
    assert quote.fair_value < CENTRE
    assert agent.toxicity == pytest.approx(0.75 * (CENTRE - quote.fair_value))
    assert agent.half_spread == widened_half_spread(SKEW.half_spread, widening, agent.toxicity)
    assert agent.half_spread > SKEW.half_spread


def test_agent_restarts_its_score_at_step_zero():
    widening = replace(TOXICITY, markout_horizon=1)
    agent = ToxicityMarketMaker(SKEW, KALMAN, widening)
    agent.quote(Observation(0, 0, 0, (), (), CENTRE, None, None))
    fills = (OwnFill(Side.BUY, CENTRE, 10),)
    agent.quote(Observation(1, 10, 0, fills, (), CENTRE, CENTRE - 2, CENTRE + 2))
    assert agent.toxicity > 0
    agent.quote(Observation(0, 0, 0, (), (), CENTRE, None, None))
    assert (agent.toxicity, agent.half_spread) == (0.0, SKEW.half_spread)


def test_agent_is_built_from_agent_config_only_and_uses_only_the_observation():
    # The constructor takes only [agent.*] sections; replaying the observations reproduces
    # every quote, so nothing else (such as V) can feed it; the module imports no market code.
    params = inspect.signature(ToxicityMarketMaker).parameters
    assert [p.annotation.__name__ for p in params.values()] == [
        "SkewConfig",
        "KalmanConfig",
        "ToxicityConfig",
    ]
    seen: list[Observation] = []
    quotes: list[Quote] = []
    widening = replace(TOXICITY, widen_per_tick=2.0)

    class Recorder:
        def __init__(self) -> None:
            self.inner = ToxicityMarketMaker(SKEW, KALMAN, widening)

        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            quotes.append(self.inner.quote(obs))
            return quotes[-1]

    run_episode(episode_config(n_steps=300), agent=Recorder())
    fresh = ToxicityMarketMaker(SKEW, KALMAN, widening)
    assert [fresh.quote(obs) for obs in seen] == quotes
    source = inspect.getsource(toxicity_module)
    assert "mm.market" not in source and "mm.simulation" not in source


@pytest.mark.parametrize("scenario", scenario_names())
def test_invariant_monitor_passes_a_full_episode_in_every_scenario(scenario):
    widening = replace(
        CONFIG.agent, type="toxicity", toxicity=replace(TOXICITY, widen_per_tick=8.0)
    )
    config = replace(episode_config(scenario, n_steps=CONFIG.n_steps), agent=widening)
    result = run_episode(config)  # the monitor halts the run on any violation
    assert len(result.steps) == CONFIG.n_steps


def test_full_episode_is_deterministic():
    assert run_episode(episode_config()) == run_episode(episode_config())


def test_registry_builds_the_toxicity_agent():
    assert "toxicity" in AGENT_NAMES
    assert isinstance(make_agent(episode_config()), ToxicityMarketMaker)


def raw_config() -> dict:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("markout_horizon", 0, "markout_horizon must be >= 1"),
        ("widen_per_tick", -0.5, "widen_per_tick must be >= 0"),
        ("ewma_halflife", 0.0, "ewma_halflife must be > 0"),
        ("max_half_spread", 1, "max_half_spread must be >= skew half_spread"),
    ],
)
def test_toxicity_config_rejects_out_of_range_values(key, value, message):
    raw = raw_config()
    raw["agent"]["toxicity"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_unknown_toxicity_key_is_rejected_by_name():
    raw = raw_config()
    raw["agent"]["toxicity"]["halflife"] = 50.0
    with pytest.raises(ValueError, match="unknown config key 'agent.toxicity.halflife'"):
        build_config(raw)


@pytest.mark.parametrize(
    "key", ["markout_horizon", "widen_per_tick", "ewma_halflife", "max_half_spread"]
)
def test_missing_toxicity_key_is_rejected_by_name(key):
    raw = raw_config()
    del raw["agent"]["toxicity"][key]
    with pytest.raises(ValueError, match=f"missing config key 'agent.toxicity.{key}'"):
        build_config(raw)


@pytest.mark.parametrize(("key", "value"), [("markout_horizon", 5.5), ("max_half_spread", "8")])
def test_toxicity_integer_keys_must_be_integers(key, value):
    raw = raw_config()
    raw["agent"]["toxicity"][key] = value
    with pytest.raises(ValueError, match=f"'agent.toxicity.{key}' must be an integer"):
        build_config(raw)
