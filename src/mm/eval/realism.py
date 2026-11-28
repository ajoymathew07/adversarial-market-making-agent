"""Realism check: statistics of taker flow and prices, computed the same way on simulator output
and on real trade data. Pure functions on numpy arrays; no file IO.

Conventions: `signs` are +1 for a buying taker and -1 for a selling taker; `step_index` is the
time bin (step) an order falls in; a reference price `ref_start[j]` is the price at the start of
step j.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

# Size buckets for markouts, as quantile edges of the order sizes.
SIZE_QUANTILES = (0.0, 0.5, 0.9, 0.99, 1.0)
# Normal kurtosis, subtracted to give excess kurtosis.
NORMAL_KURTOSIS = 3.0


@dataclass(frozen=True)
class TakerOrders:
    times: FloatArray
    prices: FloatArray
    sizes: FloatArray
    signs: IntArray


@dataclass(frozen=True)
class Fit:
    """Least-squares line through the points that were fitted (`n_points`)."""

    slope: float
    r2: float
    n_points: int


@dataclass(frozen=True)
class SizeStats:
    p90_over_median: float
    p99_over_median: float
    max_over_median: float
    excess_kurtosis: float


def merge_taker_orders(
    times: FloatArray, prices: FloatArray, sizes: FloatArray, signs: IntArray
) -> TakerOrders:
    """Merge consecutive trades with the same time and side into one taker order.

    A taker sweeping several price levels prints one trade per level at the same time; the
    merged order has the summed size and the last (worst) price it reached.
    """
    n = len(times)
    if n == 0:
        return TakerOrders(times, prices, sizes, signs)
    new_group = np.ones(n, dtype=bool)
    new_group[1:] = (times[1:] != times[:-1]) | (signs[1:] != signs[:-1])
    starts = np.flatnonzero(new_group)
    ends = np.append(starts[1:], n) - 1
    return TakerOrders(
        times=times[starts],
        prices=prices[ends],
        sizes=np.add.reduceat(sizes, starts),
        signs=signs[starts],
    )


def bin_index(times: FloatArray, start: float, bin_width: float) -> IntArray:
    """Index of the time bin [start + i*w, start + (i+1)*w) each time falls in."""
    return np.floor((times - start) / bin_width).astype(np.int64)


def bin_last_price(
    times: FloatArray, prices: FloatArray, start: float, bin_width: float, n_bins: int
) -> FloatArray:
    """Last trade price in each bin, forward-filled through empty bins.

    Empty bins before the first trade take the first trade's price. Times must be sorted.
    """
    if len(times) == 0:
        raise ValueError("need at least one trade")
    idx = bin_index(times, start, bin_width)
    inside = (idx >= 0) & (idx < n_bins)
    idx, kept = idx[inside], prices[inside]
    last = np.full(n_bins, np.nan)
    last[idx] = kept  # sorted times: the last write per bin is its last trade
    filled = np.flatnonzero(~np.isnan(last))
    if filled.size == 0:
        raise ValueError("no trades inside the bins")
    carry = np.maximum.accumulate(np.where(~np.isnan(last), np.arange(n_bins), 0))
    out = last[carry]
    out[: filled[0]] = kept[0]
    return out


def touch_probabilities(
    ref_start: FloatArray,
    step_index: IntArray,
    prices: FloatArray,
    signs: IntArray,
    deltas: FloatArray,
) -> FloatArray:
    """P(a quote delta from the reference is traded at or through within one step), per delta.

    A bid at ref - delta is touched if a selling taker prints (or would trade) at a price
    <= ref - delta in that step; an ask at ref + delta if a buying taker reaches >= ref + delta.
    The result averages the bid and ask sides over all steps.
    """
    n_steps = len(ref_start)
    lowest_sell = np.full(n_steps, np.inf)
    highest_buy = np.full(n_steps, -np.inf)
    sell, buy = signs < 0, signs > 0
    np.minimum.at(lowest_sell, step_index[sell], prices[sell])
    np.maximum.at(highest_buy, step_index[buy], prices[buy])
    bid_gap = ref_start - lowest_sell  # touched when >= delta
    ask_gap = highest_buy - ref_start
    d = deltas[:, None]
    bid = (bid_gap[None, :] >= d).mean(axis=1)
    ask = (ask_gap[None, :] >= d).mean(axis=1)
    return np.asarray((bid + ask) / 2, dtype=np.float64)


def _line_fit(x: FloatArray, y: FloatArray) -> Fit:
    slope, intercept = np.polyfit(x, y, 1)
    residual = y - (slope * x + intercept)
    total = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(residual**2)) / total if total > 0 else float("nan")
    return Fit(float(slope), r2, len(x))


def fit_exponential(deltas: FloatArray, probs: FloatArray) -> Fit:
    """Fit log P = a - k * delta on the points with P > 0; returns slope = k (positive).

    With delta in units of sigma_step the slope is k * sigma.
    """
    keep = probs > 0
    fit = _line_fit(deltas[keep], np.log(probs[keep]))
    return Fit(-fit.slope, fit.r2, fit.n_points)


def fit_power_law(deltas: FloatArray, probs: FloatArray) -> Fit:
    """Fit log P = a - b * log delta on the points with P > 0 and delta > 0; returns slope = b."""
    keep = (probs > 0) & (deltas > 0)
    fit = _line_fit(np.log(deltas[keep]), np.log(probs[keep]))
    return Fit(-fit.slope, fit.r2, fit.n_points)


def dispersion_index(counts: FloatArray) -> float:
    """Variance over mean of per-bin counts; 1 for Poisson arrivals, > 1 for bursty ones."""
    return float(np.var(counts) / np.mean(counts))


def interarrival_cv(times: FloatArray) -> float:
    """Std over mean of the gaps between sorted arrival times; 1 for a Poisson process."""
    gaps = np.diff(times)
    return float(np.std(gaps) / np.mean(gaps))


def excess_kurtosis(x: FloatArray) -> float:
    centred = x - x.mean()
    return float(np.mean(centred**4) / np.mean(centred**2) ** 2 - NORMAL_KURTOSIS)


def size_stats(sizes: FloatArray) -> SizeStats:
    p50, p90, p99 = np.quantile(sizes, [0.5, 0.9, 0.99])
    return SizeStats(
        p90_over_median=float(p90 / p50),
        p99_over_median=float(p99 / p50),
        max_over_median=float(sizes.max() / p50),
        excess_kurtosis=excess_kurtosis(sizes),
    )


def markout_values(
    trade_times: FloatArray,
    trade_prices: FloatArray,
    signs: IntArray,
    ref_times: FloatArray,
    ref_prices: FloatArray,
    horizons: FloatArray,
    sigma: float,
) -> FloatArray:
    """sign * (ref price at trade time + h - trade price) / sigma, shape (orders, horizons).

    The reference price at time tau is the last `ref_prices` entry with `ref_times <= tau`
    (sorted). Positive means the price moved the taker's way. NaN where t + h is past the end.
    """
    future = trade_times[:, None] + horizons[None, :]
    idx = np.searchsorted(ref_times, future, side="right") - 1
    later = ref_prices[np.clip(idx, 0, len(ref_prices) - 1)]
    out = signs[:, None] * (later - trade_prices[:, None]) / sigma
    out[(future > ref_times[-1]) | (idx < 0)] = np.nan
    return np.asarray(out, dtype=np.float64)


def size_buckets(sizes: FloatArray) -> IntArray:
    """Bucket of each order by size quantile: 0-50%, 50-90%, 90-99%, 99-100% (right-inclusive)."""
    edges = np.quantile(sizes, SIZE_QUANTILES[1:-1])
    return np.searchsorted(edges, sizes, side="left").astype(np.int64)


def bucket_means(values: FloatArray, buckets: IntArray) -> FloatArray:
    """NaN-ignoring mean of `values` rows per bucket, shape (buckets, columns); NaN if empty."""
    n_buckets = len(SIZE_QUANTILES) - 1
    out = np.full((n_buckets, values.shape[1]), np.nan)
    for b in range(n_buckets):
        rows = values[buckets == b]
        for col in range(values.shape[1]):
            column = rows[:, col]
            column = column[~np.isnan(column)]
            if column.size:
                out[b, col] = column.mean()
    return out


def variance_ratio(prices: FloatArray, h: int) -> float:
    """Var(h-step change) / (h * Var(1-step change)), overlapping changes; 1 for a random walk."""
    one = np.diff(prices)
    many = prices[h:] - prices[:-h]
    return float(np.var(many) / (h * np.var(one)))
