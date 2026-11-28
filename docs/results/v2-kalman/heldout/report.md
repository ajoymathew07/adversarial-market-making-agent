Superseded: used the market's true parameters (leak); see heldout-calibrated/

# Evaluation report

30 seeds (1000..1029), 2000 steps per episode. Money in price units; markouts per lot; fair-value error in ticks.

## Summary: skew

| Metric (mean [95% CI]) | no_informed | base | toxic |
|---|---|---|---|
| Final PnL | 3.01 [1.44, 4.43] | 0.45 [-1.30, 2.14] | 1.83 [0.44, 3.13] |
| Spread capture | 3.04 [2.18, 3.92] | 11.36 [10.39, 12.22] | 27.19 [26.55, 27.80] |
| Inventory PnL | -0.03 [-1.68, 1.50] | -10.91 [-12.46, -9.39] | -25.36 [-26.77, -24.04] |
| Max drawdown | 3.96 [3.28, 4.74] | 5.45 [4.44, 6.55] | 4.87 [4.18, 5.69] |
| Sharpe | 0.81 [0.42, 1.16] | 0.18 [-0.19, 0.55] | 0.41 [0.14, 0.66] |
| Informed markout/lot, t=10 | n/a | -0.0315 [-0.0323, -0.0308] | -0.0263 [-0.0267, -0.0259] |
| Noise markout/lot, t=10 | 0.0013 [0.0007, 0.0018] | 0.0077 [0.0073, 0.0081] | 0.0165 [0.0162, 0.0168] |
| Mean \|q\| | 6.95 [6.73, 7.16] | 7.64 [7.41, 7.88] | 8.33 [8.12, 8.54] |
| % time at limit | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.00] |
| Fair-value RMSE (ticks) | 2.47 [2.41, 2.54] | 2.21 [2.17, 2.25] | 2.00 [1.98, 2.02] |
| Fair-value bias (ticks) | 0.03 [-0.02, 0.07] | -0.02 [-0.05, 0.02] | -0.02 [-0.04, 0.01] |

## Markouts by counterparty kind and horizon: skew

| Kind | Horizon | no_informed | base | toxic |
|---|---|---|---|---|
| noise | 0 | 0.0013 [0.0009, 0.0016] | 0.0033 [0.0030, 0.0036] | 0.0044 [0.0041, 0.0046] |
| noise | 1 | 0.0012 [0.0008, 0.0016] | 0.0038 [0.0035, 0.0041] | 0.0061 [0.0059, 0.0064] |
| noise | 5 | 0.0012 [0.0007, 0.0017] | 0.0061 [0.0057, 0.0065] | 0.0118 [0.0115, 0.0120] |
| noise | 10 | 0.0013 [0.0007, 0.0018] | 0.0077 [0.0073, 0.0081] | 0.0165 [0.0162, 0.0168] |
| noise | 20 | 0.0012 [0.0007, 0.0017] | 0.0080 [0.0076, 0.0085] | 0.0163 [0.0158, 0.0167] |
| informed | 0 | n/a | 0.0071 [0.0063, 0.0078] | 0.0135 [0.0131, 0.0139] |
| informed | 1 | n/a | 0.0033 [0.0024, 0.0040] | 0.0103 [0.0099, 0.0108] |
| informed | 5 | n/a | -0.0115 [-0.0123, -0.0108] | -0.0040 [-0.0045, -0.0035] |
| informed | 10 | n/a | -0.0315 [-0.0323, -0.0308] | -0.0263 [-0.0267, -0.0259] |
| informed | 20 | n/a | -0.0323 [-0.0336, -0.0311] | -0.0255 [-0.0263, -0.0247] |

## Summary: kalman

| Metric (mean [95% CI]) | no_informed | base | toxic |
|---|---|---|---|
| Final PnL | 0.53 [-0.93, 1.98] | 5.65 [4.11, 7.17] | 12.96 [11.54, 14.28] |
| Spread capture | 0.73 [-0.24, 1.67] | 13.37 [12.58, 14.14] | 29.84 [29.14, 30.53] |
| Inventory PnL | -0.19 [-1.85, 1.51] | -7.73 [-9.25, -6.19] | -16.88 [-18.61, -15.30] |
| Max drawdown | 5.10 [4.21, 6.07] | 4.19 [3.45, 5.00] | 3.46 [2.85, 4.16] |
| Sharpe | 0.19 [-0.12, 0.50] | 1.32 [0.96, 1.69] | 2.86 [2.50, 3.20] |
| Informed markout/lot, t=10 | n/a | -0.0306 [-0.0312, -0.0299] | -0.0242 [-0.0245, -0.0239] |
| Noise markout/lot, t=10 | 0.0004 [-0.0002, 0.0010] | 0.0095 [0.0091, 0.0099] | 0.0185 [0.0181, 0.0188] |
| Mean \|q\| | 7.82 [7.60, 8.06] | 7.66 [7.42, 7.88] | 7.43 [7.21, 7.66] |
| % time at limit | 0.00 [0.00, 0.01] | 0.00 [0.00, 0.00] | 0.00 [0.00, 0.01] |
| Fair-value RMSE (ticks) | 2.58 [2.52, 2.64] | 2.13 [2.09, 2.16] | 1.94 [1.92, 1.97] |
| Fair-value bias (ticks) | 0.05 [-0.01, 0.11] | 0.00 [-0.04, 0.04] | -0.01 [-0.04, 0.02] |

