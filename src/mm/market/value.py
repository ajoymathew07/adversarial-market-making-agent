"""Hidden true value: a Gaussian random walk in ticks, generated once per episode."""

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
    increments = config.true_value.sigma * rng.standard_normal(n_increments)
    path = initial_value + np.concatenate(([0.0], np.cumsum(increments)))
    return path.astype(np.float64)
