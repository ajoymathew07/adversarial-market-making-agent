"""Estimate the v2 agent's `[agent.kalman]` parameters from the calibration agent's observations.

Only what the agent itself sees or chose is used: its own fills (side, price, size), its own
posted quotes, the centres it quoted around and the last trade price. Never V, never the taker
kind, never [market].

    fill rate  mean fills per step on one side at distance d ≈ (λ/2)·exp(−k·d); a least-squares
               line through log(mean fills) against d gives λ̂ = 2·exp(intercept), k̂ = −slope
    sizes      ŝ = mean fill size, Ê[s²] = mean of squared fill sizes
    σ̂          σ̂² = mean((p(t+L) − p(t))²) / L over last trade prices p; the bid/ask bounce
               adds a fixed amount to the squared change, so a long lag L dilutes it
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass, replace

import numpy as np

from mm.agent import CalibrationMarketMaker, Observation
from mm.config import SimConfig
from mm.simulation import run_episode
from mm.types import Side


@dataclass(frozen=True)
class FillRatePoint:
    distance: int  # ticks from the centre the quote was placed around
    quotes: int  # side-steps with a resting quote at this distance
    fills: int  # fills on those quotes

    @property
    def mean_fills(self) -> float:
        return self.fills / self.quotes


@dataclass(frozen=True)
class CalibrationResult:
    sigma: float
    noise_rate: float
    k: float
    mean_size: float
    mean_size_sq: float
    fill_rates: tuple[FillRatePoint, ...]  # one per distance, ascending
    n_fills: int


def calibrate(config: SimConfig, seeds: Sequence[int], n_steps: int) -> CalibrationResult:
    """Run the calibration agent on each seed of `config` and estimate from what it saw."""
    agents = [_run_calibration_agent(config, seed, n_steps) for seed in seeds]
    episodes = [agent.observations for agent in agents]
    outcomes = [o for agent in agents for o in quote_outcomes(agent.observations, agent.centres)]
    points = fill_rate_points(outcomes)
    noise_rate, k = fit_fill_rate(points)
    sizes = np.array([f.size for obs in episodes for o in obs for f in o.own_fills], dtype=float)
    prices = [[o.last_trade_price for o in observations] for observations in episodes]
    return CalibrationResult(
        sigma=sigma_from_trade_prices(prices, config.calibration.sigma_lag),
        noise_rate=noise_rate,
        k=k,
        mean_size=float(sizes.mean()),
        mean_size_sq=float(np.mean(sizes**2)),
        fill_rates=points,
        n_fills=int(sizes.size),
    )


def _run_calibration_agent(config: SimConfig, seed: int, n_steps: int) -> CalibrationMarketMaker:
    episode = replace(config, seed=seed, n_steps=n_steps)
    agent = CalibrationMarketMaker(
        episode.agent.calibration,
        episode.agent.skew.skew_per_lot,
        episode.risk.max_order_size,
        seed,
    )
    run_episode(episode, agent)
    return agent


def quote_outcomes(
    observations: Sequence[Observation], centres: Sequence[int]
) -> list[tuple[int, int]]:
    """(distance from the centre, fills) for every side that rested.

    obs[t+1] holds where step t's quotes rested and their fills. The last step's quotes have
    no next observation and are dropped.
    """
    outcomes = []
    for centre, after in zip(centres, observations[1:], strict=False):
        if after.posted_bid is not None:
            fills = sum(1 for f in after.own_fills if f.side is Side.BUY)
            outcomes.append((centre - after.posted_bid, fills))
        if after.posted_ask is not None:
            fills = sum(1 for f in after.own_fills if f.side is Side.SELL)
            outcomes.append((after.posted_ask - centre, fills))
    return outcomes


def fill_rate_points(outcomes: Sequence[tuple[int, int]]) -> tuple[FillRatePoint, ...]:
    """Pool both sides: number of quotes and fills at each distance."""
    quotes: dict[int, int] = {}
    fills: dict[int, int] = {}
    for distance, n in outcomes:
        quotes[distance] = quotes.get(distance, 0) + 1
        fills[distance] = fills.get(distance, 0) + n
    return tuple(FillRatePoint(d, quotes[d], fills[d]) for d in sorted(quotes))


def fit_fill_rate(points: Sequence[FillRatePoint]) -> tuple[float, float]:
    """(λ̂, k̂) from log(mean fills) = log(λ/2) − k·d, unweighted least squares."""
    if len(points) < 2 or any(p.fills == 0 for p in points):
        raise ValueError("the fill-rate fit needs fills at two or more distances")
    distances = np.array([p.distance for p in points], dtype=float)
    log_means = np.log([p.mean_fills for p in points])
    slope, intercept = np.polyfit(distances, log_means, 1)
    return 2 * math.exp(float(intercept)), -float(slope)


def sigma_from_trade_prices(prices: Sequence[Sequence[int]], lag: int) -> float:
    """sqrt(mean((p(t+lag) − p(t))²) / lag), pooling every episode's overlapping pairs."""
    changes = [np.asarray(p[lag:], dtype=float) - p[:-lag] for p in prices if len(p) > lag]
    if not changes:
        raise ValueError(f"no episode has more than {lag} trade prices")
    squared = np.concatenate(changes) ** 2
    return math.sqrt(float(squared.mean()) / lag)
