import inspect
import math
import tomllib
from dataclasses import replace
from typing import Any

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
from mm.config import (
    DEFAULT_CONFIG_PATH,
    ToxicityConfig,
    build_config,
    load_config,
    scenario_names,
)
from mm.simulation import run_episode
from mm.types import Side

CONFIG = load_config()
SKEW, KALMAN = CONFIG.agent.skew, CONFIG.agent.kalman
TAU = 5
CENTRE = 10000
# The tests' own settings, so they do not depend on the tuned values in the config file.
TOXICITY = ToxicityConfig(
    base_half_spread=SKEW.half_spread,
    markout_horizon=TAU,
    widen_per_tick=1.0,
    ewma_halflife=10.0,
    max_half_spread=8,
)


def score(halflife: float = 10.0, tau: int = TAU) -> ToxicityScore:
    return ToxicityScore(replace(TOXICITY, markout_horizon=tau, ewma_halflife=halflife))


def toxic_score(halflife: float = 10.0) -> ToxicityScore:
    """A score after one 5-lot buy whose fair value fell a further 4 ticks after absorbing it."""
    s = score(halflife)
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))
    s.update(1 + TAU, (), CENTRE - 4.0)
    return s


def obs(
    step: int,
    position: int = 0,
    fills: tuple[OwnFill, ...] = (),
    posted: tuple[int | None, int | None] = (None, None),
) -> Observation:
    return Observation(step, position, 0, fills, (), CENTRE, posted[0], posted[1])


def episode_config(scenario: str = "toxic", n_steps: int = 500, seed: int = 3):
    config = replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)
    agent = replace(config.agent, type="toxicity", toxicity=TOXICITY)
    return replace(config, agent=agent)


def test_with_zero_widening_v3_quotes_exactly_as_v2():
    config = episode_config()
    no_widening = replace(TOXICITY, widen_per_tick=0.0)
    v2 = run_episode(config, KalmanMarketMaker(SKEW, KALMAN))
    v3 = run_episode(config, ToxicityMarketMaker(SKEW, KALMAN, no_widening))
    assert v3 == v2


def test_fill_whose_fair_value_jump_is_only_the_filters_own_reaction_scores_zero():
    agent = ToxicityMarketMaker(SKEW, KALMAN, TOXICITY)
    agent.quote(obs(0))
    # Ten lots bought: the filter reads taker selling and moves fv down as it absorbs the fill.
    absorbed = agent.quote(obs(1, 10, (OwnFill(Side.BUY, CENTRE, 10),), (CENTRE - 2, CENTRE + 2)))
    assert absorbed.fair_value < CENTRE - 1
    # No quotes rest afterwards, so the filter only predicts: fv does not drift after the jump.
    for step in range(2, 2 + TAU):
        quote = agent.quote(obs(step, 10))
    assert quote.fair_value == absorbed.fair_value
    assert agent.toxicity == 0.0
    assert agent.half_spread == TOXICITY.base_half_spread


def test_continued_same_direction_drift_after_a_buy_scores_negative():
    agent = ToxicityMarketMaker(SKEW, KALMAN, TOXICITY)
    agent.quote(obs(0))
    posted = (CENTRE - 2, CENTRE + 2)
    reference = agent.quote(obs(1, 5, (OwnFill(Side.BUY, CENTRE, 5),), posted)).fair_value
    # We keep buying: the takers keep selling, so fv keeps falling after the first fill.
    for step in range(2, 2 + TAU):
        quote = agent.quote(obs(step, 5 * step, (OwnFill(Side.BUY, CENTRE - 2, 5),), posted))
    assert quote.fair_value < reference
    assert agent.toxicity > 0


def test_buy_followed_by_a_further_fair_value_fall_raises_toxicity():
    s = toxic_score()
    # One fill from a = 0: a = (1 - d^5) * (-4) with d = 0.5^(1/10).
    assert s.value == pytest.approx(4 * (1 - 0.5**0.5))


def test_sell_followed_by_a_further_fair_value_rise_raises_toxicity():
    s = score()
    s.update(1, (OwnFill(Side.SELL, CENTRE, 5),), float(CENTRE))
    s.update(1 + TAU, (), CENTRE + 4.0)
    assert s.value == pytest.approx(4 * (1 - 0.5**0.5))


