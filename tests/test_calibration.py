import inspect
import math

import pytest

import mm.calibration as calibration_module
from mm.agent import Observation, OwnFill
from mm.calibration import (
    FillRatePoint,
    calibrate,
    fill_rate_points,
    fit_fill_rate,
    quote_outcomes,
    sigma_from_trade_prices,
)
from mm.config import load_config
from mm.types import Side


def observation(
    posted: tuple[int | None, int | None], fills: tuple[OwnFill, ...] = ()
) -> Observation:
    return Observation(
        step=1,
        position=0,
        cash=0,
        own_fills=fills,
        last_step_trades=(),
        last_trade_price=0,
        posted_bid=posted[0],
        posted_ask=posted[1],
    )


def test_outcomes_pair_each_step_with_the_next_observation():
    observations = [
        observation((None, None)),
        # Step 0's quotes: bid 2 below centre 100 with two buys, ask 3 above with no fill.
        observation((98, 103), (OwnFill(Side.BUY, 98, 4), OwnFill(Side.BUY, 98, 1))),
        # Step 1's quotes: only an ask, 1 above centre 101, filled once.
        observation((None, 102), (OwnFill(Side.SELL, 102, 5),)),
    ]
    centres = [100, 101, 99]  # the last centre has no next observation
    assert quote_outcomes(observations, centres) == [(2, 2), (3, 0), (1, 1)]


def test_points_pool_both_sides_by_distance():
    points = fill_rate_points([(2, 1), (1, 0), (2, 0), (1, 3)])
    assert points == (FillRatePoint(1, 2, 3), FillRatePoint(2, 2, 1))
    assert points[0].mean_fills == 1.5


def test_fit_recovers_lambda_and_k_from_an_exact_curve():
    rate, k = 0.8, 0.5
    points = [
        FillRatePoint(d, 1_000_000, round(1_000_000 * rate / 2 * math.exp(-k * d)))
        for d in range(1, 6)
    ]
    fitted_rate, fitted_k = fit_fill_rate(points)
    assert fitted_rate == pytest.approx(rate, rel=1e-4)
    assert fitted_k == pytest.approx(k, rel=1e-4)


def test_fit_needs_fills_at_two_distances():
    with pytest.raises(ValueError, match="two or more distances"):
        fit_fill_rate([FillRatePoint(1, 10, 3), FillRatePoint(2, 10, 0)])
    with pytest.raises(ValueError, match="two or more distances"):
        fit_fill_rate([FillRatePoint(1, 10, 3)])


def test_sigma_is_the_long_lag_variance_per_step():
    # Lag 2 over [0, 1, 2, 3] gives changes 2 and 2, so sigma^2 = 4 / 2.
    assert sigma_from_trade_prices([[0, 1, 2, 3]], lag=2) == pytest.approx(math.sqrt(2))
    # A constant bounce of ±1 adds the same amount at every lag, so its share falls with lag.
    bounce = [100 + (1 if t % 2 else -1) for t in range(1000)]
    assert sigma_from_trade_prices([bounce], lag=1) > sigma_from_trade_prices([bounce], lag=51)


def test_sigma_needs_more_prices_than_the_lag():
    with pytest.raises(ValueError, match="more than 5 trade prices"):
        sigma_from_trade_prices([[1, 2, 3]], lag=5)


def test_calibrate_reproduces_the_committed_kalman_values():
    config = load_config(scenario="base")
    result = calibrate(config, config.evaluation.dev_seeds, config.n_steps)
    kalman = config.agent.kalman
    for key in ("sigma", "noise_rate", "mean_size", "mean_size_sq", "k"):
        assert getattr(result, key) == pytest.approx(getattr(kalman, key), abs=0.005), key
    assert [p.distance for p in result.fill_rates] == [1, 2, 3, 4, 5]


def test_estimation_never_reads_the_market():
    source = inspect.getsource(calibration_module)
    assert "mm.market" not in source and ".market" not in source
    assert "true_value" not in source and "taker_kind" not in source
