from dataclasses import replace

import numpy as np
import pytest

from mm.config import MarketConfig, load_config
from mm.market import generate_value_path

BASE = load_config().market
V0 = load_config().instrument.initial_price_ticks


def with_sigma(sigma: float) -> MarketConfig:
    return replace(BASE, true_value=replace(BASE.true_value, sigma=sigma))


def test_same_seed_gives_identical_path():
    a = generate_value_path(BASE, V0, 500, np.random.default_rng(7))
    b = generate_value_path(BASE, V0, 500, np.random.default_rng(7))
    np.testing.assert_array_equal(a, b)


def test_different_seed_gives_different_path():
    a = generate_value_path(BASE, V0, 500, np.random.default_rng(7))
    b = generate_value_path(BASE, V0, 500, np.random.default_rng(8))
    assert not np.array_equal(a, b)


def test_path_covers_every_step_plus_lookahead_and_starts_at_initial_value():
    config = replace(BASE, informed=replace(BASE.informed, lookahead=10))
    path = generate_value_path(config, 12345, 100, np.random.default_rng(0))
    assert len(path) == 100 + 10 + 1
    assert path[0] == 12345.0
    assert path.dtype == np.float64


def test_increments_have_zero_mean_and_sigma_std():
    path = generate_value_path(with_sigma(2.5), V0, 100_000, np.random.default_rng(1))
    increments = np.diff(path)
    assert abs(increments.mean()) < 0.05
    assert increments.std() == pytest.approx(2.5, rel=0.02)


def test_zero_sigma_gives_flat_path():
    path = generate_value_path(with_sigma(0.0), V0, 50, np.random.default_rng(0))
    assert np.all(path == V0)


def test_path_rejects_non_positive_step_count():
    with pytest.raises(ValueError):
        generate_value_path(BASE, V0, 0, np.random.default_rng(0))
