import math

from mm.eval.stats import bootstrap_ci

RESAMPLES = 2000

# Irregular values, so bootstrap means do not fall on a coarse grid shared by every seed.
DATA = [1.13, 4.71, 2.29, -3.37, 6.83, 0.41, 2.97, 3.53, -0.89, 5.17]


def test_bootstrap_is_deterministic_for_a_fixed_seed():
    assert bootstrap_ci(DATA, RESAMPLES, seed=7) == bootstrap_ci(DATA, RESAMPLES, seed=7)


def test_bootstrap_changes_with_the_seed():
    assert bootstrap_ci(DATA, RESAMPLES, seed=7) != bootstrap_ci(DATA, RESAMPLES, seed=8)


def test_interval_contains_the_mean():
    est = bootstrap_ci(DATA, RESAMPLES, seed=0)
    assert est.mean == sum(DATA) / len(DATA)
    assert est.low < est.mean < est.high


def test_constant_data_gives_zero_width_interval():
    est = bootstrap_ci([0.1] * 30, RESAMPLES, seed=0)
    assert est.low == est.mean == est.high


def test_nans_are_dropped_and_all_nan_gives_nan():
    assert bootstrap_ci([1.0, math.nan, 1.0], RESAMPLES, seed=0).mean == 1.0
    assert math.isnan(bootstrap_ci([math.nan, math.nan], RESAMPLES, seed=0).mean)
