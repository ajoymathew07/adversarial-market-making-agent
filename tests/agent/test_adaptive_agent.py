import inspect
import math
import tomllib
from dataclasses import replace
from typing import Any

import pytest

import mm.agent.adaptive as adaptive_module
from mm.agent import (
    AGENT_NAMES,
    AdaptiveMarketMaker,
    KalmanMarketMaker,
    Observation,
    OwnFill,
    Quote,
    make_agent,
)
from mm.agent.adaptive import FlowIntensity, uncertainty_half_spread
from mm.agent.kalman import KalmanFairValue, expected_flow
from mm.config import (
    DEFAULT_CONFIG_PATH,
    AdaptiveConfig,
    build_config,
    load_config,
    scenario_names,
)
from mm.simulation import run_episode
from mm.types import Side

CONFIG = load_config()
SKEW, KALMAN = CONFIG.agent.skew, CONFIG.agent.kalman
CENTRE = 10000
# The tests' own settings, so they do not depend on the tuned values in the config file.
ADAPTIVE = AdaptiveConfig(
    base_half_spread=3,
    uncertainty_weight=0.5,
    intensity_halflife=10.0,
    min_scale=0.25,
    max_scale=4.0,
    max_half_spread=8,
)
CONTROL_KNOBS = replace(
    ADAPTIVE, base_half_spread=4, uncertainty_weight=0.0, intensity_halflife=0.0
)


def obs(
    step: int,
    position: int = 0,
    fills: tuple[OwnFill, ...] = (),
    posted: tuple[int | None, int | None] = (None, None),
) -> Observation:
    return Observation(step, position, 0, fills, (), CENTRE, posted[0], posted[1])


def episode_config(scenario: str = "bursty_takers", n_steps: int = 500, seed: int = 3):
    config = replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)
    return replace(config, agent=replace(config.agent, type="adaptive", adaptive=ADAPTIVE))


@pytest.mark.parametrize("scenario", ["base", "toxic", "bursty_takers", "realistic_mix"])
def test_with_intensity_off_and_no_uncertainty_weight_it_quotes_exactly_as_kalman_tuned(scenario):
    config = episode_config(scenario, n_steps=1000)
    control = KalmanMarketMaker(replace(SKEW, half_spread=4), KALMAN)
    adaptive = AdaptiveMarketMaker(SKEW, KALMAN, CONTROL_KNOBS)
    assert run_episode(config, adaptive) == run_episode(config, control)


def test_registry_control_and_adaptive_with_control_knobs_give_identical_episodes():
    config = episode_config("base", n_steps=300)
    tuned = replace(config, agent=replace(config.agent, type="kalman_tuned"))
    control = replace(CONFIG.agent.kalman_tuned, half_spread=4)
    tuned = replace(tuned, agent=replace(tuned.agent, kalman_tuned=control))
    adaptive = replace(config, agent=replace(config.agent, adaptive=CONTROL_KNOBS))
    assert run_episode(adaptive) == run_episode(tuned)


def test_unit_rate_scale_leaves_the_flow_model_unchanged():
    assert expected_flow(KALMAN, 0.3, -4, 4, 1.0) == expected_flow(KALMAN, 0.3, -4, 4)


def test_rate_scale_multiplies_mean_slope_variance_and_lots():
    one, two = expected_flow(KALMAN, 0.3, -4, 3), expected_flow(KALMAN, 0.3, -4, 3, 2.0)
    for field in ("mean", "slope", "variance", "lots"):
        assert getattr(two, field) == pytest.approx(2 * getattr(one, field))


def test_expected_lots_is_the_total_fill_rate_of_both_sides():
    flow = expected_flow(KALMAN, 0.0, -4, 4)
    assert flow.lots == pytest.approx(flow.slope / KALMAN.k)
    assert expected_flow(KALMAN, 0.0, None, None).lots == 0.0


