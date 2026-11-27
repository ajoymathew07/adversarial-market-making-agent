"""Takers that arrive each step and what they want to trade. Independent of the order book."""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from mm.market.config import MarketConfig

TakerKind = Literal["noise", "informed"]


@dataclass(frozen=True)
class TakerIntent:
    """An IOC limit order a taker wants to send. Price in ticks, size in lots."""

    kind: TakerKind
    is_buy: bool
    limit_price: int
    size: int


def generate_intents(
    path: NDArray[np.float64], t: int, config: MarketConfig, rng: np.random.Generator
) -> list[TakerIntent]:
    """Return the takers arriving at step t, in random order."""
    if not 0 <= t < len(path) - config.informed_lookahead:
        raise ValueError(f"step {t} has no lookahead value in a path of length {len(path)}")
    value = float(path[t])
    future_value = float(path[t + config.informed_lookahead])

    n_noise = int(rng.poisson(config.noise_rate))
    n_informed = int(rng.poisson(config.informed_rate))

    intents = [_noise_intent(value, config, rng) for _ in range(n_noise)]
    if future_value != value:
        intents += [_informed_intent(value, future_value, config, rng) for _ in range(n_informed)]

    order = rng.permutation(len(intents))
    return [intents[i] for i in order]


def _noise_intent(value: float, config: MarketConfig, rng: np.random.Generator) -> TakerIntent:
    # Exponential tolerance makes P(buyer accepts an ask d ticks above value) = exp(-k * d).
    is_buy = bool(rng.random() < 0.5)
    size = int(rng.integers(config.noise_size_min, config.noise_size_max + 1))
    tolerance = float(rng.exponential(1.0 / config.noise_tolerance_rate))
    if is_buy:
        limit = math.floor(value + tolerance)
    else:
        limit = math.ceil(value - tolerance)
    return TakerIntent("noise", is_buy, limit, size)


def _informed_intent(
    value: float, future_value: float, config: MarketConfig, rng: np.random.Generator
) -> TakerIntent:
    # The limit is the worst price that still leaves at least the edge threshold.
    is_buy = future_value > value
    size = int(rng.integers(config.informed_size_min, config.informed_size_max + 1))
    if is_buy:
        limit = math.floor(future_value - config.informed_edge_threshold)
    else:
        limit = math.ceil(future_value + config.informed_edge_threshold)
    return TakerIntent("informed", is_buy, limit, size)
