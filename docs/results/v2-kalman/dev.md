# v2 kalman: experiments on development seeds

Dev seeds 0..29, 2000 steps. Money in price units, fair-value error in ticks. v2 uses the calibrated `[agent.kalman]` (docs/results/calibration.md). The oracle column uses the market's true parameters, which the agent must not know; it is shown for reference only.

## Theory check

Calibrated parameters, constant symmetric quotes (half-spread 2, fv at the centre): gain κ = 0.332 ticks per net lot, predicted fair-value error std 2.03 ticks (posterior; 2.28 before the update). Measured v2 fair-value RMSE: no_informed 2.70 [2.59, 2.81], base 2.43 [2.10, 3.03], toxic 2.82 [1.74, 4.94].

## v1 (skew) vs v2 (kalman, calibrated)

Mean [95% CI] over seeds. ✔ on the agent's value: the per-seed difference from the baseline on identical markets has a 95% CI that excludes 0. The oracle column is not marked.

### no_informed

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 2.73 [1.53, 3.95] | -0.89 [-3.33, 1.43] ✔ | 0.72 [-1.05, 2.45] |
| Spread capture | 3.59 [2.94, 4.24] | 0.30 [-1.04, 1.65] ✔ | 1.64 [0.72, 2.57] |
| Inventory PnL | -0.85 [-2.06, 0.31] | -1.19 [-3.26, 0.75] | -0.92 [-2.55, 0.68] |
| Max drawdown | 4.35 [3.77, 4.99] | 7.97 [6.59, 9.46] ✔ | 5.41 [4.47, 6.52] |
| Sharpe | 0.71 [0.41, 1.02] | -0.02 [-0.43, 0.40] ✔ | 0.26 [-0.12, 0.64] |
| Informed markout/lot, t=10 | n/a | n/a | n/a |
| Noise markout/lot, t=10 | 0.0016 [0.0012, 0.0021] | 0.0002 [-0.0008, 0.0011] ✔ | 0.0007 [0.0001, 0.0014] |
| Mean \|q\| | 6.93 [6.74, 7.12] | 9.92 [9.49, 10.36] ✔ | 7.82 [7.53, 8.12] |
| % time at limit | 0.00 [0.00, 0.00] | 0.12 [0.00, 0.34] ✔ | 0.02 [0.00, 0.04] |
| Fair-value RMSE (ticks) | 2.44 [2.40, 2.48] | 2.70 [2.59, 2.81] ✔ | 2.54 [2.48, 2.62] |
| Fair-value bias (ticks) | 0.01 [-0.04, 0.08] | -0.01 [-0.10, 0.09] | 0.01 [-0.06, 0.09] |

### base

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 1.07 [-0.73, 2.80] | 5.56 [3.44, 7.62] ✔ | 5.65 [4.05, 7.21] |
| Spread capture | 12.00 [11.41, 12.59] | 14.60 [13.71, 15.44] ✔ | 13.68 [13.09, 14.34] |
| Inventory PnL | -10.93 [-12.68, -9.20] | -9.04 [-11.06, -7.14] ✔ | -8.03 [-9.78, -6.36] |
| Max drawdown | 5.08 [4.14, 6.11] | 6.20 [4.99, 7.70] ✔ | 4.34 [3.62, 5.15] |
| Sharpe | 0.31 [-0.08, 0.69] | 1.14 [0.73, 1.57] ✔ | 1.34 [0.95, 1.73] |
| Informed markout/lot, t=10 | -0.0307 [-0.0315, -0.0300] | -0.0299 [-0.0307, -0.0291] ✔ | -0.0298 [-0.0306, -0.0290] |
| Noise markout/lot, t=10 | 0.0078 [0.0074, 0.0082] | 0.0096 [0.0091, 0.0100] ✔ | 0.0095 [0.0092, 0.0099] |
| Mean \|q\| | 7.62 [7.42, 7.84] | 9.94 [9.17, 11.02] ✔ | 7.60 [7.33, 7.88] |
| % time at limit | 0.00 [0.00, 0.00] | 1.20 [0.00, 3.39] | 0.07 [0.00, 0.22] |
| Fair-value RMSE (ticks) | 2.20 [2.17, 2.24] | 2.43 [2.10, 3.03] | 2.13 [2.09, 2.16] |
| Fair-value bias (ticks) | -0.02 [-0.05, 0.02] | -0.18 [-0.58, 0.06] | -0.02 [-0.06, 0.03] |

