import numpy as np
import pytest

from mm.market import MarketConfig, generate_value_path


def test_same_seed_gives_identical_path():
    config = MarketConfig()
    a = generate_value_path(config, 500, np.random.default_rng(7))
    b = generate_value_path(config, 500, np.random.default_rng(7))
    np.testing.assert_array_equal(a, b)


def test_different_seed_gives_different_path():
    config = MarketConfig()
    a = generate_value_path(config, 500, np.random.default_rng(7))
    b = generate_value_path(config, 500, np.random.default_rng(8))
    assert not np.array_equal(a, b)


def test_path_covers_every_step_plus_lookahead_and_starts_at_initial_value():
    config = MarketConfig(initial_value=12345.5, informed_lookahead=10)
    path = generate_value_path(config, 100, np.random.default_rng(0))
    assert len(path) == 100 + 10 + 1
    assert path[0] == 12345.5
    assert path.dtype == np.float64


def test_increments_have_zero_mean_and_sigma_std():
    config = MarketConfig(sigma=2.5)
    increments = np.diff(generate_value_path(config, 100_000, np.random.default_rng(1)))
    assert abs(increments.mean()) < 0.05
    assert increments.std() == pytest.approx(2.5, rel=0.02)


def test_zero_sigma_gives_flat_path():
    path = generate_value_path(MarketConfig(sigma=0.0), 50, np.random.default_rng(0))
    assert np.all(path == MarketConfig().initial_value)


def test_path_rejects_non_positive_step_count():
    with pytest.raises(ValueError):
        generate_value_path(MarketConfig(), 0, np.random.default_rng(0))
