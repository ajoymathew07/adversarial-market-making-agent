# v2 kalman: experiments on development seeds

Dev seeds 0..29, 2000 steps. Mean [95% CI] over seeds; money in price units, fair-value error in ticks.

## Theory check

Constant symmetric quotes (half-spread 2, fv at the centre): gain κ = 0.474 ticks per net lot, predicted fair-value error std 1.70 ticks (posterior; 1.97 before the update). Measured v2 fair-value RMSE: base 2.13 [2.09, 2.16], toxic 1.93 [1.91, 1.95].

## v1 (skew) vs v2 (kalman)

### Summary: skew

| Metric (mean [95% CI]) | base | toxic |
|---|---|---|
| Final PnL | 1.07 [-0.73, 2.80] | 1.45 [-0.48, 3.38] |
| Spread capture | 12.00 [11.41, 12.59] | 26.09 [25.38, 26.82] |
| Inventory PnL | -10.93 [-12.68, -9.20] | -24.64 [-26.79, -22.50] |
| Max drawdown | 5.08 [4.14, 6.11] | 5.41 [4.52, 6.39] |
| Sharpe | 0.31 [-0.08, 0.69] | 0.37 [-0.01, 0.76] |
| Informed markout/lot, t=10 | -0.0307 [-0.0315, -0.0300] | -0.0266 [-0.0270, -0.0261] |
| Noise markout/lot, t=10 | 0.0078 [0.0074, 0.0082] | 0.0164 [0.0160, 0.0168] |
| Mean \|q\| | 7.62 [7.42, 7.84] | 8.32 [8.06, 8.58] |
| % time at limit | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| Fair-value RMSE (ticks) | 2.20 [2.17, 2.24] | 2.02 [1.99, 2.04] |
| Fair-value bias (ticks) | -0.02 [-0.05, 0.02] | 0.00 [-0.03, 0.04] |

### Summary: kalman

| Metric (mean [95% CI]) | base | toxic |
|---|---|---|
| Final PnL | 5.65 [4.05, 7.21] | 12.46 [11.03, 13.87] |
| Spread capture | 13.68 [13.09, 14.34] | 28.65 [27.71, 29.59] |
| Inventory PnL | -8.03 [-9.78, -6.36] | -16.18 [-17.95, -14.40] |
| Max drawdown | 4.34 [3.62, 5.15] | 3.41 [2.87, 3.97] |
| Sharpe | 1.34 [0.95, 1.73] | 2.77 [2.39, 3.16] |
| Informed markout/lot, t=10 | -0.0298 [-0.0306, -0.0290] | -0.0246 [-0.0251, -0.0242] |
| Noise markout/lot, t=10 | 0.0095 [0.0092, 0.0099] | 0.0183 [0.0179, 0.0187] |
| Mean \|q\| | 7.60 [7.33, 7.88] | 7.37 [7.12, 7.62] |
| % time at limit | 0.07 [0.00, 0.22] | 0.00 [0.00, 0.01] |
| Fair-value RMSE (ticks) | 2.13 [2.09, 2.16] | 1.93 [1.91, 1.95] |
| Fair-value bias (ticks) | -0.02 [-0.06, 0.03] | -0.00 [-0.03, 0.03] |

### kalman − skew: base

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | 4.59 [3.66, 5.46] | yes |
| Spread capture | 1.69 [1.11, 2.28] | yes |
| Inventory PnL | 2.90 [2.16, 3.55] | yes |
| Max drawdown | -0.75 [-1.34, -0.15] | yes |
| Sharpe | 1.04 [0.82, 1.25] | yes |
| Mean \|q\| | -0.03 [-0.22, 0.17] | no |
| % time at limit | 0.07 [0.00, 0.22] | no |
| Informed markout/lot, t=10 | 0.0009 [0.0004, 0.0014] | yes |
| Fair-value RMSE (ticks) | -0.08 [-0.10, -0.06] | yes |
| Fair-value bias (ticks) | 0.00 [-0.03, 0.04] | no |

### kalman − skew: toxic

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | 11.02 [9.71, 12.24] | yes |
| Spread capture | 2.56 [1.72, 3.39] | yes |
| Inventory PnL | 8.46 [7.34, 9.59] | yes |
| Max drawdown | -2.01 [-2.67, -1.41] | yes |
| Sharpe | 2.41 [2.14, 2.64] | yes |
| Mean \|q\| | -0.95 [-1.13, -0.76] | yes |
| % time at limit | 0.00 [0.00, 0.01] | no |
| Informed markout/lot, t=10 | 0.0019 [0.0016, 0.0023] | yes |
| Fair-value RMSE (ticks) | -0.09 [-0.11, -0.07] | yes |
| Fair-value bias (ticks) | -0.01 [-0.03, 0.02] | no |

## Gain sensitivity (check only; config keeps gain_scale = 1)

| gain_scale | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|
| 0.5 | 4.90 [2.36, 8.16] | 3.48 [-0.64, 6.90] | 0.86 [0.43, 1.27] | 3.86 [1.74, 7.17] | 12.62 [8.13, 16.23] | 2.32 [1.76, 2.85] |
| 1 | 2.13 [2.09, 2.16] | 5.65 [4.05, 7.21] | 1.34 [0.95, 1.73] | 1.93 [1.91, 1.95] | 12.46 [11.03, 13.87] | 2.77 [2.39, 3.16] |
| 2 | 2.42 [2.38, 2.45] | -0.44 [-1.82, 0.90] | -0.06 [-0.42, 0.31] | 2.37 [2.34, 2.39] | 2.66 [1.45, 3.87] | 0.71 [0.40, 1.04] |

## Robustness: misspecified agent assumptions (one at a time, vs the market's k and λ)

| Agent assumption | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|
| correct | 2.13 [2.09, 2.16] | 5.65 [4.05, 7.21] | 1.34 [0.95, 1.73] | 1.93 [1.91, 1.95] | 12.46 [11.03, 13.87] | 2.77 [2.39, 3.16] |
| k ×0.5 | 3.38 [2.07, 5.72] | 5.73 [2.95, 8.14] | 1.22 [0.78, 1.66] | 2.97 [1.79, 5.28] | 13.37 [10.26, 15.88] | 2.57 [2.09, 3.05] |
| k ×1.5 | 2.26 [2.23, 2.30] | 3.25 [1.91, 4.58] | 0.89 [0.53, 1.26] | 2.18 [2.16, 2.20] | 7.98 [6.65, 9.28] | 1.98 [1.62, 2.34] |
| λ ×0.5 | 2.36 [2.33, 2.40] | 0.94 [-0.58, 2.37] | 0.31 [-0.05, 0.67] | 2.30 [2.27, 2.32] | 3.79 [2.41, 5.16] | 0.93 [0.59, 1.28] |
| λ ×1.5 | 2.13 [2.08, 2.18] | 5.28 [3.57, 6.92] | 1.23 [0.84, 1.63] | 1.83 [1.80, 1.86] | 14.47 [12.95, 15.99] | 3.18 [2.77, 3.60] |
