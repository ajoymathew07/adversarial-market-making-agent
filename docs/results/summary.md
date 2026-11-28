# Results summary (held-out seeds)

Mean over held-out seeds 1000..1029, 2000 steps. ✔ on v5: its per-seed difference from v2-tuned has a 95% CI that excludes 0. Full tables with CIs: `docs/results/v5-final/heldout.md`.

| Scenario | Sharpe v1 | Sharpe v2 | Sharpe v2-tuned | Sharpe v4 | Sharpe v5 | Final PnL v1 | Final PnL v2 | Final PnL v2-tuned | Final PnL v4 | Final PnL v5 |
|---|---|---|---|---|---|---|---|---|---|---|
| no_informed | 0.81 | -0.09 | 2.79 | 2.87 | 4.27 ✔ | 3.01 | -0.92 | 13.93 | 14.04 | 12.27 ✔ |
| base | 0.18 | 1.10 | 3.23 | 3.24 | 4.61 ✔ | 0.45 | 5.56 | 16.42 | 16.17 | 14.37 ✔ |
| toxic | 0.41 | 2.80 | 4.01 | 3.98 | 5.19 ✔ | 1.83 | 14.91 | 20.83 | 20.65 | 17.17 ✔ |
| uniform_takers (unseen) | 0.70 | 1.27 | 2.08 | 1.89 | 2.46 ✔ | 2.74 | 6.32 | 9.87 | 8.33 | 6.83 ✔ |
| heavy_tail_takers (unseen) | 0.04 | 0.82 | 2.86 | 2.99 | 4.41 ✔ | -0.10 | 4.10 | 14.57 | 14.93 | 14.03 |
| bursty_takers (unseen) | 0.09 | 0.91 | 2.96 | 3.17 | 4.37 ✔ | 0.03 | 4.51 | 15.00 | 15.35 | 13.81 |
| heavy_tail_sizes (unseen) | -0.50 | 0.26 | 2.38 | 2.48 | 3.48 ✔ | -2.73 | 0.90 | 11.75 | 11.58 | 10.91 |
| fat_tail_value (unseen) | 0.47 | 1.29 | 3.39 | 3.44 | 4.72 ✔ | 1.99 | 6.72 | 17.35 | 17.61 | 14.68 ✔ |
| realistic_mix (unseen) | -0.54 | 0.17 | 2.19 | 2.45 | 3.01 ✔ | -2.86 | 0.38 | 10.89 | 11.58 | 9.30 ✔ |