def test_rho_rises_when_observed_fills_exceed_expected_and_falls_back():
    rho = FlowIntensity(ADAPTIVE)
    assert rho.scale == 1.0  # nothing rested yet
    for _ in range(20):
        rho.update(observed_lots=2.0, expected_lots=1.0)
    high = rho.scale
    assert 1.5 < high <= 2.0
    for _ in range(40):
        rho.update(observed_lots=1.0, expected_lots=1.0)
    assert 1.0 <= rho.scale < 1.1 < high


def test_rho_halves_its_distance_to_the_new_ratio_after_one_halflife():
    rho = FlowIntensity(replace(ADAPTIVE, intensity_halflife=10.0))
    for _ in range(10):
        rho.update(2.0, 1.0)
    # O = 2(1 − 0.5) = 1, E = 1 − 0.5 = 0.5: equal decay keeps the ratio at exactly 2.
    assert rho.scale == pytest.approx(2.0)


@pytest.mark.parametrize(("observed", "bound"), [(100.0, 4.0), (0.0, 0.25)])
def test_rho_stays_within_its_clip(observed, bound):
    rho = FlowIntensity(ADAPTIVE)
    for _ in range(50):
        rho.update(observed, 1.0)
        assert ADAPTIVE.min_scale <= rho.scale <= ADAPTIVE.max_scale
    assert rho.scale == bound


def test_rho_is_one_when_intensity_is_off():
    rho = FlowIntensity(replace(ADAPTIVE, intensity_halflife=0.0))
    rho.update(100.0, 1.0)
    assert not rho.enabled and rho.scale == 1.0


@pytest.mark.parametrize("variance", [0.0, 0.5, 4.0, 9.0, 30.0, 1e6])
def test_spread_grows_with_variance_within_base_and_max(variance):
    half = uncertainty_half_spread(ADAPTIVE, variance)
    assert ADAPTIVE.base_half_spread <= half <= ADAPTIVE.max_half_spread
    assert half == min(math.floor(3 + 0.5 * math.sqrt(variance) + 0.5), 8)


def test_spread_is_monotone_in_variance():
    halves = [uncertainty_half_spread(ADAPTIVE, p) for p in range(400)]
    assert halves == sorted(halves)
    assert halves[0] == 3 and halves[-1] == 8


def test_agent_quotes_wider_as_its_filter_grows_less_certain():
    agent = AdaptiveMarketMaker(SKEW, KALMAN, replace(ADAPTIVE, uncertainty_weight=1.0))
    first = agent.quote(obs(0))
    assert agent.variance == pytest.approx(KALMAN.sigma**2)  # nothing rested: predict only
    for step in range(1, 30):  # nothing rests, so P grows by σ² each step
        quote = agent.quote(obs(step))
    assert agent.half_spread > uncertainty_half_spread(ADAPTIVE, 0.0)
    assert quote.ask_price is not None and quote.bid_price is not None
    assert first.ask_price is not None and first.bid_price is not None
    assert quote.ask_price - quote.bid_price > first.ask_price - first.bid_price


def test_more_fills_than_expected_raise_rho_and_the_filter_uses_the_previous_rho():
    agent = AdaptiveMarketMaker(SKEW, KALMAN, ADAPTIVE)
    agent.quote(obs(0))
    posted = (CENTRE - 3, CENTRE + 3)
    fills = (OwnFill(Side.BUY, CENTRE - 3, 5), OwnFill(Side.SELL, CENTRE + 3, 5))
    reference = KalmanFairValue(KALMAN, float(CENTRE))
    reference.update(0.0, None, None)  # step 0: nothing rested
    agent.quote(obs(1, 0, fills, posted))
    reference.update(0.0, *posted, rate_scale=1.0)  # ρ was 1 before this observation
    assert agent.variance == pytest.approx(reference.variance)
    assert agent.intensity_scale > 1


def test_agent_restarts_at_step_zero():
    agent = AdaptiveMarketMaker(SKEW, KALMAN, ADAPTIVE)
    agent.quote(obs(0))
    posted = (CENTRE - 3, CENTRE + 3)
    for step in range(1, 10):
        agent.quote(obs(step, 0, (OwnFill(Side.BUY, CENTRE - 3, 5),), posted))
    assert agent.intensity_scale != 1.0
    agent.quote(obs(0))
    assert agent.intensity_scale == 1.0
    assert agent.variance == pytest.approx(KALMAN.sigma**2)


