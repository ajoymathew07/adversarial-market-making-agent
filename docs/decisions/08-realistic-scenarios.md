# 08: Realism stress scenarios

## Why

The BTCUSDT realism check ([results](../results/realism/btcusdt-2026-11-25.md)) found three
assumptions that fail: taker arrivals are bursty (dispersion index 27.6, Poisson ≈ 1), sizes are
heavy-tailed (p99/median 152 vs 3.3) and price changes are fat-tailed (excess kurtosis 16.9).

## Principle: shape only, same means

Each scenario changes one shape and keeps base's mean noise arrival rate (1/step), mean noise size
(3 lots) and value-step σ (1 tick). Informed takers are unchanged (15% share). The agents keep
their base-calibrated parameters (`[agent.*]`) and are not tuned on these scenarios. Every option
is off in base and draws no random numbers when off, so base results are byte-identical.

## Models

| Scenario | Switch (`config/default.toml`) | Model |
|---|---|---|
| `bursty_takers` | `market.noise.arrivals = "regime"` | Noise rate × 0.5 (calm) or × 3.0 (busy); two-state Markov chain with geometric spells of mean 80 / 20 steps (leave with probability 1/80, 1/20 per step). Busy share 0.2, so the mean rate is 0.8·0.5 + 0.2·3 = 1. First regime from the stationary distribution. The per-step rate scale is drawn once per episode, after the value path (`mm.market.arrivals`). Dispersion index ≈ 2 per step, ≈ 9 over 10 steps. |
| `heavy_tail_sizes` | `market.noise.size_shape = "lognormal"` | Noise size = max(1, round(LogNormal(μ, 1))), μ = 0.5642, solved by bisection so the exact mean of the rounded size is 3.0. p99/median ≈ 9. |
| `fat_tail_value` | `market.true_value.step_shape = "student_t"` | Steps σ·√((df−2)/df)·t_df with df = 5: same variance, excess kurtosis 6. |
| `realistic_mix` | all three | All three together. |

Results: [stress-realistic/heldout.md](../results/stress-realistic/heldout.md) (`make stress-realistic`).

## Rejected

| Alternative | Why not |
|---|---|
| Hawkes (self-exciting) arrivals | Harder to derive and to hold the mean rate fixed; the regime chain is two numbers per state |
| Gamma-mixed Poisson per step | No persistence: bursts would not last, while BTC's dispersion grows with the window (9.6 → 27.6 → 148) |
| Poisson jump component in the value | Needs an extra jump-size parameter; Student-t gives fat tails with one (df) |
| Noise flow that moves the true value | Changes the core model (noise becomes informative); stated as a limitation instead |

Limitation: real flow is informative at every size (realism check, markouts); here noise flow
still does not move the true value.
