# Fair-value error baseline (H1)

Held-out seeds 1000..1029, 2000 steps, `python -m mm --agents naive,skew`. Measurement only, no
tuning. Error = the agent's fair value (the last trade price for both agents) − true value V(t),
in ticks, over every step. Mean [95% CI] over seeds.

| Agent | Metric | no_informed | base | toxic |
|---|---|---|---|---|
| naive | RMSE | 8.74 [5.72, 12.15] | 10.39 [6.92, 14.48] | 15.03 [10.64, 20.22] |
| naive | Bias | -0.09 [-2.88, 2.81] | -0.29 [-3.81, 3.22] | 0.48 [-4.50, 6.00] |
| skew | RMSE | 2.47 [2.41, 2.54] | 2.21 [2.17, 2.25] | 2.00 [1.98, 2.02] |
| skew | Bias | 0.03 [-0.02, 0.07] | -0.02 [-0.05, 0.02] | -0.02 [-0.04, 0.01] |

The skew agent's fair-value estimate is off by 2.0–2.5 ticks RMS in every scenario, about the
size of its 2-tick half-spread. The naive agent's error is several times larger (8.7–15.0 ticks)
and varies widely between seeds. Neither agent shows a bias: every bias CI contains 0.
