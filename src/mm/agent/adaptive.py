"""v4: the tuned control (v2 fair value + v1 skew + its own base spread), adapting to the flow.

Two optional features, both computed from the agent's own observations only:

1. Online intensity. v2's noise rate λ was calibrated once on base. Each observation, the agent
   compares the lots it was actually filled with the lots its own flow model expected for the
   quotes that rested (`expected_flow(...).lots`, at ρ = 1 and the fair value they were quoted
   around), and keeps an EWMA of each with decay d = 0.5^(1 / intensity_halflife):
       O ← d·O + (1 − d)·observed lots,   E ← d·E + (1 − d)·expected lots
       ρ = clip(O / E, min_scale, max_scale)          (ρ = 1 while E = 0)
   The filter then uses λ·ρ in `expected_flow`, so the mean h, slope H and variance R of the
   flow all scale with ρ. The filter update at an observation uses the ρ from the previous
   observations, so the flow being filtered does not also set its own noise level.
   intensity_halflife = 0 is "off": ρ ≡ 1, exactly the control's filter.

2. Uncertainty spread. With P the filter's posterior variance (ticks²):
       half_spread = clip(round_half_away(base + a·√P + c·T), base, max_half_spread)
   a = 0 gives the control's fixed base spread. T is v3's toxicity score (mm.agent.toxicity),
   included only when a ToxicityConfig is given (the v5 `final` agent); c = its widen_per_tick.

3. Competitive base (v6 `competitive`, optional). With a CompetitionConfig, `base` above is
   replaced each quote by mm.agent.competition's effective base, narrowed when the agent's
   share of public traded volume falls.

Quotes: reservation r = round(fv) − round(q · skew_per_lot), bid/ask = r ∓ half_spread.
"""

import math

from mm.agent.competition import VolumeShare, competitive_base
from mm.agent.interface import Observation, Quote
from mm.agent.kalman import KalmanFairValue, expected_flow, net_taker_buys
from mm.agent.skew import round_half_away, skew_ticks
from mm.agent.toxicity import ToxicityScore
from mm.config import (
    AdaptiveConfig,
    CompetitionConfig,
    KalmanConfig,
    SkewConfig,
    ToxicityConfig,
)


class FlowIntensity:
    """ρ: EWMA of observed own-fill lots over EWMA of the flow model's expected lots."""

    def __init__(self, config: AdaptiveConfig) -> None:
        self._config = config
        halflife = config.intensity_halflife
        self._decay = 0.5 ** (1 / halflife) if halflife > 0 else 1.0
        self._observed = 0.0
        self._expected = 0.0

    @property
    def enabled(self) -> bool:
        return self._config.intensity_halflife > 0

    @property
    def scale(self) -> float:
        """ρ, clipped; 1 when off or before any quote has rested."""
        if not self.enabled or self._expected <= 0:
            return 1.0
        ratio = self._observed / self._expected
        return min(max(ratio, self._config.min_scale), self._config.max_scale)

    def update(self, observed_lots: float, expected_lots: float) -> None:
        if not self.enabled:
            return
        d = self._decay
        self._observed = d * self._observed + (1 - d) * observed_lots
        self._expected = d * self._expected + (1 - d) * expected_lots


def uncertainty_half_spread(
    config: AdaptiveConfig,
    variance: float,
    toxicity_widening: float = 0.0,
    base: int | None = None,
) -> int:
    """round_half_away(base + a·√P + extra), clipped to [base, max_half_spread].

    `base` defaults to config.base_half_spread; v6 passes its effective base instead.
    """
    base = config.base_half_spread if base is None else base
    wanted = round_half_away(
        base + config.uncertainty_weight * math.sqrt(variance) + toxicity_widening
    )
    return min(max(wanted, base), config.max_half_spread)


class AdaptiveMarketMaker:
    """The control's quotes with an online noise intensity and an uncertainty-scaled spread.

    `skew` supplies skew_per_lot and quote_size only; the half-spread comes from `adaptive`.
    `toxicity`, if given, adds v3's c·T to the half-spread (the v5 `final` agent).
    `competition`, if given, narrows the base with the volume share (the v6 `competitive` agent).
    """

    def __init__(
        self,
        skew: SkewConfig,
        kalman: KalmanConfig,
        adaptive: AdaptiveConfig,
        toxicity: ToxicityConfig | None = None,
        competition: CompetitionConfig | None = None,
    ) -> None:
        self._skew = skew
        self._kalman = kalman
        self._config = adaptive
        self._toxicity_config = toxicity
        self._competition = competition
        self._started = False
        self._reset(0.0)

    def _reset(self, initial_value: float) -> None:
        self._filter = KalmanFairValue(self._kalman, initial_value)
        self._intensity = FlowIntensity(self._config)
        self._toxicity = ToxicityScore(self._toxicity_config) if self._toxicity_config else None
        self._half_spread = self._config.base_half_spread
        self._effective_base = self._config.base_half_spread
        self._share = VolumeShare(self._competition.share_halflife) if self._competition else None

    @property
    def intensity_scale(self) -> float:
        """The current ρ, for evaluation."""
        return self._intensity.scale

    @property
    def volume_share(self) -> float | None:
        """v6's share of public traded volume; None without a CompetitionConfig."""
        return self._share.value if self._share is not None else None

    @property
    def effective_base(self) -> int:
        """The base half-spread of the latest quote (v6 narrows it; otherwise the config's)."""
        return self._effective_base

    @property
    def half_spread(self) -> int:
        """The half-spread of the latest quote, in ticks."""
        return self._half_spread

    @property
    def variance(self) -> float:
        """The filter's posterior variance P after the latest update, ticks²."""
        return self._filter.variance

    def quote(self, obs: Observation) -> Quote:
        if obs.step == 0 or not self._started:
            # At step 0 the last trade price is the public initial price.
            self._reset(float(obs.last_trade_price))
            self._started = True
        fills = obs.own_fills
        rate_scale = self._intensity.scale  # from the observations before this one
        if obs.posted_bid is not None or obs.posted_ask is not None:
            # Expected lots at ρ = 1, around the fair value the resting quotes were placed at.
            fv = self._filter.value
            expected = expected_flow(self._kalman, fv, obs.posted_bid, obs.posted_ask)
            self._intensity.update(sum(f.size for f in fills), expected.lots)
        self._filter.update(net_taker_buys(fills), obs.posted_bid, obs.posted_ask, rate_scale)
        fair_value = self._filter.value

        widening = 0.0
        if self._toxicity is not None and self._toxicity_config is not None:
            self._toxicity.update(obs.step, fills, fair_value)
            widening = self._toxicity_config.widen_per_tick * self._toxicity.value
        if self._share is not None and self._competition is not None:
            self._share.update(
                sum(f.size for f in fills), sum(t.size for t in obs.last_step_trades)
            )
            self._effective_base = competitive_base(
                self._config.base_half_spread, self._share.value, self._competition
            )
        self._half_spread = uncertainty_half_spread(
            self._config, self._filter.variance, widening, self._effective_base
        )

        skew = skew_ticks(obs.position, self._skew.skew_per_lot)
        reservation = round_half_away(fair_value) - skew
        size = self._skew.quote_size
        return Quote(
            bid_price=reservation - self._half_spread,
            bid_size=size,
            ask_price=reservation + self._half_spread,
            ask_size=size,
            fair_value=fair_value,
        )
