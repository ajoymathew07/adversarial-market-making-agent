import math
from dataclasses import replace

import numpy as np
import pytest

from mm.config import MarketConfig, load_config
from mm.market import TakerIntent, generate_intents, generate_value_path
from mm.types import Side

BASE = load_config().market
V0 = load_config().instrument.initial_price_ticks


def market(
    rate: float = BASE.noise.rate,
    share: float = BASE.informed.share,
    lookahead: int = BASE.informed.lookahead,
) -> MarketConfig:
    return replace(
        BASE,
        noise=replace(BASE.noise, rate=rate),
        informed=replace(BASE.informed, share=share, lookahead=lookahead),
    )


def run_episode(config: MarketConfig, n_steps: int, seed: int) -> list[list[TakerIntent]]:
    rng = np.random.default_rng(seed)
    path = generate_value_path(config, V0, n_steps, rng)
    return [generate_intents(path, t, config, rng) for t in range(n_steps)]


def flat_path(value: float, config: MarketConfig, n_steps: int) -> np.ndarray:
    return np.full(n_steps + config.informed.lookahead + 1, value)


def test_same_seed_gives_identical_intents():
    config = market(share=0.4)
    assert run_episode(config, 300, seed=3) == run_episode(config, 300, seed=3)


def test_different_seed_gives_different_intents():
    config = market(share=0.4)
    assert run_episode(config, 300, seed=3) != run_episode(config, 300, seed=4)


def test_average_noise_count_matches_noise_rate():
    config = market(rate=1.5, share=0.0)
    steps = run_episode(config, 20_000, seed=5)
    mean_count = np.mean([len(step) for step in steps])
    assert mean_count == pytest.approx(1.5, rel=0.03)


@pytest.mark.parametrize("share", [0.15, 0.40])
def test_informed_fraction_of_takers_matches_configured_share(share):
    config = market(rate=2.0, share=share)
    intents = [i for step in run_episode(config, 20_000, seed=6) for i in step]
    informed = sum(i.kind == "informed" for i in intents)
    assert informed / len(intents) == pytest.approx(share, abs=0.01)


def test_zero_share_never_produces_informed_takers():
    config = market(rate=5.0, share=0.0)
    intents = [i for step in run_episode(config, 5_000, seed=7) for i in step]
    assert intents
    assert all(i.kind == "noise" for i in intents)


def test_sizes_stay_within_configured_ranges():
    config = market(rate=3.0, share=0.4)
    intents = [i for step in run_episode(config, 5_000, seed=8) for i in step]
    noise_sizes = {i.size for i in intents if i.kind == "noise"}
    informed_sizes = {i.size for i in intents if i.kind == "informed"}
    assert noise_sizes == set(range(1, 6))
    assert informed_sizes == set(range(5, 11))


def test_noise_sides_are_balanced():
    config = market(rate=5.0, share=0.0)
    intents = [i for step in run_episode(config, 5_000, seed=9) for i in step]
    assert np.mean([i.side is Side.BUY for i in intents]) == pytest.approx(0.5, abs=0.02)


def noise_intents_at(value: float, n_steps: int, seed: int) -> list[TakerIntent]:
    config = market(rate=20.0, share=0.0)
    path = flat_path(value, config, n_steps)
    rng = np.random.default_rng(seed)
    return [i for t in range(n_steps) for i in generate_intents(path, t, config, rng)]


# Quotes sit on integer ticks, so each case is (true value, distance to the nearest tested tick).
@pytest.mark.parametrize("value", [10000.0, 10000.4])
@pytest.mark.parametrize("ticks_away", [1, 2, 3])
def test_noise_buyer_accepts_ask_with_probability_exp_minus_k_distance(value, ticks_away):
    k = BASE.noise.tolerance_rate
    ask = math.ceil(value) + ticks_away
    buyers = [i for i in noise_intents_at(value, 5_000, seed=10) if i.side is Side.BUY]
    accepted = np.mean([i.limit_price >= ask for i in buyers])
    assert accepted == pytest.approx(math.exp(-k * (ask - value)), abs=0.015)


@pytest.mark.parametrize("value", [10000.0, 10000.4])
@pytest.mark.parametrize("ticks_away", [1, 2, 3])
def test_noise_seller_accepts_bid_with_probability_exp_minus_k_distance(value, ticks_away):
    k = BASE.noise.tolerance_rate
    bid = math.floor(value) - ticks_away
    sellers = [i for i in noise_intents_at(value, 5_000, seed=11) if i.side is Side.SELL]
    accepted = np.mean([i.limit_price <= bid for i in sellers])
    assert accepted == pytest.approx(math.exp(-k * (value - bid)), abs=0.015)


def informed_intents(path: np.ndarray, config: MarketConfig) -> list[TakerIntent]:
    rng = np.random.default_rng(12)
    intents = [i for _ in range(200) for i in generate_intents(path, 0, config, rng)]
    return [i for i in intents if i.kind == "informed"]


INFORMED_CONFIG = market(rate=5.0, share=0.5, lookahead=2)


def test_informed_buyer_limit_is_largest_tick_keeping_the_edge():
    path = np.array([10000.0, 9990.0, 10005.3])
    intents = informed_intents(path, INFORMED_CONFIG)
    assert intents
    threshold = INFORMED_CONFIG.informed.edge_threshold
    for intent in intents:
        assert intent.side is Side.BUY
        assert intent.limit_price <= 10005.3 - threshold < intent.limit_price + 1
    assert intents[0].limit_price == 10004


def test_informed_seller_limit_is_smallest_tick_keeping_the_edge():
    path = np.array([10000.0, 10010.0, 9994.6])
    intents = informed_intents(path, INFORMED_CONFIG)
    assert intents
    threshold = INFORMED_CONFIG.informed.edge_threshold
    for intent in intents:
        assert intent.side is Side.SELL
        assert intent.limit_price - 1 < 9994.6 + threshold <= intent.limit_price
    assert intents[0].limit_price == 9996


def test_no_informed_taker_when_future_value_equals_current():
    path = np.array([10000.0, 10007.0, 10000.0])
    assert informed_intents(path, INFORMED_CONFIG) == []


def test_informed_side_follows_direction_of_future_value():
    config = market(rate=2.0, share=0.4)
    rng = np.random.default_rng(13)
    path = generate_value_path(config, V0, 2_000, rng)
    seen = 0
    for t in range(2_000):
        rises = path[t + config.informed.lookahead] > path[t]
        for intent in generate_intents(path, t, config, rng):
            if intent.kind == "informed":
                seen += 1
                assert intent.side is (Side.BUY if rises else Side.SELL)
    assert seen > 100


def test_intents_rejects_step_without_lookahead_value():
    config = BASE
    path = flat_path(10000.0, config, 5)
    rng = np.random.default_rng(0)
    with pytest.raises(ValueError):
        generate_intents(path, 6, config, rng)
    with pytest.raises(ValueError):
        generate_intents(path, -1, config, rng)
