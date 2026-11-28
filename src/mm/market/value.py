"""Hidden true value: a random walk in ticks, generated once per episode.

Steps are Gaussian by default; the student_t shape has the same std but fat tails.
"""

import math

import numpy as np
from numpy.typing import NDArray

from mm.config import MarketConfig


def generate_value_path(
    config: MarketConfig, initial_value: int, n_steps: int, rng: np.random.Generator
) -> NDArray[np.float64]:
    """Return V(0..n_steps + lookahead), so informed takers can see ahead at every step."""
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    n_increments = n_steps + config.informed.lookahead
    increments = config.true_value.sigma * _unit_steps(config, n_increments, rng)
    path = initial_value + np.concatenate(([0.0], np.cumsum(increments)))
    return path.astype(np.float64)


def _unit_steps(config: MarketConfig, n: int, rng: np.random.Generator) -> NDArray[np.float64]:
    """n zero-mean, unit-variance draws in the configured shape."""
    shape = config.true_value.step_shape
    if shape == "normal":
        return rng.standard_normal(n)
    if shape == "student_t":
        # Var(t_df) = df / (df - 2); rescale so the step variance is still sigma^2.
        df = config.true_value.student_t_df
        return rng.standard_t(df, n) * math.sqrt((df - 2) / df)
    raise ValueError(f"unknown value step shape {shape!r}")
