"""Per-step scale of the noise-taker arrival rate, generated once per episode.

poisson: the scale is 1 at every step and no random numbers are drawn, so base runs are unchanged.
regime: a two-state Markov chain (calm, busy). Each spell lasts a geometric number of steps with
the configured mean, so the chain leaves calm with probability 1/calm_duration per step and busy
with 1/busy_duration. The first regime is drawn from the stationary distribution, where the busy
share is busy_duration / (calm_duration + busy_duration).
"""

import numpy as np
from numpy.typing import NDArray

from mm.config import NoiseConfig


def generate_noise_rate_scale(
    config: NoiseConfig, n_steps: int, rng: np.random.Generator
) -> NDArray[np.float64]:
    """Return the factor on the noise rate at each step 0..n_steps-1."""
    if n_steps < 1:
        raise ValueError("n_steps must be >= 1")
    if config.arrivals == "poisson":
        return np.ones(n_steps)
    if config.arrivals == "regime":
        busy = regime_path(config, n_steps, rng)
        return np.where(busy, config.busy_rate_scale, config.calm_rate_scale)
    raise ValueError(f"unknown noise arrivals {config.arrivals!r}")


def regime_path(config: NoiseConfig, n_steps: int, rng: np.random.Generator) -> NDArray[np.bool_]:
    """True where the market is busy, as alternating spells of geometric length."""
    durations = {False: config.calm_duration, True: config.busy_duration}
    busy_share = config.busy_duration / (config.calm_duration + config.busy_duration)
    busy = bool(rng.random() < busy_share)
    spells: list[NDArray[np.bool_]] = []
    filled = 0
    while filled < n_steps:
        length = int(rng.geometric(1.0 / durations[busy]))
        spells.append(np.full(length, busy))
        filled += length
        busy = not busy
    return np.concatenate(spells)[:n_steps]
