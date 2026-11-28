"""Calibration agent: quotes at random distances so the agent can measure how fills fall off.

Used only by `make calibrate` on development seeds. Each step it quotes, for each side
independently, at a distance d drawn uniformly from [min_distance, max_distance] ticks around
its centre (bid = centre − d_bid, ask = centre + d_ask, so it never self-crosses). Size is the
largest the gate allows, so a large taker is less hidden by our own size.

The centre is v1's: the last trade price shifted by position × skew_per_lot. Without the shift,
inventory runs to one side and the last trade price stops following the value.

It keeps the observations it received and the centres it used; `mm.calibration` estimates
everything from those alone. Its randomness comes from its own generator, seeded from the
episode seed, so the market's value path and takers are the same as with any other agent.
"""

import numpy as np

from mm.agent.interface import Observation, Quote
from mm.agent.skew import skew_ticks
from mm.config import CalibrationAgentConfig


class CalibrationMarketMaker:
    def __init__(
        self, config: CalibrationAgentConfig, skew_per_lot: float, quote_size: int, seed: int
    ) -> None:
        self._config = config
        self._skew_per_lot = skew_per_lot
        self._quote_size = quote_size
        self._seed = seed
        self._rng = self._new_rng()
        self.observations: list[Observation] = []
        self.centres: list[int] = []  # the centre each step's quotes were placed around

    def _new_rng(self) -> np.random.Generator:
        return np.random.Generator(np.random.PCG64([self._seed, self._config.rng_stream]))

    def quote(self, obs: Observation) -> Quote:
        if obs.step == 0:  # a new episode: start the same random stream again
            self._rng = self._new_rng()
            self.observations, self.centres = [], []
        low, high = self._config.min_distance, self._config.max_distance
        d_bid, d_ask = (int(d) for d in self._rng.integers(low, high + 1, size=2))
        centre = obs.last_trade_price - skew_ticks(obs.position, self._skew_per_lot)
        self.observations.append(obs)
        self.centres.append(centre)
        return Quote(
            bid_price=centre - d_bid,
            bid_size=self._quote_size,
            ask_price=centre + d_ask,
            ask_size=self._quote_size,
            fair_value=float(obs.last_trade_price),
        )
