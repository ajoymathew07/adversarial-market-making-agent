"""v1: the naive quote, shifted against inventory by the Avellaneda-Stoikov reservation price."""

import math

from mm.agent.interface import Observation, Quote
from mm.config import SkewConfig


class InventorySkewMarketMaker:
    """Quotes r ± half_spread, with r = centre − q · γ · σ² · τ rounded to the nearest tick."""

    def __init__(self, config: SkewConfig) -> None:
        self._config = config

    def quote(self, obs: Observation) -> Quote:
        reservation = obs.last_trade_price - skew_ticks(obs.position, self._config.skew_per_lot)
        half_spread = self._config.half_spread
        size = self._config.quote_size
        return Quote(
            bid_price=reservation - half_spread,
            bid_size=size,
            ask_price=reservation + half_spread,
            ask_size=size,
            fair_value=float(obs.last_trade_price),
        )


def skew_ticks(position: int, skew_per_lot: float) -> int:
    """position * skew_per_lot rounded to the nearest tick, halves away from zero."""
    return round_half_away(position * skew_per_lot)


def round_half_away(x: float) -> int:
    """x rounded to the nearest integer, halves away from zero.

    Rounding the magnitude keeps a long and a short of the same size mirror images
    (+0.5 -> +1, -0.5 -> -1), unlike Python's round(), which sends halves to the even tick.
    For a positive price this is the same as rounding halves up.
    """
    return int(math.copysign(math.floor(abs(x) + 0.5), x))
