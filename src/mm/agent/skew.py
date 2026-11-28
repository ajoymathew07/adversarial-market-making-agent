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
    """position * skew_per_lot rounded to the nearest tick, halves away from zero.

    Rounding the magnitude keeps a long and a short of the same size mirror images
    (+0.5 -> +1, -0.5 -> -1), unlike Python's round(), which sends halves to the even tick.
    """
    shift = position * skew_per_lot
    return int(math.copysign(math.floor(abs(shift) + 0.5), shift))