### toxic

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 1.45 [-0.48, 3.38] | 13.65 [10.53, 16.19] ✔ | 12.46 [11.03, 13.87] |
| Spread capture | 26.09 [25.38, 26.82] | 33.58 [31.17, 35.27] ✔ | 28.65 [27.71, 29.59] |
| Inventory PnL | -24.64 [-26.79, -22.50] | -19.93 [-22.15, -17.77] ✔ | -16.18 [-17.95, -14.40] |
| Max drawdown | 5.41 [4.52, 6.39] | 5.21 [3.70, 7.64] | 3.41 [2.87, 3.97] |
| Sharpe | 0.37 [-0.01, 0.76] | 2.69 [2.19, 3.16] ✔ | 2.77 [2.39, 3.16] |
| Informed markout/lot, t=10 | -0.0266 [-0.0270, -0.0261] | -0.0247 [-0.0255, -0.0239] ✔ | -0.0246 [-0.0251, -0.0242] |
| Noise markout/lot, t=10 | 0.0164 [0.0160, 0.0168] | 0.0198 [0.0194, 0.0204] ✔ | 0.0183 [0.0179, 0.0187] |
| Mean \|q\| | 8.32 [8.06, 8.58] | 10.38 [8.84, 13.11] ✔ | 7.37 [7.12, 7.62] |
| % time at limit | 0.00 [0.00, 0.00] | 3.11 [0.00, 9.26] | 0.00 [0.00, 0.01] |
| Fair-value RMSE (ticks) | 2.02 [1.99, 2.04] | 2.82 [1.74, 4.94] | 1.93 [1.91, 1.95] |
| Fair-value bias (ticks) | 0.00 [-0.03, 0.04] | 0.98 [-0.01, 2.94] | -0.00 [-0.03, 0.03] |

## Gain sensitivity (check only; config keeps gain_scale = 1)

| gain_scale | FV RMSE (no_informed) | Final PnL (no_informed) | Sharpe (no_informed) | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 6.88 [4.02, 10.60] | -7.42 [-11.61, -3.66] | -0.53 [-0.84, -0.20] | 5.99 [3.12, 9.66] | -0.44 [-5.04, 3.56] | 0.28 [-0.11, 0.68] | 4.73 [1.95, 8.38] | 8.87 [3.86, 13.18] | 1.38 [0.86, 1.89] |
| 1 | 2.70 [2.59, 2.81] | -0.89 [-3.33, 1.43] | -0.02 [-0.43, 0.40] | 2.43 [2.10, 3.03] | 5.56 [3.44, 7.62] | 1.14 [0.73, 1.57] | 2.82 [1.74, 4.94] | 13.65 [10.53, 16.19] | 2.69 [2.19, 3.16] |
| 2 | 2.59 [2.53, 2.65] | -0.68 [-2.39, 1.00] | -0.08 [-0.46, 0.31] | 2.14 [2.10, 2.17] | 4.93 [3.51, 6.33] | 1.23 [0.87, 1.61] | 1.98 [1.96, 2.00] | 11.56 [10.13, 12.95] | 2.72 [2.33, 3.11] |

## Robustness: calibrated k and λ scaled one at a time

| Agent assumption | FV RMSE (no_informed) | Final PnL (no_informed) | Sharpe (no_informed) | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|---|---|---|
| calibrated | 2.70 [2.59, 2.81] | -0.89 [-3.33, 1.43] | -0.02 [-0.43, 0.40] | 2.43 [2.10, 3.03] | 5.56 [3.44, 7.62] | 1.14 [0.73, 1.57] | 2.82 [1.74, 4.94] | 13.65 [10.53, 16.19] | 2.69 [2.19, 3.16] |
| k ×0.5 | 5.19 [2.78, 8.50] | -2.92 [-7.06, 0.68] | -0.09 [-0.47, 0.29] | 4.80 [2.38, 8.03] | 3.31 [-1.08, 7.03] | 0.77 [0.33, 1.21] | 3.89 [1.74, 7.24] | 12.02 [7.29, 15.96] | 1.98 [1.44, 2.51] |
| k ×1.5 | 2.63 [2.54, 2.71] | 0.01 [-2.03, 2.01] | 0.12 [-0.29, 0.53] | 3.11 [2.05, 5.19] | 5.48 [2.93, 7.66] | 1.33 [0.90, 1.75] | 1.83 [1.80, 1.87] | 13.84 [12.21, 15.43] | 2.88 [2.48, 3.30] |
| λ ×0.5 | 2.52 [2.45, 2.59] | 1.82 [-0.41, 3.89] | 0.50 [0.09, 0.90] | 2.12 [2.09, 2.15] | 6.26 [4.41, 8.01] | 1.30 [0.90, 1.70] | 3.02 [1.94, 5.15] | 10.67 [7.73, 13.02] | 2.17 [1.70, 2.64] |
| λ ×1.5 | 3.22 [2.88, 3.74] | -6.29 [-9.49, -3.26] | -0.81 [-1.25, -0.38] | 3.29 [2.19, 5.38] | 1.81 [-1.01, 4.40] | 0.52 [0.10, 0.95] | 2.78 [1.68, 4.94] | 12.72 [9.52, 15.35] | 2.45 [1.96, 2.93] |
