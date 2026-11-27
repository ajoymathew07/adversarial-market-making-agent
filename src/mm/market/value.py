"""Hidden true value: a Gaussian random walk in ticks, generated once per episode."""

import numpy as np
from numpy.typing import NDArray

from mm.market.config import MarketConfig


def generate_value_path(
    config: MarketConfig, n_steps: int, rng: np.random.Generator
) -> NDArray[np.float64]:
    """Return V(0..n_steps + lookahead), so informed takers can see ahead at every step."""
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    n_increments = n_steps + config.informed_lookahead
    increments = config.sigma * rng.standard_normal(n_increments)
    path = config.initial_value + np.concatenate(([0.0], np.cumsum(increments)))
    return path.astype(np.float64)