def test_agent_is_built_from_agent_config_only_and_uses_only_the_observation():
    params = inspect.signature(AdaptiveMarketMaker).parameters
    annotations = [str(p.annotation) for p in params.values()]
    assert all("market" not in a.lower() for a in annotations)
    seen: list[Observation] = []
    quotes: list[Quote] = []

    class Recorder:
        def __init__(self) -> None:
            self.inner = AdaptiveMarketMaker(SKEW, KALMAN, ADAPTIVE)

        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            quotes.append(self.inner.quote(obs))
            return quotes[-1]

    run_episode(episode_config(n_steps=300), agent=Recorder())
    fresh = AdaptiveMarketMaker(SKEW, KALMAN, ADAPTIVE)
    assert [fresh.quote(o) for o in seen] == quotes
    source = inspect.getsource(adaptive_module)
    assert "mm.market" not in source and "mm.simulation" not in source
    assert "MarketConfig" not in source and "NoiseConfig" not in source


@pytest.mark.parametrize("scenario", scenario_names())
def test_invariant_monitor_passes_a_full_episode_in_every_scenario(scenario):
    wide = replace(ADAPTIVE, uncertainty_weight=2.0, intensity_halflife=5.0)
    config = episode_config(scenario, n_steps=CONFIG.n_steps)
    config = replace(config, agent=replace(config.agent, adaptive=wide))
    result = run_episode(config)  # the monitor halts the run on any violation
    assert len(result.steps) == CONFIG.n_steps


def test_full_episode_is_deterministic():
    assert run_episode(episode_config()) == run_episode(episode_config())


def test_registry_builds_the_adaptive_agent():
    assert "adaptive" in AGENT_NAMES
    assert isinstance(make_agent(episode_config()), AdaptiveMarketMaker)


def raw_config() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("base_half_spread", 0, "base_half_spread must be >= 1"),
        ("max_half_spread", 2, "max_half_spread must be >= base_half_spread"),
        ("uncertainty_weight", -0.1, "uncertainty_weight must be >= 0"),
        ("intensity_halflife", -1.0, "intensity_halflife must be >= 0"),
        ("min_scale", 0.0, "0 < min_scale <= 1 <= max_scale"),
        ("min_scale", 1.5, "0 < min_scale <= 1 <= max_scale"),
        ("max_scale", 0.5, "0 < min_scale <= 1 <= max_scale"),
    ],
)
def test_adaptive_config_rejects_out_of_range_values(key, value, message):
    raw = raw_config()
    raw["agent"]["adaptive"]["base_half_spread"] = 3
    raw["agent"]["adaptive"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_unknown_key_in_the_adaptive_section_is_rejected_by_name():
    raw = raw_config()
    raw["agent"]["adaptive"]["halflife"] = 1
    with pytest.raises(ValueError, match="unknown config key 'agent.adaptive.halflife'"):
        build_config(raw)


@pytest.mark.parametrize("key", list(raw_config()["agent"]["adaptive"]))
def test_missing_key_in_the_adaptive_section_is_rejected_by_name(key):
    raw = raw_config()
    del raw["agent"]["adaptive"][key]
    with pytest.raises(ValueError, match=f"missing config key 'agent.adaptive.{key}'"):
        build_config(raw)


@pytest.mark.parametrize(("key", "value"), [("base_half_spread", 3.0), ("max_half_spread", "8")])
def test_adaptive_integer_keys_must_be_integers(key, value):
    raw = raw_config()
    raw["agent"]["adaptive"][key] = value
    with pytest.raises(ValueError, match=f"'agent.adaptive.{key}' must be an integer"):
        build_config(raw)


def test_adaptive_section_has_exactly_the_documented_keys():
    assert set(raw_config()["agent"]["adaptive"]) == {
        "base_half_spread",
        "uncertainty_weight",
        "intensity_halflife",
        "min_scale",
        "max_scale",
        "max_half_spread",
    }
