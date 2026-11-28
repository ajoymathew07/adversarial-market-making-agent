# Stress: realism scenarios, held-out seeds

Agents were calibrated on base dev seeds and not tuned on these scenarios. Held-out seeds 1000..1029, 2000 steps, informed share 0.15 in every scenario. Money in price units, fair-value error in ticks.

Mean [95% CI] over seeds. ✔ on the agent's value: the per-seed difference from the baseline on identical markets has a 95% CI that excludes 0.

## base

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) |
|---|---|---|
| Final PnL | 0.45 [-1.30, 2.14] | 5.56 [3.61, 7.46] ✔ |
| Spread capture | 11.36 [10.39, 12.22] | 15.09 [14.16, 15.96] ✔ |
| Inventory PnL | -10.91 [-12.46, -9.39] | -9.53 [-11.47, -7.57] ✔ |
| Max drawdown | 5.45 [4.44, 6.55] | 5.55 [4.57, 6.59] |
| Sharpe | 0.18 [-0.19, 0.55] | 1.10 [0.73, 1.47] ✔ |
| Informed markout/lot, t=10 | -0.0315 [-0.0323, -0.0308] | -0.0305 [-0.0312, -0.0299] ✔ |
| Noise markout/lot, t=10 | 0.0077 [0.0073, 0.0081] | 0.0096 [0.0091, 0.0102] ✔ |
| Mean \|q\| | 7.64 [7.41, 7.88] | 9.51 [9.21, 9.80] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.04] |
| Fair-value RMSE (ticks) | 2.21 [2.17, 2.25] | 2.09 [2.04, 2.14] ✔ |
| Fair-value bias (ticks) | -0.02 [-0.05, 0.02] | -0.00 [-0.04, 0.04] |

## bursty_takers

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) |
|---|---|---|
| Final PnL | 0.03 [-1.88, 1.73] | 4.51 [2.36, 6.63] ✔ |
| Spread capture | 11.96 [11.00, 12.87] | 15.89 [14.85, 16.93] ✔ |
| Inventory PnL | -11.93 [-13.93, -10.16] | -11.37 [-13.66, -9.12] |
| Max drawdown | 6.31 [5.17, 7.55] | 6.23 [5.16, 7.43] |
| Sharpe | 0.09 [-0.25, 0.42] | 0.91 [0.51, 1.30] ✔ |
| Informed markout/lot, t=10 | -0.0314 [-0.0320, -0.0307] | -0.0314 [-0.0321, -0.0307] |
| Noise markout/lot, t=10 | 0.0081 [0.0076, 0.0085] | 0.0101 [0.0095, 0.0106] ✔ |
| Mean \|q\| | 8.20 [7.94, 8.48] | 9.44 [9.14, 9.74] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.04] |
| Fair-value RMSE (ticks) | 2.32 [2.28, 2.37] | 2.27 [2.22, 2.32] ✔ |
| Fair-value bias (ticks) | 0.03 [-0.03, 0.08] | 0.07 [0.01, 0.13] ✔ |

## heavy_tail_sizes

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) |
|---|---|---|
| Final PnL | -2.73 [-4.66, -0.99] | 0.90 [-1.00, 2.78] ✔ |
| Spread capture | 10.27 [9.75, 10.79] | 12.06 [11.38, 12.71] ✔ |
| Inventory PnL | -12.99 [-14.85, -11.35] | -11.16 [-12.93, -9.42] ✔ |
| Max drawdown | 6.89 [5.63, 8.36] | 6.53 [5.44, 7.70] |
| Sharpe | -0.50 [-0.87, -0.15] | 0.26 [-0.09, 0.60] ✔ |
| Informed markout/lot, t=10 | -0.0318 [-0.0325, -0.0310] | -0.0306 [-0.0314, -0.0297] ✔ |
| Noise markout/lot, t=10 | 0.0085 [0.0081, 0.0089] | 0.0098 [0.0093, 0.0103] ✔ |
| Mean \|q\| | 7.91 [7.66, 8.17] | 9.48 [9.18, 9.78] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.03] |
| Fair-value RMSE (ticks) | 2.19 [2.15, 2.22] | 2.14 [2.10, 2.18] ✔ |
| Fair-value bias (ticks) | 0.01 [-0.03, 0.04] | -0.01 [-0.04, 0.02] |

