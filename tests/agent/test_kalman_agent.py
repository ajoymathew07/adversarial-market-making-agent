import inspect
import math
import tomllib
from dataclasses import replace
from itertools import pairwise

import pytest

import mm.agent.kalman as kalman_module
from mm.agent import AGENT_NAMES, KalmanMarketMaker, Observation, OwnFill, Quote, make_agent
from mm.agent.kalman import (
    KalmanFairValue,
    expected_flow,
    net_taker_buys,
    steady_state,
    symmetric_steady_state,
)
from mm.config import DEFAULT_CONFIG_PATH, KalmanConfig, build_config, load_config
from mm.simulation import run_episode
from mm.types import Side

CONFIG = load_config()
KALMAN = CONFIG.agent.kalman
SKEW = CONFIG.agent.skew
CENTRE = 10000


def observation(
    step: int = 1,
    position: int = 0,
    fills: tuple[OwnFill, ...] = (),
    posted: tuple[int | None, int | None] = (CENTRE - 2, CENTRE + 2),
) -> Observation:
    return Observation(
        step=step,
        position=position,
        cash=0,
        own_fills=fills,
        last_step_trades=(),
        last_trade_price=CENTRE,
        posted_bid=posted[0],
        posted_ask=posted[1],
    )


def warmed_filter(steps: int = 5) -> KalmanFairValue:
    """A filter with some variance, sitting at CENTRE with symmetric quotes."""
    fv = KalmanFairValue(KALMAN, float(CENTRE))
    for _ in range(steps):
        fv.update(0, CENTRE - 2, CENTRE + 2)
    return fv


def test_theory_steady_state_matches_the_hand_numbers():
    # Round textbook values (σ = λ = 1, sizes uniform 1..5, e^(−2k) = 0.3), not the config's.
    textbook = KalmanConfig(1.0, 1.0, 3.0, 11.0, k=-math.log(0.30) / 2, gain_scale=1.0)
    state = symmetric_steady_state(textbook, half_spread=2)
    flow = expected_flow(textbook, 0.0, -2, 2)
    assert flow.slope == pytest.approx(0.54, abs=0.005)  # λ s̄ k e^(−2k)
    assert flow.variance == pytest.approx(3.3)  # λ E[s²] e^(−2k)
    assert state.gain == pytest.approx(0.47, abs=0.01)
    assert state.error_std == pytest.approx(1.7, abs=0.01)


def test_iterating_the_filter_with_fixed_h_and_r_converges_to_the_steady_state():
    # Symmetric quotes around fv and zero innovation keep fv, H and R fixed.
    fv = KalmanFairValue(KALMAN, float(CENTRE))
    for _ in range(200):
        fv.update(0, CENTRE - 2, CENTRE + 2)
    state = symmetric_steady_state(KALMAN, half_spread=2)
    assert fv.value == CENTRE
    assert fv.variance == pytest.approx(state.posterior_variance, rel=1e-9)
    fv.update(1, CENTRE - 2, CENTRE + 2)  # one net lot of taker buying moves fv by the gain
    assert fv.value - CENTRE == pytest.approx(state.gain, rel=1e-9)


def test_steady_state_needs_a_positive_slope():
    with pytest.raises(ValueError, match="positive slope"):
        steady_state(0.0, 1.0, 1.0)


def test_zero_innovation_leaves_fair_value_unchanged():
    fv = warmed_filter()
    flow = expected_flow(KALMAN, fv.value, CENTRE - 3, CENTRE + 1)  # asymmetric quotes, h != 0
    assert flow.mean != 0
    before = fv.value
    fv.update(flow.mean, CENTRE - 3, CENTRE + 1)
    assert fv.value == pytest.approx(before, abs=1e-12)


def test_taker_buy_excess_moves_fair_value_up_and_sell_excess_moves_it_down():
    up, down = warmed_filter(), warmed_filter()
    up.update(5, CENTRE - 2, CENTRE + 2)
    down.update(-5, CENTRE - 2, CENTRE + 2)
    assert up.value > CENTRE > down.value
    assert up.value - CENTRE == pytest.approx(CENTRE - down.value)


