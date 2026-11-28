import math

import numpy as np
import pytest

from mm.eval import realism as rz


def rng(seed=0):
    return np.random.Generator(np.random.PCG64(seed))


def test_same_timestamp_same_side_trades_merge_into_one_taker_order():
    times = np.array([1.0, 1.0, 1.0, 2.0, 2.0])
    prices = np.array([100.0, 99.0, 98.0, 98.0, 99.0])
    sizes = np.array([1.0, 2.0, 3.0, 1.0, 1.0])
    signs = np.array([-1, -1, -1, -1, 1])
    merged = rz.merge_taker_orders(times, prices, sizes, signs)
    np.testing.assert_array_equal(merged.times, [1.0, 2.0, 2.0])
    np.testing.assert_array_equal(merged.prices, [98.0, 98.0, 99.0])  # last = worst level
    np.testing.assert_array_equal(merged.sizes, [6.0, 1.0, 1.0])
    np.testing.assert_array_equal(merged.signs, [-1, -1, 1])


def test_merging_no_trades_returns_empty_orders():
    empty = np.array([], dtype=np.float64)
    merged = rz.merge_taker_orders(empty, empty, empty, np.array([], dtype=np.int64))
    assert len(merged.times) == 0


def test_bin_last_price_forward_fills_empty_bins_and_backfills_leading_ones():
    times = np.array([1.2, 1.7, 3.5])
    prices = np.array([10.0, 11.0, 12.0])
    last = rz.bin_last_price(times, prices, start=0.0, bin_width=1.0, n_bins=5)
    np.testing.assert_array_equal(last, [10.0, 11.0, 11.0, 12.0, 12.0])


def test_bin_last_price_rejects_no_trades_in_range():
    with pytest.raises(ValueError):
        rz.bin_last_price(np.array([]), np.array([]), 0.0, 1.0, 3)
    with pytest.raises(ValueError):
        rz.bin_last_price(np.array([10.0]), np.array([1.0]), 0.0, 1.0, 3)


def test_touch_counts_trades_at_or_through_the_quote_on_each_side():
    ref = np.array([100.0, 100.0])
    step = np.array([0, 1])
    prices = np.array([98.0, 101.0])  # step 0: sell down to 98; step 1: buy up to 101
    signs = np.array([-1, 1])
    probs = rz.touch_probabilities(ref, step, prices, signs, np.array([1.0, 2.0, 3.0]))
    # 4 side-steps; delta 1: two touched, delta 2: bid only, delta 3: none.
    np.testing.assert_allclose(probs, [0.5, 0.25, 0.0])


def test_exponential_touch_curve_is_fit_exactly_and_recovers_k_sigma():
    deltas = np.arange(0.25, 4.01, 0.25)
    probs = 0.4 * np.exp(-0.8 * deltas)
    fit = rz.fit_exponential(deltas, np.append(probs[:-1], 0.0))  # zero P is skipped
    assert fit.slope == pytest.approx(0.8)
    assert fit.r2 == pytest.approx(1.0)
    assert fit.n_points == len(deltas) - 1
    assert rz.fit_power_law(deltas, probs).r2 < 1.0


def test_power_law_touch_curve_recovers_its_exponent():
    deltas = np.arange(0.25, 4.01, 0.25)
    fit = rz.fit_power_law(deltas, 0.1 * deltas**-1.5)
    assert fit.slope == pytest.approx(1.5)
    assert fit.r2 == pytest.approx(1.0)


def test_constant_probabilities_have_undefined_r2():
    assert math.isnan(rz.fit_exponential(np.array([1.0, 2.0]), np.array([0.5, 0.5])).r2)


def test_poisson_counts_have_dispersion_near_one_and_bursty_counts_above():
    r = rng()
    assert rz.dispersion_index(r.poisson(3.0, 100_000).astype(float)) == pytest.approx(1, abs=0.03)
    rates = np.where(r.random(100_000) < 0.1, 20.0, 1.0)  # quiet periods with bursts
    assert rz.dispersion_index(r.poisson(rates).astype(float)) > 5


def test_poisson_process_has_interarrival_cv_near_one():
    times = np.cumsum(rng(1).exponential(1.0, 100_000))
    assert rz.interarrival_cv(times) == pytest.approx(1, abs=0.02)


def test_gaussian_random_walk_has_variance_ratio_near_one_and_no_excess_kurtosis():
    walk = np.cumsum(rng(2).standard_normal(200_000))
    assert rz.variance_ratio(walk, 10) == pytest.approx(1, abs=0.05)
    assert rz.variance_ratio(walk, 60) == pytest.approx(1, abs=0.1)
    assert rz.excess_kurtosis(np.diff(walk)) == pytest.approx(0, abs=0.05)


def test_mean_reverting_prices_have_variance_ratio_below_one():
    bounce = 100 + rng(3).choice([-0.5, 0.5], 50_000)
    assert rz.variance_ratio(bounce, 10) < 0.2


def test_size_stats_are_ratios_to_the_median():
    stats = rz.size_stats(np.arange(1.0, 101.0))
    assert stats.p90_over_median == pytest.approx(90.1 / 50.5)
    assert stats.max_over_median == pytest.approx(100 / 50.5)
    assert stats.excess_kurtosis == pytest.approx(-1.2, abs=0.01)  # uniform


def test_taker_trading_ahead_of_a_known_move_has_positive_markout():
    ref_times = np.arange(10.0)
    ref_prices = np.array([100.0] * 3 + [104.0] * 7)  # price jumps up at t = 3
    marks = rz.markout_values(
        np.array([2.0, 2.0]),
        np.array([100.0, 100.0]),
        np.array([1, -1]),
        ref_times,
        ref_prices,
        np.array([1.0, 5.0]),
        sigma=2.0,
    )
    np.testing.assert_allclose(marks, [[2.0, 2.0], [-2.0, -2.0]])


def test_markout_past_the_end_of_the_reference_is_nan():
    marks = rz.markout_values(
        np.array([8.0]),
        np.array([1.0]),
        np.array([1]),
        np.arange(10.0),
        np.ones(10),
        np.array([1.0, 5.0]),
        sigma=1.0,
    )
    assert marks[0, 0] == 0.0 and math.isnan(marks[0, 1])


def test_size_buckets_follow_quantiles_and_empty_buckets_average_to_nan():
    sizes = np.arange(1.0, 1001.0)
    buckets = rz.size_buckets(sizes)
    assert np.bincount(buckets).tolist() == [500, 400, 90, 10]
    values = np.column_stack([sizes, np.full(1000, np.nan)])
    means = rz.bucket_means(values, np.minimum(buckets, 2))
    assert means[0, 0] == pytest.approx(250.5)
    assert np.isnan(means[3, 0]) and np.isnan(means[0, 1])
