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

The noise-taker model treats e^(−k·distance) as an arrival intensity, buy_rate = e^(−k(ask − fv))
and sell_rate = e^(−k(fv − bid)), so h = (λ/2)·s̄·(buy_rate − sell_rate),
H = (λ/2)·s̄·k·(buy_rate + sell_rate) and R = (λ/2)·E[s²]·(buy_rate + sell_rate); a missing side
has rate 0.

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
predicted error std 2.03 ticks;
measured dev RMSE 2.12 (base), 1.76 (toxic). The model leaves out informed flow, the rounding of
the centre and that n reflects last step's value (the pre-update std is 1.97); the gap is not
split further.

## Filter lock (fixed)

The first calibrated version used a fill probability min(1, e^(−k·distance)). At the +50 limit the
gate removes the bid and the skew puts the ask below fv, so that probability was capped at 1 with
zero slope: H = 0, the gain was 0, fv froze and the agent stayed at the limit (held-out seed 1021:
60% of the episode at the limit, fair-value RMSE 29 ticks; dev seeds 28 base and 10 toxic too).

Fix: e^(−k·distance) is an arrival intensity, not a probability, so it is not capped. This is the
standard Avellaneda–Stoikov form λ(δ) = A·e^(−kδ): a quote through fv simply attracts more than
λ/2 takers per step, and H stays positive whenever a side rests. For symmetric quotes at distance
2 the rates are below 1, so no cap ever applied there and the steady-state numbers above are
unchanged. `test_agent_held_at_the_position_limit_keeps_updating_and_leaves_it` reproduces the
lock on a dev seed with a 10-lot limit. After the fix seed 1021 spends 0.35% (base) of the
episode at the limit with fair-value RMSE 1.91; dev seeds 28 (base) and 10 (toxic) 0.05% and 0.45%.

## Held-out (once, gain_scale = 1)

`docs/results/v2-kalman/heldout-calibrated/`, re-run after the fix. ✔: the per-seed difference
from v1 on identical markets has a 95% CI that excludes 0.

| Mean [95% CI] | v1 base | v2 base | v1 toxic | v2 toxic | v1 no_informed | v2 no_informed |
|---|---|---|---|---|---|---|
| Final PnL | 0.45 [-1.30, 2.14] | 5.56 [3.61, 7.46] ✔ | 1.83 [0.44, 3.13] | 14.91 [13.11, 16.62] ✔ | 3.01 [1.44, 4.43] | -0.92 [-2.69, 0.84] ✔ |
| Sharpe | 0.18 [-0.19, 0.55] | 1.10 [0.73, 1.47] ✔ | 0.41 [0.14, 0.66] | 2.80 [2.42, 3.17] ✔ | 0.81 [0.42, 1.16] | -0.09 [-0.39, 0.21] ✔ |
| Fair-value RMSE | 2.21 [2.17, 2.25] | 2.09 [2.04, 2.14] ✔ | 2.00 [1.98, 2.02] | 1.76 [1.74, 1.78] ✔ | 2.47 [2.41, 2.54] | 2.72 [2.64, 2.80] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.04] | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.03] |

Before the fix v2's final PnL was 4.28 (base), 13.62 (toxic), −1.97 (no_informed); the first run
with the market's values (superseded, `heldout/`) gave 5.65, 12.96 and 0.53.

## Not covered

The main scenario has no public reference price; one could be added as a later scenario.