def test_flow_equal_to_the_skewed_expectation_does_not_move_fair_value():
    # Long: quotes shifted down 3 ticks, so taker buys are expected. Exactly that flow is no news.
    fv = warmed_filter()
    bid, ask = CENTRE - 5, CENTRE - 1
    expected = expected_flow(KALMAN, fv.value, bid, ask)
    assert expected.mean > 1  # the skew makes us expect net taker buying
    fv.update(expected.mean, bid, ask)
    assert fv.value == pytest.approx(CENTRE, abs=1e-12)
    # The same flow read against symmetric quotes would have moved fv up.
    naive = warmed_filter()
    naive.update(expected.mean, CENTRE - 2, CENTRE + 2)
    assert naive.value > CENTRE + 0.25


def test_missing_side_contributes_nothing():
    only_ask = expected_flow(KALMAN, CENTRE, None, CENTRE + 2)
    both = expected_flow(KALMAN, CENTRE, CENTRE - 2, CENTRE + 2)
    p = math.exp(-2 * KALMAN.k)
    assert only_ask.mean == pytest.approx(KALMAN.noise_rate / 2 * KALMAN.mean_size * p)
    assert only_ask.slope == pytest.approx(both.slope / 2)
    assert only_ask.variance == pytest.approx(both.variance / 2)
    only_bid = expected_flow(KALMAN, CENTRE, CENTRE - 2, None)
    assert only_bid.mean == pytest.approx(-only_ask.mean)


def test_a_one_sided_ask_below_fair_value_still_has_slope_and_moves_fair_value():
    # At the long limit the gate drops the bid and the skew pushes the ask below fv. The rate is
    # an uncapped intensity, so it exceeds λ/2 there and still responds to fv.
    ask = CENTRE - 1
    flow = expected_flow(KALMAN, CENTRE, None, ask)
    rate = math.exp(KALMAN.k)
    assert rate > 1
    assert flow.mean == pytest.approx(KALMAN.noise_rate / 2 * KALMAN.mean_size * rate)
    assert flow.slope == pytest.approx(KALMAN.k * flow.mean)
    assert flow.slope > 0
    fv = warmed_filter()
    fv.update(0, None, ask)  # fewer taker buys than expected: fv falls
    assert fv.value < CENTRE


def test_agent_held_at_the_position_limit_keeps_updating_and_leaves_it():
    # Regression for the filter lock: a 10-lot limit and strong skew (dev seed 7, toxic) push the
    # agent to the limit with its only quote through fv. With a capped probability H was 0 there,
    # fv froze for 476 of 500 steps and the agent sat at the limit for 482.
    config = load_config(scenario="toxic")
    agent = replace(config.agent, type="kalman", skew=replace(config.agent.skew, skew_per_lot=0.3))
    config = replace(
        config, n_steps=500, seed=7, agent=agent, risk=replace(config.risk, position_limit=10)
    )
    steps = run_episode(config).steps
    at_limit = sum(abs(s.position) >= 10 for s in steps)
    assert at_limit > 0  # the scenario does reach the limit
    assert at_limit < 50
    longest_frozen = frozen = 0  # consecutive steps where fv did not change
    for before, after in pairwise(steps):
        frozen = frozen + 1 if after.fair_value == before.fair_value else 0
        longest_frozen = max(longest_frozen, frozen)
    assert longest_frozen < 20


def test_far_quotes_keep_the_variance_above_the_floor():
    flow = expected_flow(KALMAN, CENTRE, CENTRE - 500, CENTRE + 500)
    assert flow.variance == kalman_module.MIN_FLOW_VARIANCE


def test_gain_scale_zero_keeps_fair_value_at_the_initial_value():
    fv = KalmanFairValue(replace(KALMAN, gain_scale=0.0), float(CENTRE))
    for n in (5, -3, 10, 7):
        fv.update(n, CENTRE - 5, CENTRE - 1)
    assert fv.value == CENTRE


def test_no_posted_quotes_is_predict_only():
    fv = warmed_filter()
    value, variance = fv.value, fv.variance
    fv.update(0, None, None)
    assert fv.value == value
    assert fv.variance == pytest.approx(variance + KALMAN.sigma**2)


def test_net_taker_buys_is_lots_we_sold_minus_lots_we_bought():
    fills = (OwnFill(Side.SELL, CENTRE + 2, 4), OwnFill(Side.BUY, CENTRE - 2, 1))
    assert net_taker_buys(fills) == 3
    assert net_taker_buys(()) == 0


