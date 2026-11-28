"""Mean and percentile-bootstrap confidence interval across seeds. numpy only."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

CONFIDENCE = 0.95


@dataclass(frozen=True)
class Estimate:
    mean: float
    low: float
    high: float


def bootstrap_ci(
    values: Sequence[float],
    n_resamples: int,
    seed: int,
    confidence: float = CONFIDENCE,
) -> Estimate:
    """Mean with a percentile-bootstrap CI. NaNs are dropped; all-NaN gives a NaN estimate."""
    data = np.asarray(values, dtype=np.float64)
    data = data[~np.isnan(data)]
    if data.size == 0:
        return Estimate(math.nan, math.nan, math.nan)
    rng = np.random.Generator(np.random.PCG64(seed))
    resampled = rng.choice(data, size=(n_resamples, data.size), replace=True).mean(axis=1)
    tail = 100 * (1 - confidence) / 2
    low, high = np.percentile(resampled, [tail, 100 - tail])
    return Estimate(float(data.mean()), float(low), float(high))