def test_markout_is_measured_from_the_absorbed_fair_value_not_the_fill_price():
    cheap, dear = score(), score()
    cheap.update(1, (OwnFill(Side.BUY, CENTRE - 10, 5),), float(CENTRE))
    dear.update(1, (OwnFill(Side.BUY, CENTRE + 10, 5),), float(CENTRE))
    for s in (cheap, dear):
        s.update(1 + TAU, (), CENTRE - 4.0)
    assert cheap.value == dear.value > 0


def test_favourable_drift_keeps_toxicity_at_zero():
    s = score()
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))
    s.update(2, (OwnFill(Side.SELL, CENTRE, 5),), CENTRE + 2.0)
    s.update(1 + TAU, (), CENTRE + 2.0)  # the buy's fv rose by 2 after it
    s.update(2 + TAU, (), float(CENTRE))  # the sell's fv fell by 2 after it
    assert s.pending == 0
    assert s.value == 0.0


def test_pending_fills_are_not_scored_before_the_horizon():
    s = score()
    s.update(1, (OwnFill(Side.BUY, CENTRE, 5),), float(CENTRE))  # reported in observation 1
    for now in range(2, 1 + TAU):
        s.update(now, (), CENTRE - 10.0)
        assert (s.pending, s.value) == (1, 0.0)
    s.update(1 + TAU, (), CENTRE - 10.0)  # τ observations after it arrived
    assert s.pending == 0 and s.value > 0


def test_markout_uses_the_fair_value_at_maturity_not_later():
    s = toxic_score()
    matured = s.value
    s.update(2 + TAU, (), CENTRE - 40.0)
    assert s.value == matured


def test_toxicity_halves_after_one_halflife_of_break_even_fills():
    s = toxic_score(10.0)
    before = s.value
    # Two 5-lot fills whose fv does not move afterwards: 10 lots = one half-life.
    now = 2 + TAU
    s.update(now, (OwnFill(Side.BUY, CENTRE, 5), OwnFill(Side.SELL, CENTRE, 5)), float(CENTRE))
    s.update(now + TAU, (), float(CENTRE))
    assert s.value == pytest.approx(before / 2)


def test_favourable_fills_bring_toxicity_down_at_least_as_fast_as_the_halflife():
    s = toxic_score(10.0)
    before = s.value
    s.update(2 + TAU, (OwnFill(Side.BUY, CENTRE, 10),), float(CENTRE))
    s.update(2 + 2 * TAU, (), CENTRE + 1.0)
    assert s.value < before / 2


@pytest.mark.parametrize("base", [1, 2, 4])
@pytest.mark.parametrize("toxicity", [0.0, 0.4, 1.0, 2.6, 10.0, 1e6])
def test_half_spread_stays_between_base_and_max(base, toxicity):
    config = replace(TOXICITY, base_half_spread=base, widen_per_tick=2.0)
    half = widened_half_spread(config, toxicity)
    assert base <= half <= config.max_half_spread
    assert half == min(max(math.floor(base + 2.0 * toxicity + 0.5), base), 8)


def test_base_half_spread_comes_from_the_toxicity_section_not_skew():
    wide = replace(TOXICITY, base_half_spread=4, widen_per_tick=0.0)
    v2 = KalmanMarketMaker(SKEW, KALMAN).quote(obs(0))
    v3 = ToxicityMarketMaker(SKEW, KALMAN, wide).quote(obs(0))
    assert v2.bid_price is not None and v2.ask_price is not None
    assert (v3.bid_price, v3.ask_price) == (v2.bid_price - 2, v2.ask_price + 2)


def test_widened_quotes_are_symmetric_about_v2s_reservation_price():
    widening = replace(TOXICITY, widen_per_tick=8.0)
    v2 = KalmanMarketMaker(SKEW, KALMAN)
    v3 = ToxicityMarketMaker(SKEW, KALMAN, widening)
    posted = (CENTRE - 2, CENTRE + 2)
    for agent in (v2, v3):
        agent.quote(obs(0))
    for step in range(1, 2 + TAU):  # keep buying, so fv keeps falling after each fill
        fills = (OwnFill(Side.BUY, CENTRE - 2, 5),)
        a, b = v2.quote(obs(step, 20, fills, posted)), v3.quote(obs(step, 20, fills, posted))
    assert v3.toxicity > 0
    assert widening.base_half_spread < v3.half_spread <= widening.max_half_spread
    assert a.bid_price is not None and a.ask_price is not None
    assert b.bid_price is not None and b.ask_price is not None
    assert b.bid_price + b.ask_price == a.bid_price + a.ask_price
    assert b.ask_price - b.bid_price == 2 * v3.half_spread
    assert b.fair_value == a.fair_value


