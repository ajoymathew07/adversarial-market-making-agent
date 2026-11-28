"""Record what an agent quoted, per step, for evaluation only: half-spread and v3's toxicity score.

`evaluate(..., agent_factory=recorder.factory)` builds every episode's agent through the
recorder, so the per-episode means line up with the result's seeds.
"""

import math
from collections.abc import Sequence

from mm.agent import Agent, Observation, Quote, ToxicityMarketMaker, make_agent
from mm.config import SimConfig
from mm.eval.runner import ScenarioResult


class RecordingAgent:
    """Wraps an agent; keeps each quote's half-spread and, for v3, its toxicity score."""

    def __init__(self, inner: Agent) -> None:
        self.inner = inner
        self.half_spreads: list[float] = []
        self.scores: list[float] = []

    def quote(self, obs: Observation) -> Quote:
        quote = self.inner.quote(obs)
        if quote.bid_price is not None and quote.ask_price is not None:
            self.half_spreads.append((quote.ask_price - quote.bid_price) / 2)
        if isinstance(self.inner, ToxicityMarketMaker):
            self.scores.append(self.inner.toxicity)
        return quote


class EpisodeRecorder:
    """Agent factory for `evaluate` that keeps one RecordingAgent per episode, in run order."""

    def __init__(self) -> None:
        self.episodes: list[RecordingAgent] = []

    def factory(self, config: SimConfig) -> Agent:
        self.episodes.append(RecordingAgent(make_agent(config)))
        return self.episodes[-1]

    def mean_half_spread(self) -> list[float]:
        return [_mean(e.half_spreads) for e in self.episodes]

    def mean_toxicity(self) -> list[float]:
        """Per-episode mean score; empty when the agent has none."""
        return [_mean(e.scores) for e in self.episodes if e.scores]


def informed_lot_share(result: ScenarioResult) -> list[float]:
    """Per episode: informed lots / all lots the agent filled (NaN with no fills)."""
    shares = []
    for m in result.metrics:
        total = m.lots["informed"] + m.lots["noise"]
        shares.append(m.lots["informed"] / total if total else math.nan)
    return shares


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else math.nan
