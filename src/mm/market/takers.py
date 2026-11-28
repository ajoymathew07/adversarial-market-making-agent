"""Takers that arrive each step and what they want to trade. Independent of the order book."""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from mm.config import MarketConfig
from mm.types import Side

TakerKind = Literal["noise", "informed"]


@dataclass(frozen=True)
class TakerIntent:
    """An IOC limit order a taker wants to send. Price in ticks, size in lots."""

    kind: TakerKind
    side: Side
    limit_price: int
    size: int


def generate_intents(
    path: NDArray[np.float64], t: int, config: MarketConfig, rng: np.random.Generator
) -> list[TakerIntent]:
    """Return the takers arriving at step t, in random order."""
    lookahead = config.informed.lookahead
    if not 0 <= t < len(path) - lookahead:
        raise ValueError(f"step {t} has no lookahead value in a path of length {len(path)}")
    value = float(path[t])
    future_value = float(path[t + lookahead])

    n_noise = int(rng.poisson(config.noise.rate))
    n_informed = int(rng.poisson(config.informed_rate))

    intents = [_noise_intent(value, config, rng) for _ in range(n_noise)]
    if future_value != value:
        intents += [_informed_intent(value, future_value, config, rng) for _ in range(n_informed)]

    order = rng.permutation(len(intents))
    return [intents[i] for i in order]


def _noise_intent(value: float, config: MarketConfig, rng: np.random.Generator) -> TakerIntent:
    # Exponential tolerance makes P(buyer accepts an ask d ticks above value) = exp(-k * d).
    side = Side.BUY if rng.random() < 0.5 else Side.SELL
    size = int(rng.integers(config.noise.size_min, config.noise.size_max + 1))
    tolerance = float(rng.exponential(1.0 / config.noise.tolerance_rate))
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