def test_agent_restarts_its_score_at_step_zero():
    agent = ToxicityMarketMaker(SKEW, KALMAN, replace(TOXICITY, markout_horizon=1))
    agent.quote(obs(0))
    posted = (CENTRE - 2, CENTRE + 2)
    agent.quote(obs(1, 10, (OwnFill(Side.BUY, CENTRE, 10),), posted))
    agent.quote(obs(2, 20, (OwnFill(Side.BUY, CENTRE - 2, 10),), posted))
    assert agent.toxicity > 0
    agent.quote(obs(0))
    assert (agent.toxicity, agent.half_spread) == (0.0, TOXICITY.base_half_spread)


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
    config = episode_config(scenario, n_steps=CONFIG.n_steps)
    widening = replace(TOXICITY, widen_per_tick=8.0, base_half_spread=3)
    config = replace(config, agent=replace(config.agent, toxicity=widening))
    result = run_episode(config)  # the monitor halts the run on any violation
    assert len(result.steps) == CONFIG.n_steps


def test_full_episode_is_deterministic():
    assert run_episode(episode_config()) == run_episode(episode_config())


def test_registry_builds_the_toxicity_agent():
    assert "toxicity" in AGENT_NAMES
    assert isinstance(make_agent(episode_config()), ToxicityMarketMaker)


def test_registry_builds_the_tuned_spread_control_as_v2_with_its_own_half_spread():
    config = replace(CONFIG, agent=replace(CONFIG.agent, type="kalman_tuned"))
    config = replace(
        config,
        agent=replace(config.agent, kalman_tuned=replace(CONFIG.agent.kalman_tuned, half_spread=5)),
    )
    control = make_agent(config)
    assert isinstance(control, KalmanMarketMaker)
    v2 = KalmanMarketMaker(replace(SKEW, half_spread=5), KALMAN)
    assert control.quote(obs(0)) == v2.quote(obs(0))
    assert CONFIG.agent.skew.half_spread == 2  # v1 and v2 keep their own setting


def raw_config() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("base_half_spread", 0, "base_half_spread must be >= 1"),
        ("markout_horizon", 0, "markout_horizon must be >= 1"),
        ("widen_per_tick", -0.5, "widen_per_tick must be >= 0"),
        ("ewma_halflife", 0.0, "ewma_halflife must be > 0"),
        ("max_half_spread", 1, "max_half_spread must be >= base_half_spread"),
    ],
)
def test_toxicity_config_rejects_out_of_range_values(key, value, message):
    raw = raw_config()
    raw["agent"]["toxicity"]["base_half_spread"] = 2
    raw["agent"]["toxicity"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_kalman_tuned_half_spread_must_be_positive():
    raw = raw_config()
    raw["agent"]["kalman_tuned"]["half_spread"] = 0
    with pytest.raises(ValueError, match="kalman_tuned half_spread must be >= 1"):
        build_config(raw)


@pytest.mark.parametrize(("table", "key"), [("toxicity", "halflife"), ("kalman_tuned", "spread")])
def test_unknown_key_in_the_new_sections_is_rejected_by_name(table, key):
    raw = raw_config()
    raw["agent"][table][key] = 1
    with pytest.raises(ValueError, match=f"unknown config key 'agent.{table}.{key}'"):
        build_config(raw)


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ("toxicity", "base_half_spread"),
        ("toxicity", "markout_horizon"),
        ("toxicity", "widen_per_tick"),
        ("toxicity", "ewma_halflife"),
        ("toxicity", "max_half_spread"),
        ("kalman_tuned", "half_spread"),
    ],
)
def test_missing_key_in_the_new_sections_is_rejected_by_name(table, key):
    raw = raw_config()
    del raw["agent"][table][key]
    with pytest.raises(ValueError, match=f"missing config key 'agent.{table}.{key}'"):
        build_config(raw)


@pytest.mark.parametrize(
    ("key", "value"),
    [("markout_horizon", 5.5), ("max_half_spread", "8"), ("base_half_spread", 2.0)],
)
def test_toxicity_integer_keys_must_be_integers(key, value):
    raw = raw_config()
    raw["agent"]["toxicity"][key] = value
    with pytest.raises(ValueError, match=f"'agent.toxicity.{key}' must be an integer"):
        build_config(raw)
