# 06: v2 Kalman fair value from order-flow imbalance

## Problem

v1 centres on the last trade price, which is always its own bid or ask. Its estimate bounces ±2
ticks per fill, ignores fill size and lags the true value: fair-value RMSE 2.21 ticks (base) and
2.00 (toxic) on held-out seeds (`docs/results/fair-value-baseline.md`).

## Change

v2 is v1 (same skew, 2-tick half-spread, 5 lots, `[agent.skew]`) with one change: the centre is
round(fv), where fv is a Kalman filter on signed flow n = taker-buy − taker-sell lots against us.
Buying pressure means the value is above our quotes. For small moves expected flow is roughly
linear in the value (the Cont–Kukanov–Stoikov intuition that price change is linear in order-flow
imbalance), so a linear filter fits. Each step:

```
P ← P + σ²                              predict
h, H, R from the noise-taker model       expected n, dh/dfv, Var n
K = P·H / (H²·P + R)                    gain
fv ← fv + K·(n − h)                     update
P ← (1 − K·H)·P
```

h is computed from the quotes that actually rested last step. When long, v2 shifts its quotes
down and so expects more taker buys; only flow beyond that moves fv, so its own skew is not read
as information.

## Assumptions

σ, λ, s̄, E[s²] and k are the agent's own (`[agent.kalman]`). They were first set to the
market's model values, which was a leak; they are now estimated on dev seeds (07,
`docs/results/calibration.md`). gain_scale = 1 is kept; `docs/results/v2-kalman/dev.md` has the
0.5/1/2 check and k, λ at 0.5× and 1.5× of the calibrated values.

Start: fv = the opening price with P = 0. This is a choice: the opening price is public (like a
published valuation), so the agent starts certain of V₀; uncertainty then grows by σ̂² per step.

## Theory vs measurement

With the market's values, constant symmetric quotes give κ ≈ 0.47 ticks per net lot and error std
1.70 ticks; measured dev RMSE was 2.13 (base), 1.93 (toxic). With the calibrated values: κ ≈ 0.33,
predicted error std 2.03 ticks. The model leaves out informed flow, the rounding of the centre
and that n reflects last step's value (the pre-update std is 1.97); the gap is not split further.

## Held-out (once, gain_scale = 1)

Calibrated (`docs/results/v2-kalman/heldout-calibrated/`), mean final PnL v1 → v2: 0.45 → 4.28
(base), 1.83 → 13.62 (toxic), 3.01 → −1.97 (no_informed), all significant. The first run with the
market's values (superseded, `heldout/`) gave v2 5.65, 12.96 and 0.53.

On seed 1021 the calibrated filter locks: at the +50 limit the gate removes the bid, the ask sits
below fv, so its modelled fill probability is capped at 1 with zero slope; H = 0, the gain is 0
and fv stops moving (60% of the episode at the limit, fair-value RMSE 29 ticks). Dev seeds 28
(base) and 10 (toxic) show the same. Not fixed here.

## Not covered

The main scenario has no public reference price; one could be added as a later scenario.
