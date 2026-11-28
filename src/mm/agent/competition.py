"""v6: narrow the base half-spread when the agent's share of the traded volume falls.

From the agent's own Observation only. `last_step_trades` are all public prints, ours included,
so with decay d = 0.5^(1 / share_halflife):
    O ← d·O + (1 − d)·own fill lots,   P ← d·P + (1 − d)·public trade lots
    share = O / P                       (share = 1 while P = 0)
Alone every trade is ours, so O = P and share ≡ 1. The base half-spread becomes
    effective base = clip(round_half_away(base − undercut_per_share·(1 − share)), min, base)
undercut_per_share = 0 leaves the base unchanged (exactly v5).
"""

from mm.agent.skew import round_half_away
from mm.config import CompetitionConfig


class VolumeShare:
    """EWMA of own fill lots over EWMA of all public trade lots, per observation."""

    def __init__(self, halflife: float) -> None:
        self._decay = 0.5 ** (1 / halflife)
        self._own = 0.0
        self._public = 0.0

    @property
    def value(self) -> float:
        return self._own / self._public if self._public > 0 else 1.0

    def update(self, own_lots: int, public_lots: int) -> None:
        d = self._decay
        self._own = d * self._own + (1 - d) * own_lots
        self._public = d * self._public + (1 - d) * public_lots


def competitive_base(base: int, share: float, config: CompetitionConfig) -> int:
    """clip(round_half_away(base − d·(1 − share)), min_half_spread, base)."""
    wanted = round_half_away(base - config.undercut_per_share * (1 - share))
    return min(max(wanted, config.min_half_spread), base)
