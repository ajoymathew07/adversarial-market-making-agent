# Stress: taker tolerance shape, development seeds

Dev seeds 0..29, 2000 steps, informed share 0.15 in every scenario. Money in price units, fair-value error in ticks. v2 uses the `[agent.kalman]` calibrated on exponential-taker base dev seeds, unchanged in every scenario.

Mean [95% CI] over seeds. ✔ on the agent's value: the per-seed difference from the baseline on identical markets has a 95% CI that excludes 0. The naive column is not marked.

## base

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | naive (reference) |
|---|---|---|---|
| Final PnL | 1.07 [-0.73, 2.80] | 5.62 [3.62, 7.57] ✔ | -2.82 [-10.89, 4.46] |
| Spread capture | 12.00 [11.41, 12.59] | 14.74 [13.90, 15.55] ✔ | 9.34 [7.68, 10.96] |
| Inventory PnL | -10.93 [-12.68, -9.20] | -9.12 [-11.05, -7.29] ✔ | -12.16 [-18.95, -6.16] |
| Max drawdown | 5.08 [4.14, 6.11] | 5.75 [4.87, 6.73] | 24.66 [19.91, 30.02] |
| Sharpe | 0.31 [-0.08, 0.69] | 1.14 [0.73, 1.55] ✔ | 0.02 [-0.43, 0.46] |
| Informed markout/lot, t=10 | -0.0307 [-0.0315, -0.0300] | -0.0300 [-0.0309, -0.0292] ✔ | -0.0307 [-0.0323, -0.0294] |
| Noise markout/lot, t=10 | 0.0078 [0.0074, 0.0082] | 0.0096 [0.0092, 0.0101] ✔ | 0.0093 [0.0085, 0.0101] |
| Mean \|q\| | 7.62 [7.42, 7.84] | 9.33 [9.01, 9.66] ✔ | 33.94 [30.89, 37.05] |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 42.90 [33.29, 52.99] |
| Fair-value RMSE (ticks) | 2.20 [2.17, 2.24] | 2.12 [2.07, 2.17] ✔ | 17.55 [11.72, 24.37] |
| Fair-value bias (ticks) | -0.02 [-0.05, 0.02] | -0.02 [-0.08, 0.04] | 3.92 [-2.80, 11.40] |

## uniform_takers

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | naive (reference) |
|---|---|---|---|
| Final PnL | 2.21 [0.63, 3.79] | 5.80 [3.70, 7.86] ✔ | -2.15 [-10.57, 5.55] |
| Spread capture | 12.93 [12.27, 13.59] | 14.61 [13.71, 15.50] ✔ | 9.12 [7.34, 10.86] |
| Inventory PnL | -10.71 [-12.10, -9.33] | -8.82 [-10.51, -7.09] ✔ | -11.27 [-18.12, -5.02] |
| Max drawdown | 4.63 [3.97, 5.30] | 5.66 [4.67, 6.70] ✔ | 24.22 [19.52, 29.49] |
| Sharpe | 0.57 [0.20, 0.95] | 1.19 [0.76, 1.65] ✔ | 0.10 [-0.40, 0.58] |
| Informed markout/lot, t=10 | -0.0301 [-0.0310, -0.0293] | -0.0297 [-0.0307, -0.0287] ✔ | -0.0290 [-0.0302, -0.0280] |
| Noise markout/lot, t=10 | 0.0081 [0.0077, 0.0085] | 0.0095 [0.0089, 0.0101] ✔ | 0.0088 [0.0083, 0.0094] |
| Mean \|q\| | 7.54 [7.32, 7.77] | 9.37 [9.01, 9.74] ✔ | 34.08 [30.79, 37.40] |
| % time at limit | 0.00 [0.00, 0.00] | 0.02 [0.00, 0.06] | 45.95 [35.91, 56.23] |
| Fair-value RMSE (ticks) | 1.99 [1.96, 2.02] | 1.99 [1.93, 2.05] | 17.29 [11.52, 23.87] |
| Fair-value bias (ticks) | -0.03 [-0.07, 0.01] | -0.04 [-0.09, 0.01] | 4.84 [-1.85, 12.14] |

## heavy_tail_takers

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | naive (reference) |
|---|---|---|---|
| Final PnL | 0.14 [-1.42, 1.67] | 4.38 [2.45, 6.29] ✔ | -3.93 [-11.26, 2.97] |
| Spread capture | 11.40 [10.66, 12.12] | 14.56 [13.66, 15.48] ✔ | 8.53 [6.93, 10.11] |
| Inventory PnL | -11.26 [-12.80, -9.72] | -10.18 [-12.07, -8.41] | -12.46 [-18.74, -6.65] |
| Max drawdown | 5.44 [4.65, 6.34] | 5.76 [4.92, 6.66] | 23.72 [19.04, 29.00] |
| Sharpe | 0.09 [-0.25, 0.43] | 0.90 [0.51, 1.30] ✔ | -0.08 [-0.48, 0.31] |
| Informed markout/lot, t=10 | -0.0309 [-0.0317, -0.0301] | -0.0297 [-0.0305, -0.0289] ✔ | -0.0330 [-0.0361, -0.0306] |
| Noise markout/lot, t=10 | 0.0079 [0.0075, 0.0084] | 0.0096 [0.0091, 0.0102] ✔ | 0.0089 [0.0083, 0.0095] |
| Mean \|q\| | 7.66 [7.45, 7.87] | 9.38 [9.04, 9.73] ✔ | 35.47 [32.37, 38.47] |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 44.84 [35.18, 54.66] |
| Fair-value RMSE (ticks) | 2.17 [2.13, 2.21] | 2.05 [2.01, 2.10] ✔ | 16.31 [10.67, 22.74] |
| Fair-value bias (ticks) | 0.01 [-0.02, 0.04] | 0.00 [-0.03, 0.04] | 4.67 [-1.66, 11.68] |

## What the numbers show

With its parameters calibrated on exponential-taker base seeds (not leaked, not re-estimated per scenario), v2's final PnL and Sharpe are significantly above v1's in all three scenarios: final PnL 5.62 vs 1.07 (base), 5.80 vs 2.21 (uniform takers) and 4.38 vs 0.14 (heavy-tailed takers), so its edge over v1 survives the wrong fill shape. Under uniform takers v1 earns more than in base while v2 stays about the same, so the gap narrows, and v2's fair-value RMSE is no better than v1's (1.99 vs 1.99); its edge there comes from spread capture and inventory PnL. Heavy-tailed takers lower final PnL for every agent; v2 keeps a lower fair-value RMSE (2.05 vs 2.17) and higher spread capture, but its inventory PnL is no longer significantly better than v1's. v2 carries more inventory than v1 in every scenario (mean |q| about 9.4 vs 7.6 lots) and has a higher max drawdown under uniform takers (5.66 vs 4.63). Naive stays far behind, at the position limit about 45% of the time.
