from dataclasses import replace

import numpy as np
import pytest

from mm.config import TOLERANCE_SHAPES, load_config
from mm.market import generate_intents
from mm.market.takers import draw_tolerance
from mm.types import Side

BASE = load_config().market
K = BASE.noise.tolerance_rate


def draws(shape: str, n: int = 50_000, seed: int = 20) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return np.array([draw_tolerance(shape, K, rng) for _ in range(n)])


@pytest.mark.parametrize("shape", TOLERANCE_SHAPES)
def test_every_tolerance_shape_has_mean_one_over_k(shape):
    assert draws(shape).mean() == pytest.approx(1.0 / K, rel=0.03)


def test_exponential_draw_matches_the_original_exponential_sequence():
    expected = np.random.default_rng(21).exponential(1.0 / K, 1_000)
    assert np.array_equal(draws("exponential", 1_000, seed=21), expected)


def test_uniform_tolerance_never_exceeds_two_over_k():
    sample = draws("uniform")
    assert sample.min() >= 0
    assert sample.max() <= 2.0 / K


def test_lognormal_upper_tail_is_heavier_than_exponential():
    assert np.percentile(draws("lognormal"), 99) > np.percentile(draws("exponential"), 99)


def test_unknown_shape_is_rejected():
    with pytest.raises(ValueError, match="unknown tolerance shape 'gaussian'"):
        draw_tolerance("gaussian", K, np.random.default_rng(0))


def uniform_buyers(value: float, n_steps: int, seed: int) -> list[int]:
    config = replace(
        BASE,
        noise=replace(BASE.noise, rate=20.0, tolerance="uniform"),
        informed=replace(BASE.informed, share=0.0),
    )
    path = np.full(n_steps + config.informed.lookahead + 1, value)
    rng = np.random.default_rng(seed)
    intents = [i for t in range(n_steps) for i in generate_intents(path, t, config, rng)]
    return [i.limit_price for i in intents if i.side is Side.BUY]


# 2/k is about 3.3 ticks, so 1-3 ticks are inside the cutoff and 4 is beyond it.
@pytest.mark.parametrize("ticks_away", [1, 2, 3, 4])
def test_uniform_buyer_accepts_ask_with_probability_linear_in_distance(ticks_away):
    value = 10000.0
    limits = uniform_buyers(value, 5_000, seed=22)
    accepted = np.mean([limit >= value + ticks_away for limit in limits])
    assert accepted == pytest.approx(max(0.0, 1 - ticks_away * K / 2), abs=0.015)
    if ticks_away > 2 / K:
        assert accepted == 0.0

