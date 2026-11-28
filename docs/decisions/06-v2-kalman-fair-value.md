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

σ, λ, s̄, E[s²] and k are the agent's own (`[agent.kalman]`), set to the market's model values.
Robustness on dev seeds: with k or λ at 0.5× or 1.5× the market's, mean final PnL stays above
v1's except λ × 0.5 in base (`docs/results/v2-kalman/dev.md`). gain_scale = 1 had the lowest
fair-value error and the best or a tied PnL in a 0.5/1/2 check; the config keeps 1.

## Theory vs measurement

Constant symmetric quotes give κ ≈ 0.47 ticks per net lot and error std 1.70 ticks. Measured dev
RMSE: 2.13 (base), 1.93 (toxic). The model leaves out informed flow, the rounding of the centre
and that n reflects last step's value (the pre-update std is 1.97); the gap is not split further.

## Held-out (once, gain_scale = 1)

v2 − v1 final PnL: +5.20 (base), +11.13 (toxic), −2.48 (no_informed), all significant
(`docs/results/v2-kalman/heldout/report.md`).

## Not covered

The main scenario has no public reference price; one could be added as a later scenario.