def test_agent_reports_the_filter_value_and_quotes_v1_skew_around_rounded_fair_value():
    agent = KalmanMarketMaker(SKEW, KALMAN)
    first = agent.quote(observation(step=0, posted=(None, None)))
    assert first == Quote(CENTRE - 2, 5, CENTRE + 2, 5, float(CENTRE))
    fills = (OwnFill(Side.SELL, CENTRE + 2, 5),) * 2  # 10 lots of taker buying
    quote = agent.quote(observation(step=1, position=-30, fills=fills))
    assert quote.fair_value > CENTRE + 1
    centre = math.floor(quote.fair_value + 0.5)
    shift = -2  # -30 lots * 0.05 = -1.5 -> -2, as in v1
    assert quote.bid_price == centre - shift - SKEW.half_spread
    assert quote.ask_price == centre - shift + SKEW.half_spread
    assert (quote.bid_size, quote.ask_size) == (SKEW.quote_size, SKEW.quote_size)


def test_agent_restarts_its_filter_at_step_zero():
    agent = KalmanMarketMaker(SKEW, KALMAN)
    agent.quote(observation(step=0, posted=(None, None)))
    agent.quote(observation(step=1, fills=(OwnFill(Side.SELL, CENTRE + 2, 5),)))
    assert agent.quote(observation(step=0, posted=(None, None))).fair_value == CENTRE


@pytest.mark.parametrize("half_spread", [1, 2, 5])
def test_quotes_never_self_cross(half_spread):
    agent = KalmanMarketMaker(replace(SKEW, half_spread=half_spread, skew_per_lot=0.5), KALMAN)
    agent.quote(observation(step=0, posted=(None, None)))
    for position in range(-50, 51, 5):
        for n in (-10, 0, 10):
            fills = (OwnFill(Side.SELL if n > 0 else Side.BUY, CENTRE, abs(n)),) if n else ()
            quote = agent.quote(observation(position=position, fills=fills))
            assert quote.bid_price is not None and quote.ask_price is not None
            assert quote.bid_price < quote.ask_price


def test_agent_uses_only_the_observation():
    # Replaying an episode's observations into a fresh agent reproduces every quote, so nothing
    # else (such as V) can feed the quotes; and the module imports nothing from the market.
    seen: list[Observation] = []
    quotes: list[Quote] = []

    class Recorder:
        def __init__(self) -> None:
            self.inner = KalmanMarketMaker(SKEW, KALMAN)

        def quote(self, obs: Observation) -> Quote:
            seen.append(obs)
            quotes.append(self.inner.quote(obs))
            return quotes[-1]

    run_episode(replace(load_config(scenario="toxic"), n_steps=300), agent=Recorder())
    fresh = KalmanMarketMaker(SKEW, KALMAN)
    assert [fresh.quote(obs) for obs in seen] == quotes
    source = inspect.getsource(kalman_module)
    assert "mm.market" not in source and "mm.simulation" not in source


def test_full_episode_is_deterministic():
    config = replace(load_config(scenario="toxic"), n_steps=500, seed=4)
    config = replace(config, agent=replace(config.agent, type="kalman"))
    assert run_episode(config) == run_episode(config)


def test_registry_has_kalman_and_default_type_stays_skew():
    assert "kalman" in AGENT_NAMES
    config = replace(CONFIG, agent=replace(CONFIG.agent, type="kalman"))
    assert isinstance(make_agent(config), KalmanMarketMaker)
    assert CONFIG.agent.type == "skew"


def test_kalman_config_loads_the_calibrated_values():
    assert (KALMAN.sigma, KALMAN.noise_rate, KALMAN.k, KALMAN.gain_scale) == (1.04, 1.01, 0.38, 1.0)
    assert (KALMAN.mean_size, KALMAN.mean_size_sq) == (3.5, 16.44)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("sigma", -1.0, "sigma must be >= 0"),
        ("noise_rate", 0.0, "noise_rate must be > 0"),
        ("mean_size", 0.0, "mean_size must be > 0"),
        ("mean_size_sq", 8.0, "mean_size_sq must be >= mean_size"),
        ("k", 0.0, "k must be > 0"),
        ("gain_scale", -0.5, "gain_scale must be >= 0"),
    ],
)
def test_kalman_config_rejects_out_of_range_values(key, value, message):
    raw = tomllib.loads(DEFAULT_CONFIG_PATH.read_text())
    raw["agent"]["kalman"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_unknown_kalman_key_is_rejected_by_name():
    raw = tomllib.loads(DEFAULT_CONFIG_PATH.read_text())
    raw["agent"]["kalman"]["gain"] = 1.0
    with pytest.raises(ValueError, match="'agent.kalman.gain'"):
        build_config(raw)