## fat_tail_value

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) |
|---|---|---|
| Final PnL | 1.99 [0.76, 3.23] | 6.72 [5.28, 8.11] ✔ |
| Spread capture | 11.91 [11.08, 12.69] | 15.34 [14.39, 16.29] ✔ |
| Inventory PnL | -9.92 [-11.23, -8.64] | -8.61 [-10.00, -7.28] ✔ |
| Max drawdown | 4.84 [4.15, 5.59] | 5.26 [4.51, 6.12] |
| Sharpe | 0.47 [0.20, 0.75] | 1.29 [1.00, 1.58] ✔ |
| Informed markout/lot, t=10 | -0.0308 [-0.0315, -0.0302] | -0.0300 [-0.0308, -0.0292] ✔ |
| Noise markout/lot, t=10 | 0.0079 [0.0074, 0.0084] | 0.0097 [0.0093, 0.0102] ✔ |
| Mean \|q\| | 7.47 [7.30, 7.65] | 9.25 [9.01, 9.49] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.03] |
| Fair-value RMSE (ticks) | 2.18 [2.13, 2.22] | 2.06 [2.01, 2.11] ✔ |
| Fair-value bias (ticks) | 0.01 [-0.02, 0.04] | 0.01 [-0.02, 0.05] |

## realistic_mix

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) |
|---|---|---|
| Final PnL | -2.86 [-4.40, -1.26] | 0.38 [-1.69, 2.48] ✔ |
| Spread capture | 9.61 [8.71, 10.50] | 11.48 [10.28, 12.66] ✔ |
| Inventory PnL | -12.47 [-13.67, -11.21] | -11.10 [-12.43, -9.77] ✔ |
| Max drawdown | 7.39 [6.34, 8.45] | 6.98 [5.87, 8.21] |
| Sharpe | -0.54 [-0.86, -0.20] | 0.17 [-0.23, 0.58] ✔ |
| Informed markout/lot, t=10 | -0.0313 [-0.0322, -0.0305] | -0.0315 [-0.0326, -0.0304] |
| Noise markout/lot, t=10 | 0.0080 [0.0075, 0.0085] | 0.0100 [0.0095, 0.0105] ✔ |
| Mean \|q\| | 8.22 [7.95, 8.49] | 9.21 [8.93, 9.50] ✔ |
| % time at limit | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.01] |
| Fair-value RMSE (ticks) | 2.29 [2.24, 2.33] | 2.32 [2.26, 2.38] |
| Fair-value bias (ticks) | -0.04 [-0.09, 0.02] | -0.04 [-0.12, 0.03] |

## Interpretation

| Scenario | v1 Sharpe | v2 Sharpe | Reading |
|---|---|---|---|
| base | 0.18 | 1.10 ✔ | Reference. |
| bursty_takers | 0.09 | 0.91 ✔ | v2's PnL edge holds, but its informed-markout advantage disappears and its fair value gains a small bias: bursts of noise flow are partly read as information. |
| heavy_tail_sizes | −0.50 | 0.26 ✔ | Hardest single change for both: more full-size fills mean larger inventory swings (inventory PnL is the worst of the five). |
| fat_tail_value | 0.47 | 1.29 ✔ | Fat-tailed steps don't hurt either agent here; informed takers already see the full future move whatever its shape. |
| realistic_mix | −0.54 | 0.17 ✔ | v2 still beats v1, but its own PnL CI includes 0 and its fair-value error is no better than v1's. This is the weakest case and the main target for v4 (regime and uncertainty adaptation). |

v2's improvement over v1 holds in every unseen scenario (Sharpe ✔ in all five), so it doesn't depend on Poisson arrivals, narrow sizes or Gaussian steps. What does degrade is v2's fair-value advantage when arrivals are bursty.
