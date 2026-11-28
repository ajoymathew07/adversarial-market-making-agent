"""v3: v2 (Kalman fair value + v1 skew) that widens its spread when its own fills go against it.

v3 changes one thing from v2: the half-spread. The agent marks each of its own fills against
its OWN fair value τ steps later (it never sees V or taker kinds):
    m = s · (fv(t_fill + τ) − price)    ticks per lot; s = +1 for a buy, −1 for a sell
m < 0 means the fill went against us. Fills younger than τ steps are pending and not scored.

Toxicity score, an exponentially weighted average per lot over matured fills, starting at 0:
    a ← d^w · a + (1 − d^w) · m,   d = 0.5^(1 / ewma_halflife),  w = the fill's lots
    T = max(0, −a)
This is the same as averaging lot by lot, so an old markout's weight halves every
`ewma_halflife` lots of matured fills. Starting at 0 means no evidence of toxicity yet.

Quotes, around v2's reservation price r (fair value and skew unchanged):
    half_spread = clip(round_half_away(base + c · T), base, max_half_spread)
    bid = r − half_spread,  ask = r + half_spread
"""

from collections import deque
from dataclasses import dataclass

from mm.agent.interface import Observation, OwnFill, Quote
from mm.agent.kalman import KalmanMarketMaker
from mm.agent.skew import round_half_away
from mm.config import KalmanConfig, SkewConfig, ToxicityConfig


@dataclass(frozen=True)
class PendingFill:
    step: int  # the step the fill happened in
    fill: OwnFill


class ToxicityScore:
    """Markouts of the agent's own fills against its later fair value, as one score T >= 0."""

    def __init__(self, config: ToxicityConfig) -> None:
        self._config = config
        self._decay_per_lot = 0.5 ** (1 / config.ewma_halflife)
        self._average = 0.0  # ticks per lot; < 0 when matured fills went against us
        self._pending: deque[PendingFill] = deque()

    @property
    def value(self) -> float:
        """T = max(0, −average markout per lot), in ticks."""
        return max(0.0, -self._average)

    @property
    def pending(self) -> int:
        return len(self._pending)

    def update(self, now: int, new_fills: tuple[OwnFill, ...], fair_value: float) -> None:
        """At step `now`: record the previous step's fills, then score every fill τ steps old.

        `fair_value` is the agent's estimate at `now`, the one it quotes around.
        """
        self._pending.extend(PendingFill(now - 1, fill) for fill in new_fills)
        while self._pending and now - self._pending[0].step >= self._config.markout_horizon:
            fill = self._pending.popleft().fill
            markout = fill.side.sign * (fair_value - fill.price)
            weight = self._decay_per_lot**fill.size
            self._average = weight * self._average + (1 - weight) * markout


def widened_half_spread(base: int, config: ToxicityConfig, toxicity: float) -> int:
    """round_half_away(base + c·T), clipped to [base, max_half_spread]."""
    wanted = round_half_away(base + config.widen_per_tick * toxicity)
    return min(max(wanted, base), config.max_half_spread)


class ToxicityMarketMaker:
    """Quotes v2's reservation price ± a half-spread that grows with the toxicity score."""

    def __init__(self, skew: SkewConfig, kalman: KalmanConfig, toxicity: ToxicityConfig) -> None:
        self._skew = skew
        self._config = toxicity
        self._v2 = KalmanMarketMaker(skew, kalman)
        self._score = ToxicityScore(toxicity)
        self._half_spread = skew.half_spread

    @property
    def toxicity(self) -> float:
        """The current score T in ticks, for evaluation."""
        return self._score.value

    @property
    def half_spread(self) -> int:
        """The half-spread of the latest quote, in ticks."""
        return self._half_spread

    def quote(self, obs: Observation) -> Quote:
        if obs.step == 0:
            self._score = ToxicityScore(self._config)
        v2 = self._v2.quote(obs)
        # v2 always quotes both sides at reservation ± base half-spread.
        assert v2.bid_price is not None
        reservation = v2.bid_price + self._skew.half_spread
        self._score.update(obs.step, obs.own_fills, v2.fair_value)
        self._half_spread = widened_half_spread(
            self._skew.half_spread, self._config, self._score.value
        )
        return Quote(
            bid_price=reservation - self._half_spread,
            bid_size=v2.bid_size,
            ask_price=reservation + self._half_spread,
            ask_size=v2.ask_size,
            fair_value=v2.fair_value,
        )
