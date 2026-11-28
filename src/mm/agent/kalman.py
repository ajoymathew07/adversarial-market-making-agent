"""v2: v1's inventory skew around a Kalman-filter fair value driven by order-flow imbalance.

v2 changes one thing from v1: the centre it quotes around. v1 centres on the last trade price,
which is always its own bid or ask. v2 estimates the true value from the signed flow that hits
its quotes. It uses only the Observation, never V or taker kinds.

Model (the agent's own assumptions, `[agent.kalman]`):
    true value   V(t) = V(t-1) + N(0, σ²)                         random walk
    signal       n = taker-buy lots − taker-sell lots against us in the previous step
                   = lots we sold − lots we bought
    noise takers Poisson(λ) per step, buy or sell with prob 1/2, size with mean s̄ and E[s²];
                 a buyer lifts our ask with p_buy = min(1, exp(−k(ask − V))),
                 a seller hits our bid with p_sell = min(1, exp(−k(V − bid))).
So for the quotes that actually rested:
    E[n]   = h(V) = (λ/2) s̄ (p_buy − p_sell)
    dh/dV  = H    = (λ/2) s̄ k (p_buy·[p_buy<1] + p_sell·[p_sell<1])
    Var[n] = R    = (λ/2) E[s²] (p_buy + p_sell)                 compound Poisson
Linearising h around the estimate fv gives one (extended) Kalman step:
    predict  P ← P + σ²
    gain     K = P·H / (H²·P + R)
    update   fv ← fv + K·(n − h(fv)),   P ← (1 − K·H)·P
"""

import math
from dataclasses import dataclass

from mm.agent.interface import Observation, OwnFill, Quote
from mm.agent.skew import round_half_away, skew_ticks
from mm.config import KalmanConfig, SkewConfig

# Keeps the gain finite when both fill probabilities are tiny (quotes far from fv).
MIN_FLOW_VARIANCE = 1e-9


@dataclass(frozen=True)
class FlowExpectation:
    """What the noise-taker model expects of n for given quotes and fair value."""

    mean: float  # h, lots
    slope: float  # H = dh/dfv, lots per tick
    variance: float  # R, lots^2


def expected_flow(
    config: KalmanConfig, fv: float, bid: int | None, ask: int | None
) -> FlowExpectation:
    """h, H and R for the quotes that rested; a missing side contributes nothing."""
    k = config.k
    p_buy = min(1.0, math.exp(-k * (ask - fv))) if ask is not None else 0.0
    p_sell = min(1.0, math.exp(-k * (fv - bid))) if bid is not None else 0.0
    # A capped probability (quote through fv) does not change with fv, so its slope is 0.
    sensitive = (p_buy if p_buy < 1 else 0.0) + (p_sell if p_sell < 1 else 0.0)
    half_rate = config.noise_rate / 2
    return FlowExpectation(
        mean=half_rate * config.mean_size * (p_buy - p_sell),
        slope=half_rate * config.mean_size * k * sensitive,
        variance=max(half_rate * config.mean_size_sq * (p_buy + p_sell), MIN_FLOW_VARIANCE),
    )


class KalmanFairValue:
    """The filter alone: fair value `value` (ticks) and its variance, updated once per step."""

    def __init__(self, config: KalmanConfig, initial_value: float) -> None:
        self._config = config
        self._value = initial_value
        self._variance = 0.0

    @property
    def value(self) -> float:
        return self._value

    @property
    def variance(self) -> float:
        return self._variance

    def update(self, net_taker_buys: float, posted_bid: int | None, posted_ask: int | None) -> None:
        """One predict + update step from the previous step's flow and resting quotes."""
        self._variance += self._config.sigma**2
        if posted_bid is None and posted_ask is None:
            return  # nothing rested, so the flow says nothing about the value
        # The expectation uses the quotes that actually rested, skew included. When long, the
        # agent shifts its quotes down, so it expects more taker buys; only flow beyond that
        # expectation moves fv. This keeps the agent's own skew from being read as information.
        flow = expected_flow(self._config, self._value, posted_bid, posted_ask)
        p, h = self._variance, flow.slope
        gain = self._config.gain_scale * p * h / (h * h * p + flow.variance)
        self._value += gain * (net_taker_buys - flow.mean)
        self._variance = max((1 - gain * h) * p, 0.0)


@dataclass(frozen=True)
class SteadyState:
    gain: float  # K, ticks per net lot
    prior_variance: float  # P after predict, ticks^2
    posterior_variance: float  # P after update, ticks^2

    @property
    def error_std(self) -> float:
        return math.sqrt(self.posterior_variance)


def steady_state(slope: float, flow_variance: float, sigma: float) -> SteadyState:
    """Fixed point of the filter for constant H, R and Q = σ².

    From P⁻ = P⁺ + Q and P⁺ = P⁻·R / (H²·P⁻ + R):  H²·P⁻² − Q·H²·P⁻ − Q·R = 0, so
    P⁻ = (Q + sqrt(Q² + 4·Q·R/H²)) / 2.
    """
    if slope <= 0:
        raise ValueError("steady state needs a positive slope H")
    q = sigma**2
    prior = (q + math.sqrt(q * q + 4 * q * flow_variance / slope**2)) / 2
    gain = prior * slope / (slope**2 * prior + flow_variance)
    return SteadyState(gain, prior, (1 - gain * slope) * prior)


def symmetric_steady_state(config: KalmanConfig, half_spread: int) -> SteadyState:
    """The theory check: constant quotes at fv ± half_spread, so H and R are constant."""
    flow = expected_flow(config, 0.0, -half_spread, half_spread)
    return steady_state(flow.slope, flow.variance, config.sigma)


def net_taker_buys(fills: tuple[OwnFill, ...]) -> int:
    """Taker-buy minus taker-sell lots: a taker buy is our sell."""
    return sum(-f.side.sign * f.size for f in fills)


class KalmanMarketMaker:
    """Quotes v1's skewed spread around round(fv) instead of the last trade price."""

    def __init__(self, skew: SkewConfig, kalman: KalmanConfig) -> None:
        self._skew = skew
        self._kalman = kalman
        self._filter: KalmanFairValue | None = None

    def quote(self, obs: Observation) -> Quote:
        if self._filter is None or obs.step == 0:
            # At step 0 the last trade price is the public initial price.
            self._filter = KalmanFairValue(self._kalman, float(obs.last_trade_price))
        self._filter.update(net_taker_buys(obs.own_fills), obs.posted_bid, obs.posted_ask)
        fair_value = self._filter.value
        centre = round_half_away(fair_value)
        reservation = centre - skew_ticks(obs.position, self._skew.skew_per_lot)
        half_spread = self._skew.half_spread
        size = self._skew.quote_size
        return Quote(
            bid_price=reservation - half_spread,
            bid_size=size,
            ask_price=reservation + half_spread,
            ask_size=size,
            fair_value=fair_value,
        )