## Markouts by counterparty kind and horizon: kalman

| Kind | Horizon | no_informed | base | toxic |
|---|---|---|---|---|
| noise | 0 | 0.0003 [-0.0001, 0.0007] | 0.0039 [0.0036, 0.0042] | 0.0046 [0.0044, 0.0049] |
| noise | 1 | 0.0002 [-0.0002, 0.0006] | 0.0046 [0.0044, 0.0049] | 0.0066 [0.0063, 0.0068] |
| noise | 5 | 0.0003 [-0.0002, 0.0007] | 0.0075 [0.0071, 0.0079] | 0.0133 [0.0130, 0.0135] |
| noise | 10 | 0.0004 [-0.0002, 0.0010] | 0.0095 [0.0091, 0.0099] | 0.0185 [0.0181, 0.0188] |
| noise | 20 | 0.0003 [-0.0003, 0.0009] | 0.0097 [0.0092, 0.0102] | 0.0182 [0.0177, 0.0187] |
| informed | 0 | n/a | 0.0085 [0.0078, 0.0091] | 0.0167 [0.0163, 0.0171] |
| informed | 1 | n/a | 0.0047 [0.0040, 0.0053] | 0.0135 [0.0131, 0.0139] |
| informed | 5 | n/a | -0.0100 [-0.0108, -0.0093] | -0.0008 [-0.0011, -0.0004] |
| informed | 10 | n/a | -0.0306 [-0.0312, -0.0299] | -0.0242 [-0.0245, -0.0239] |
| informed | 20 | n/a | -0.0310 [-0.0323, -0.0298] | -0.0234 [-0.0243, -0.0227] |

## kalman − skew: no_informed

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | -2.48 [-3.48, -1.45] | yes |
| Spread capture | -2.31 [-3.08, -1.55] | yes |
| Inventory PnL | -0.16 [-0.99, 0.66] | no |
| Max drawdown | 1.14 [0.66, 1.61] | yes |
| Sharpe | -0.62 [-0.87, -0.37] | yes |
| Mean \|q\| | 0.88 [0.68, 1.08] | yes |
| % time at limit | 0.00 [0.00, 0.01] | no |
| Informed markout/lot, t=10 | n/a | n/a |
| Fair-value RMSE (ticks) | 0.11 [0.06, 0.16] | yes |
| Fair-value bias (ticks) | 0.02 [-0.02, 0.06] | no |

## kalman − skew: base

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | 5.20 [4.37, 6.13] | yes |
| Spread capture | 2.01 [1.41, 2.66] | yes |
| Inventory PnL | 3.18 [2.41, 3.97] | yes |
| Max drawdown | -1.26 [-2.08, -0.51] | yes |
| Sharpe | 1.14 [0.96, 1.33] | yes |
| Mean \|q\| | 0.01 [-0.13, 0.16] | no |
| % time at limit | 0.00 [0.00, 0.00] | no |
| Informed markout/lot, t=10 | 0.0010 [0.0004, 0.0015] | yes |
| Fair-value RMSE (ticks) | -0.09 [-0.11, -0.06] | yes |
| Fair-value bias (ticks) | 0.02 [-0.01, 0.04] | no |

## kalman − skew: toxic

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | 11.13 [10.45, 11.82] | yes |
| Spread capture | 2.65 [1.94, 3.33] | yes |
| Inventory PnL | 8.48 [7.72, 9.27] | yes |
| Max drawdown | -1.41 [-1.88, -0.95] | yes |
| Sharpe | 2.45 [2.28, 2.63] | yes |
| Mean \|q\| | -0.89 [-1.06, -0.74] | yes |
| % time at limit | 0.00 [0.00, 0.01] | no |
| Informed markout/lot, t=10 | 0.0021 [0.0018, 0.0025] | yes |
| Fair-value RMSE (ticks) | -0.05 [-0.07, -0.04] | yes |
| Fair-value bias (ticks) | 0.01 [-0.01, 0.03] | no |
