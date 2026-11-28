# Competing makers, held-out seeds

Held-out seeds 1000..1029, 2000 steps, informed share 0.15. Each column is one agent of ours against the scenario's competitor; both use their frozen config. Money in price units; lots per episode. Mean [95% CI] over seeds.

## vs_v1 (competitor: skew)

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) | v2-tuned |
|---|---|---|---|
| Our final PnL | -5.17 [-6.81, -3.56] | -6.86 [-8.85, -4.88] | -0.37 [-2.58, 1.71] |
| Our Sharpe | -1.17 [-1.52, -0.82] | -1.17 [-1.48, -0.85] | 0.08 [-0.31, 0.48] |
| Our noise lots filled | 1295.20 [1269.57, 1320.93] | 1470.43 [1450.53, 1491.90] | 493.47 [481.83, 504.67] |
| Our informed lots filled | 439.80 [421.63, 458.13] | 452.60 [436.07, 470.30] | 191.10 [178.80, 203.80] |
| Competitor final PnL | -3.98 [-5.63, -2.38] | -3.65 [-5.26, -2.12] | 1.37 [0.04, 2.64] |
| Our % of maker volume | 49.69 [49.15, 50.20] | 50.87 [50.42, 51.29] | 21.31 [20.81, 21.78] |

## vs_tuned (competitor: kalman_tuned)

| Metric (mean [95% CI]) | v1 (skew) | v2 (kalman) | v2-tuned |
|---|---|---|---|
| Our final PnL | 1.70 [0.27, 3.12] | 2.90 [0.90, 4.95] | 5.91 [3.87, 7.87] |
| Our Sharpe | 0.51 [0.13, 0.89] | 0.64 [0.26, 1.04] | 1.29 [0.86, 1.72] |
| Our noise lots filled | 2029.77 [2003.43, 2055.53] | 2055.13 [2034.77, 2074.67] | 690.57 [675.17, 706.07] |
| Our informed lots filled | 492.20 [471.00, 513.10] | 507.40 [488.03, 527.80] | 211.93 [198.77, 224.57] |
| Competitor final PnL | -0.44 [-2.59, 1.56] | -2.49 [-4.65, -0.42] | 5.77 [3.66, 7.77] |
| Our % of maker volume | 78.71 [78.16, 79.22] | 80.89 [80.49, 81.29] | 50.12 [49.54, 50.72] |

## Interpretation

TBD
