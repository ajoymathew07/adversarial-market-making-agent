"""v0 baseline: a fixed symmetric spread around the last trade price, no inventory awareness."""

from mm.agent.interface import Observation, Quote
from mm.config import NaiveConfig


class NaiveMarketMaker:
    def __init__(self, config: NaiveConfig) -> None:
        self._config = config

    def quote(self, obs: Observation) -> Quote:
        centre = obs.last_trade_price
        half_spread = self._config.half_spread
        size = self._config.quote_size
        return Quote(
            bid_price=centre - half_spread,
            bid_size=size,
            ask_price=centre + half_spread,
            ask_size=size,
        )
