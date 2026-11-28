# Evaluation report

30 seeds (1000..1029), 2000 steps per episode. Money in price units; markouts per lot.

## Summary: naive

| Metric (mean [95% CI]) | no_informed | base | toxic |
|---|---|---|---|
| Final PnL | 4.69 [-2.63, 11.35] | 3.31 [-3.50, 9.40] | 0.46 [-7.71, 7.75] |
| Spread capture | 5.38 [4.59, 6.20] | 10.59 [9.10, 12.07] | 17.66 [14.58, 20.68] |
| Inventory PnL | -0.69 [-7.61, 5.53] | -7.28 [-13.13, -2.14] | -17.19 [-23.39, -11.90] |
| Max drawdown | 18.12 [14.03, 22.77] | 18.88 [15.20, 23.20] | 21.95 [17.86, 26.91] |
| Sharpe | 0.64 [0.12, 1.15] | 0.37 [-0.05, 0.77] | 0.19 [-0.27, 0.63] |
| Informed markout/lot, t=10 | n/a | -0.0310 [-0.0321, -0.0298] | -0.0266 [-0.0273, -0.0261] |
| Noise markout/lot, t=10 | 0.0030 [0.0025, 0.0035] | 0.0089 [0.0083, 0.0095] | 0.0177 [0.0173, 0.0182] |
| Mean \|q\| | 27.81 [24.53, 31.12] | 31.90 [29.19, 34.62] | 36.28 [33.28, 39.20] |
| % time at limit | 24.05 [16.10, 32.48] | 33.99 [25.64, 42.48] | 48.21 [39.08, 57.49] |

## Markouts by counterparty kind and horizon: naive

| Kind | Horizon | no_informed | base | toxic |
|---|---|---|---|---|
| noise | 0 | 0.0029 [0.0027, 0.0032] | 0.0050 [0.0047, 0.0054] | 0.0064 [0.0059, 0.0069] |
| noise | 1 | 0.0029 [0.0026, 0.0031] | 0.0056 [0.0052, 0.0059] | 0.0077 [0.0073, 0.0082] |
| noise | 5 | 0.0029 [0.0025, 0.0033] | 0.0075 [0.0070, 0.0079] | 0.0130 [0.0127, 0.0133] |
| noise | 10 | 0.0030 [0.0025, 0.0035] | 0.0089 [0.0083, 0.0095] | 0.0177 [0.0173, 0.0182] |
| noise | 20 | 0.0027 [0.0022, 0.0033] | 0.0091 [0.0083, 0.0097] | 0.0177 [0.0170, 0.0186] |
| informed | 0 | n/a | 0.0077 [0.0064, 0.0088] | 0.0148 [0.0142, 0.0154] |
| informed | 1 | n/a | 0.0040 [0.0027, 0.0052] | 0.0111 [0.0104, 0.0117] |
| informed | 5 | n/a | -0.0111 [-0.0126, -0.0098] | -0.0038 [-0.0045, -0.0031] |
| informed | 10 | n/a | -0.0310 [-0.0321, -0.0298] | -0.0266 [-0.0273, -0.0261] |
| informed | 20 | n/a | -0.0333 [-0.0355, -0.0313] | -0.0283 [-0.0309, -0.0261] |

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

## skew − naive: no_informed

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | -1.68 [-7.98, 5.61] | no |
| Spread capture | -2.34 [-3.14, -1.47] | yes |
| Inventory PnL | 0.66 [-5.11, 7.34] | no |
| Max drawdown | -14.15 [-18.69, -10.32] | yes |
| Sharpe | 0.17 [-0.35, 0.74] | no |
| Mean \|q\| | -20.86 [-24.17, -17.62] | yes |
| % time at limit | -24.05 [-32.48, -16.10] | yes |
| Informed markout/lot, t=10 | n/a | n/a |

## skew − naive: base

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | -2.86 [-8.44, 3.41] | no |
| Spread capture | 0.77 [-0.65, 2.31] | no |
| Inventory PnL | -3.63 [-8.35, 1.93] | no |
| Max drawdown | -13.43 [-17.33, -10.10] | yes |
| Sharpe | -0.19 [-0.61, 0.25] | no |
| Mean \|q\| | -24.26 [-26.93, -21.61] | yes |
| % time at limit | -33.99 [-42.48, -25.64] | yes |
| Informed markout/lot, t=10 | -0.0006 [-0.0016, 0.0005] | no |

## skew − naive: toxic

Per-seed differences (agent − baseline) on identical markets; significant when the 95% CI excludes 0.

| Metric | Mean difference [95% CI] | Significant |
|---|---|---|
| Final PnL | 1.36 [-5.59, 9.43] | no |
| Spread capture | 9.53 [6.36, 12.79] | yes |
| Inventory PnL | -8.17 [-13.26, -2.12] | yes |
| Max drawdown | -17.08 [-21.97, -13.13] | yes |
| Sharpe | 0.22 [-0.19, 0.66] | no |
| Mean \|q\| | -27.95 [-30.80, -25.01] | yes |
| % time at limit | -48.21 [-57.49, -39.08] | yes |
| Informed markout/lot, t=10 | 0.0004 [-0.0003, 0.0011] | no |
