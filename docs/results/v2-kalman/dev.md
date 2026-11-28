# v2 kalman: experiments on development seeds

Dev seeds 0..29, 2000 steps. Money in price units, fair-value error in ticks. v2 uses the calibrated `[agent.kalman]` (docs/results/calibration.md). The oracle column uses the market's true parameters, which the agent must not know; it is shown for reference only.

## Theory check

Calibrated parameters, constant symmetric quotes (half-spread 2, fv at the centre): gain κ = 0.332 ticks per net lot, predicted fair-value error std 2.03 ticks (posterior; 2.28 before the update). Measured v2 fair-value RMSE: no_informed 2.69 [2.60, 2.80], base 2.12 [2.07, 2.17], toxic 1.76 [1.73, 1.78].

## v1 (skew) vs v2 (kalman, calibrated)

Mean [95% CI] over seeds. ✔ on the agent's value: the per-seed difference from the baseline on identical markets has a 95% CI that excludes 0. The oracle column is not marked.

### no_informed

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 2.73 [1.53, 3.95] | -0.98 [-3.39, 1.33] ✔ | 0.63 [-1.18, 2.40] |
| Spread capture | 3.59 [2.94, 4.24] | 0.23 [-1.06, 1.54] ✔ | 1.56 [0.66, 2.48] |
| Inventory PnL | -0.85 [-2.06, 0.31] | -1.21 [-3.20, 0.68] | -0.93 [-2.54, 0.66] |
| Max drawdown | 4.35 [3.77, 4.99] | 7.93 [6.56, 9.40] ✔ | 5.43 [4.48, 6.53] |
| Sharpe | 0.71 [0.41, 1.02] | -0.05 [-0.47, 0.38] ✔ | 0.23 [-0.16, 0.62] |
| Informed markout/lot, t=10 | n/a | n/a | n/a |
| Noise markout/lot, t=10 | 0.0016 [0.0012, 0.0021] | 0.0001 [-0.0009, 0.0010] ✔ | 0.0007 [0.0001, 0.0013] |
| Mean \|q\| | 6.93 [6.74, 7.12] | 9.75 [9.37, 10.14] ✔ | 7.77 [7.50, 8.05] |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 0.00 [0.00, 0.00] |
| Fair-value RMSE (ticks) | 2.44 [2.40, 2.48] | 2.69 [2.60, 2.80] ✔ | 2.55 [2.48, 2.62] |
| Fair-value bias (ticks) | 0.01 [-0.04, 0.08] | -0.01 [-0.11, 0.08] | 0.01 [-0.06, 0.08] |

### base

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 1.07 [-0.73, 2.80] | 5.62 [3.62, 7.57] ✔ | 5.79 [4.18, 7.34] |
| Spread capture | 12.00 [11.41, 12.59] | 14.74 [13.90, 15.55] ✔ | 13.68 [13.07, 14.35] |
| Inventory PnL | -10.93 [-12.68, -9.20] | -9.12 [-11.05, -7.29] ✔ | -7.89 [-9.60, -6.23] |
| Max drawdown | 5.08 [4.14, 6.11] | 5.75 [4.87, 6.73] | 4.23 [3.59, 4.94] |
| Sharpe | 0.31 [-0.08, 0.69] | 1.14 [0.73, 1.55] ✔ | 1.37 [0.98, 1.76] |
| Informed markout/lot, t=10 | -0.0307 [-0.0315, -0.0300] | -0.0300 [-0.0309, -0.0292] ✔ | -0.0299 [-0.0307, -0.0291] |
| Noise markout/lot, t=10 | 0.0078 [0.0074, 0.0082] | 0.0096 [0.0092, 0.0101] ✔ | 0.0096 [0.0092, 0.0099] |
| Mean \|q\| | 7.62 [7.42, 7.84] | 9.33 [9.01, 9.66] ✔ | 7.53 [7.29, 7.78] |
| % time at limit | 0.00 [0.00, 0.00] | 0.01 [0.00, 0.02] | 0.00 [0.00, 0.00] |
| Fair-value RMSE (ticks) | 2.20 [2.17, 2.24] | 2.12 [2.07, 2.17] ✔ | 2.12 [2.08, 2.16] |
| Fair-value bias (ticks) | -0.02 [-0.05, 0.02] | -0.02 [-0.08, 0.04] | -0.02 [-0.06, 0.02] |

