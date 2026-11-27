"""Parameters of the simulated market. Prices are in integer ticks, sizes in integer lots."""

import math
from dataclasses import dataclass

# The noise-taker fill probability is calibrated at this distance from the true value.
FILL_PROB_REFERENCE_TICKS = 2.0


@dataclass(frozen=True)
class MarketConfig:
    tick_size: float = 0.01
    initial_value: float = 10000.0  # ticks, i.e. 100.00
    sigma: float = 1.0  # std of the true-value step, in ticks

    noise_rate: float = 1.0  # mean noise takers per step
    noise_size_min: int = 1
    noise_size_max: int = 5
    fill_prob_at_2_ticks: float = 0.30

    informed_share: float = 0.15  # expected fraction of takers that are informed
    informed_lookahead: int = 10  # steps ahead an informed taker sees the true value
    informed_edge_threshold: float = 1.0  # minimum edge in ticks an informed taker demands
    informed_size_min: int = 5
    informed_size_max: int = 10

    def __post_init__(self) -> None:
        if self.tick_size <= 0:
            raise ValueError("tick_size must be > 0")
        if self.sigma < 0:
            raise ValueError("sigma must be >= 0")
        if self.noise_rate < 0:
            raise ValueError("noise_rate must be >= 0")
        if not 0 < self.fill_prob_at_2_ticks < 1:
            raise ValueError("fill_prob_at_2_ticks must be in (0, 1)")
        if not 0 <= self.informed_share < 1:
            raise ValueError("informed_share must be in [0, 1)")
        if self.informed_lookahead < 1:
            raise ValueError("informed_lookahead must be >= 1")
        if self.informed_edge_threshold < 0:
            raise ValueError("informed_edge_threshold must be >= 0")
        if not 1 <= self.noise_size_min <= self.noise_size_max:
            raise ValueError("noise sizes must satisfy 1 <= min <= max")
        if not 1 <= self.informed_size_min <= self.informed_size_max:
            raise ValueError("informed sizes must satisfy 1 <= min <= max")

    @property
    def noise_tolerance_rate(self) -> float:
        """k in P(fill at distance d) = exp(-k * d), from the calibration point."""
        return -math.log(self.fill_prob_at_2_ticks) / FILL_PROB_REFERENCE_TICKS

    @property
    def informed_rate(self) -> float:
        """Mean informed takers per step, so that informed / all takers = informed_share."""
        return self.noise_rate * self.informed_share / (1 - self.informed_share)
