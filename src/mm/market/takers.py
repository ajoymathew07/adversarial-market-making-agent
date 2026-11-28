"""Takers that arrive each step and what they want to trade. Independent of the order book."""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from mm.config import MarketConfig, NoiseConfig
from mm.types import Side

TakerKind = Literal["noise", "informed"]

# Log-scale std of the lognormal tolerance; its mu is set so the mean stays 1/k.
LOGNORMAL_SIGMA = 1.0


@dataclass(frozen=True)
class TakerIntent:
    """An IOC limit order a taker wants to send. Price in ticks, size in lots."""

    kind: TakerKind
    side: Side
    limit_price: int
    size: int


def generate_intents(
    path: NDArray[np.float64],
    t: int,
    config: MarketConfig,
    rng: np.random.Generator,
    noise_rate_scale: float = 1.0,
) -> list[TakerIntent]:
    """Return the takers arriving at step t, in random order.

    `noise_rate_scale` multiplies the noise rate at this step (see mm.market.arrivals);
    the informed rate does not change.
    """
    lookahead = config.informed.lookahead
    if not 0 <= t < len(path) - lookahead:
        raise ValueError(f"step {t} has no lookahead value in a path of length {len(path)}")
    value = float(path[t])
    future_value = float(path[t + lookahead])

    n_noise = int(rng.poisson(config.noise.rate * noise_rate_scale))
    n_informed = int(rng.poisson(config.informed_rate))

    intents = [_noise_intent(value, config, rng) for _ in range(n_noise)]
    if future_value != value:
        intents += [_informed_intent(value, future_value, config, rng) for _ in range(n_informed)]

    order = rng.permutation(len(intents))
    return [intents[i] for i in order]


def draw_tolerance(shape: str, k: float, rng: np.random.Generator) -> float:
    """How many ticks past the true value a noise taker accepts; the mean is 1/k for every shape.

    exponential: P(accept at distance d) = exp(-k * d), the model the agents assume.
    uniform: 1 - d * k / 2 up to a hard cutoff at 2/k.
    lognormal: a heavy upper tail, so a few takers accept very bad prices.
    """
    mean = 1.0 / k
    if shape == "exponential":
        return float(rng.exponential(mean))
    if shape == "uniform":
        return float(rng.uniform(0.0, 2.0 * mean))
    if shape == "lognormal":
        mu = math.log(mean) - LOGNORMAL_SIGMA**2 / 2
        return float(rng.lognormal(mu, LOGNORMAL_SIGMA))
    raise ValueError(f"unknown tolerance shape {shape!r}")


def draw_noise_size(config: NoiseConfig, rng: np.random.Generator) -> int:
    """A noise taker's size in lots.

    uniform: integers size_min..size_max inclusive.
    lognormal: max(1, round(LogNormal(size_log_mu, size_log_sigma))), a heavy upper tail.
    """
    if config.size_shape == "uniform":
        return int(rng.integers(config.size_min, config.size_max + 1))
    if config.size_shape == "lognormal":
        return max(1, round(float(rng.lognormal(config.size_log_mu, config.size_log_sigma))))
    raise ValueError(f"unknown noise size shape {config.size_shape!r}")


def _noise_intent(value: float, config: MarketConfig, rng: np.random.Generator) -> TakerIntent:
    side = Side.BUY if rng.random() < 0.5 else Side.SELL
    size = draw_noise_size(config.noise, rng)
    tolerance = draw_tolerance(config.noise.tolerance, config.noise.tolerance_rate, rng)
    if side is Side.BUY:
        limit = math.floor(value + tolerance)
    else:
        limit = math.ceil(value - tolerance)
    return TakerIntent("noise", side, limit, size)


def _informed_intent(
    value: float, future_value: float, config: MarketConfig, rng: np.random.Generator
) -> TakerIntent:
    # The limit is the worst price that still leaves at least the edge threshold.
    side = Side.BUY if future_value > value else Side.SELL
    size = int(rng.integers(config.informed.size_min, config.informed.size_max + 1))
    threshold = config.informed.edge_threshold
    if side is Side.BUY:
        limit = math.floor(future_value - threshold)
    else:
        limit = math.ceil(future_value + threshold)
    return TakerIntent("informed", side, limit, size)