### toxic

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman, calibrated) | oracle (leaked, for reference only) |
|---|---|---|---|
| Final PnL | 1.45 [-0.48, 3.38] | 14.48 [12.62, 16.31] ✔ | 12.45 [10.99, 13.87] |
| Spread capture | 26.09 [25.38, 26.82] | 34.54 [33.62, 35.47] ✔ | 28.60 [27.67, 29.55] |
| Inventory PnL | -24.64 [-26.79, -22.50] | -20.06 [-22.33, -17.83] ✔ | -16.15 [-17.92, -14.37] |
| Max drawdown | 5.41 [4.52, 6.39] | 4.42 [3.71, 5.20] ✔ | 3.41 [2.87, 3.98] |
| Sharpe | 0.37 [-0.01, 0.76] | 2.75 [2.32, 3.19] ✔ | 2.77 [2.39, 3.16] |
| Informed markout/lot, t=10 | -0.0266 [-0.0270, -0.0261] | -0.0244 [-0.0248, -0.0239] ✔ | -0.0246 [-0.0250, -0.0241] |
| Noise markout/lot, t=10 | 0.0164 [0.0160, 0.0168] | 0.0196 [0.0193, 0.0200] ✔ | 0.0183 [0.0179, 0.0187] |
| Mean \|q\| | 8.32 [8.06, 8.58] | 9.11 [8.77, 9.44] ✔ | 7.36 [7.12, 7.61] |
| % time at limit | 0.00 [0.00, 0.00] | 0.04 [0.00, 0.10] | 0.00 [0.00, 0.00] |
| Fair-value RMSE (ticks) | 2.02 [1.99, 2.04] | 1.76 [1.73, 1.78] ✔ | 1.93 [1.91, 1.95] |
| Fair-value bias (ticks) | 0.00 [-0.03, 0.04] | 0.00 [-0.02, 0.02] | -0.00 [-0.03, 0.03] |

## Gain sensitivity (check only; config keeps gain_scale = 1)

| gain_scale | FV RMSE (no_informed) | Final PnL (no_informed) | Sharpe (no_informed) | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|---|---|---|
| 0.5 | 3.12 [2.96, 3.30] | -7.31 [-10.69, -4.01] | -0.79 [-1.17, -0.39] | 2.34 [2.26, 2.43] | 0.29 [-2.79, 3.33] | 0.16 [-0.24, 0.57] | 1.71 [1.69, 1.74] | 11.11 [8.41, 13.78] | 1.55 [1.14, 1.97] |
| 1 | 2.69 [2.60, 2.80] | -0.98 [-3.39, 1.33] | -0.05 [-0.47, 0.38] | 2.12 [2.07, 2.17] | 5.62 [3.62, 7.57] | 1.14 [0.73, 1.55] | 1.76 [1.73, 1.78] | 14.48 [12.62, 16.31] | 2.75 [2.32, 3.19] |
| 2 | 2.59 [2.53, 2.65] | -0.63 [-2.31, 1.04] | -0.07 [-0.45, 0.32] | 2.14 [2.10, 2.18] | 4.89 [3.47, 6.30] | 1.23 [0.86, 1.60] | 1.99 [1.97, 2.01] | 11.55 [10.11, 12.94] | 2.71 [2.33, 3.10] |

## Robustness: calibrated k and λ scaled one at a time

| Agent assumption | FV RMSE (no_informed) | Final PnL (no_informed) | Sharpe (no_informed) | FV RMSE (base) | Final PnL (base) | Sharpe (base) | FV RMSE (toxic) | Final PnL (toxic) | Sharpe (toxic) |
|---|---|---|---|---|---|---|---|---|---|
| calibrated | 2.69 [2.60, 2.80] | -0.98 [-3.39, 1.33] | -0.05 [-0.47, 0.38] | 2.12 [2.07, 2.17] | 5.62 [3.62, 7.57] | 1.14 [0.73, 1.55] | 1.76 [1.73, 1.78] | 14.48 [12.62, 16.31] | 2.75 [2.32, 3.19] |
| k ×0.5 | 2.75 [2.64, 2.87] | -1.80 [-4.64, 0.88] | -0.12 [-0.51, 0.26] | 2.16 [2.11, 2.21] | 4.93 [2.32, 7.46] | 0.82 [0.42, 1.23] | 1.74 [1.72, 1.77] | 13.70 [11.14, 16.13] | 2.07 [1.63, 2.53] |
| k ×1.5 | 2.63 [2.55, 2.72] | -0.13 [-2.19, 1.88] | 0.08 [-0.33, 0.50] | 2.09 [2.05, 2.13] | 6.02 [4.19, 7.77] | 1.34 [0.93, 1.75] | 1.82 [1.80, 1.85] | 13.94 [12.34, 15.51] | 2.90 [2.51, 3.31] |
| λ ×0.5 | 2.50 [2.43, 2.56] | 2.02 [-0.06, 3.98] | 0.50 [0.10, 0.90] | 2.12 [2.09, 2.16] | 6.13 [4.16, 8.00] | 1.28 [0.86, 1.69] | 1.96 [1.93, 1.98] | 11.68 [9.87, 13.42] | 2.25 [1.83, 2.68] |
| λ ×1.5 | 2.98 [2.84, 3.13] | -6.39 [-9.47, -3.43] | -0.93 [-1.40, -0.47] | 2.22 [2.15, 2.30] | 2.48 [0.34, 4.61] | 0.55 [0.14, 0.96] | 1.70 [1.67, 1.73] | 13.37 [11.27, 15.42] | 2.49 [2.05, 2.94] |
