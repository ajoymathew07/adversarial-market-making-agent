"""v3: v2's fair value and skew, with a half-spread that widens when its own fills go against it.

The agent marks each of its fills by how its OWN fair value drifts after the filter has absorbed
the fill (it never sees V or taker kinds). A fill made in step s first arrives in observation
s + 1; the fair value after that observation's update is the reference, and the fair value τ
observations later is the mark:
    m = s · (fv(s + 1 + τ) − fv(s + 1))    ticks per lot; s = +1 for a buy, −1 for a sell
The Kalman filter moves fv against every fill as it absorbs it; measuring from after that jump
leaves only later drift, so a fill scores m < 0 only if the value kept moving against us.
Fills whose mark has not arrived are pending and not scored.

Toxicity score, an exponentially weighted average per lot over matured fills, starting at 0:
    a ← d^w · a + (1 − d^w) · m,   d = 0.5^(1 / ewma_halflife),  w = the fill's lots
    T = max(0, −a)
This is the same as averaging lot by lot, so an old markout's weight halves every
`ewma_halflife` lots of matured fills. Starting at 0 means no evidence of toxicity yet.

Quotes, around v2's reservation price r (fair value and skew unchanged):
    half_spread = clip(round_half_away(base + c · T), base, max_half_spread)
    bid = r − half_spread,  ask = r + half_spread
with base = [agent.toxicity] base_half_spread.
"""

from collections import deque
from dataclasses import dataclass

from mm.agent.interface import Observation, OwnFill, Quote
from mm.agent.kalman import KalmanMarketMaker
from mm.agent.skew import round_half_away
from mm.config import KalmanConfig, SkewConfig, ToxicityConfig


@dataclass(frozen=True)
class PendingFill:
    arrived: int  # the observation step in which the fill was first reported
    reference: float  # the agent's fair value after absorbing the fill, ticks
    fill: OwnFill


class ToxicityScore:
    """Post-fill drift of the agent's own fair value, as one score T >= 0."""

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
        """At observation `now`, with `fair_value` already updated for `new_fills`.

        Scores every fill reported τ observations ago, then records the new fills with
        `fair_value` as their reference.
        """
        while self._pending and now - self._pending[0].arrived >= self._config.markout_horizon:
            pending = self._pending.popleft()
            markout = pending.fill.side.sign * (fair_value - pending.reference)
            weight = self._decay_per_lot**pending.fill.size
            self._average = weight * self._average + (1 - weight) * markout
        self._pending.extend(PendingFill(now, fair_value, fill) for fill in new_fills)


def widened_half_spread(config: ToxicityConfig, toxicity: float) -> int:
    """round_half_away(base + c·T), clipped to [base_half_spread, max_half_spread]."""
    base = config.base_half_spread
    wanted = round_half_away(base + config.widen_per_tick * toxicity)
    return min(max(wanted, base), config.max_half_spread)


class ToxicityMarketMaker:
    """Quotes v2's reservation price ± a half-spread that grows with the toxicity score."""

    def __init__(self, skew: SkewConfig, kalman: KalmanConfig, toxicity: ToxicityConfig) -> None:
        self._skew = skew
        self._config = toxicity
        self._v2 = KalmanMarketMaker(skew, kalman)
        self._score = ToxicityScore(toxicity)
        self._half_spread = toxicity.base_half_spread

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
        # v2 always quotes both sides at its reservation price ± skew.half_spread.
        assert v2.bid_price is not None
        reservation = v2.bid_price + self._skew.half_spread
        self._score.update(obs.step, obs.own_fills, v2.fair_value)
        self._half_spread = widened_half_spread(self._config, self._score.value)
        return Quote(
            bid_price=reservation - self._half_spread,
            bid_size=v2.bid_size,
            ask_price=reservation + self._half_spread,
            ask_size=v2.ask_size,
            fair_value=v2.fair_value,
        )
