# v4 adaptive: dev sweep against the tuned control

Dev seeds 0..29, 2000 steps, training scenarios no_informed, base, toxic. Mean Sharpe [95% CI] over seeds. Objective: the worst case (lowest mean Sharpe) of the three; ties go to the first config in grid order. Fixed (untuned choices): min_scale = 0.25, max_scale = 4, max_half_spread = 8; skew_per_lot and quote_size from [agent.skew]. The control is the grid point (base = 4, a = 0, intensity_halflife = off), which quotes exactly as kalman_tuned.

## Verdict

Does v4 beat the tuned control? **yes**. Best worst-case Sharpe: 2.798 (base = 3, a = 0.5, intensity_halflife = 100) against the control's 2.636, a margin of +0.161.

## Best per feature combination

| Feature setting | Best worst-case Sharpe | Best config |
|---|---|---|
| intensity off, a = 0 | 2.636 | base = 4, a = 0, intensity_halflife = off |
| intensity off, a > 0 | 2.636 | base = 3, a = 0.5, intensity_halflife = off |
| intensity on, a = 0 | 2.790 | base = 4, a = 0, intensity_halflife = 20 |
| intensity on, a > 0 | 2.798 | base = 3, a = 0.5, intensity_halflife = 100 |

## What the chosen config quotes (dev, no_informed, base, toxic)

| Scenario | Mean ρ | Mean half-spread (ticks) |
|---|---|---|
| no_informed | 0.703 [0.691, 0.715] | 4.098 [4.067, 4.135] |
| base | 0.760 [0.743, 0.777] | 4.068 [4.044, 4.097] |
| toxic | 0.876 [0.854, 0.897] | 4.026 [4.013, 4.041] |

## Diagnostic: the control with a constant λ factor (not a candidate)

If a constant factor on the calibrated noise rate matches v4, ρ's gain comes from correcting the level of λ, not from tracking how it changes.

| λ factor | Sharpe no_informed | Sharpe base | Sharpe toxic | Worst case |
|---|---|---|---|---|
| 0.6 | 2.76 [2.24, 3.29] | 3.27 [2.70, 3.84] | 3.92 [3.33, 4.51] | 2.76 |
| 0.7 | 2.70 [2.18, 3.25] | 3.15 [2.62, 3.69] | 3.90 [3.36, 4.43] | 2.70 |
| 0.8 | 2.71 [2.21, 3.23] | 3.19 [2.66, 3.72] | 3.95 [3.43, 4.47] | 2.71 |
| 0.9 | 2.64 [2.15, 3.16] | 3.15 [2.63, 3.68] | 3.95 [3.41, 4.50] | 2.64 |
| 1 | 2.64 [2.15, 3.15] | 3.10 [2.62, 3.59] | 3.83 [3.33, 4.34] | 2.64 |

## Detection: does ρ track the busy/calm regime in bursty_takers?

Config: base = 3, a = 0.5, intensity_halflife = 100. ρ_t is the agent's intensity after its quote at step t; busy_t is the market's regime for the takers that arrive after that quote (evaluation only). corr is the Pearson correlation of ρ_t with the 0/1 busy flag.

| Quantity (dev seeds, per-episode mean [95% CI]) | Value |
|---|---|
| Mean ρ in busy steps | 0.829 [0.799, 0.860] |
| Mean ρ in calm steps | 0.706 [0.681, 0.734] |
| Busy − calm (per episode) | 0.123 [0.102, 0.144] |
| corr(ρ_t, busy_t) within an episode | 0.231 [0.199, 0.263] |
| corr(ρ_t, busy_t) pooled over all steps | 0.246 |
| True busy / calm noise rate (market side) | 6 |

## Fair-value RMSE against the control (ticks, dev seeds)

Mean [95% CI] over seeds. ✔: the per-seed difference from the control has a 95% CI that excludes 0.

| Scenario | control (v2-tuned) | v4 chosen |
|---|---|---|
| bursty_takers | 2.284 [2.236, 2.331] | 2.309 [2.270, 2.350] |
| realistic_mix | 2.419 [2.361, 2.481] | 2.443 [2.390, 2.500] |

## Full grid

| Base | a | Half-life | Sharpe no_informed | Sharpe base | Sharpe toxic | Worst case |  |
|---|---|---|---|---|---|---|---|
| 3 | 0 | off | 2.01 [1.55, 2.48] | 2.82 [2.36, 3.30] | 4.14 [3.66, 4.62] | 2.01 |  |
| 3 | 0 | 20 | 2.28 [1.82, 2.76] | 2.93 [2.46, 3.42] | 4.10 [3.59, 4.59] | 2.28 |  |
| 3 | 0 | 100 | 2.33 [1.86, 2.82] | 2.94 [2.46, 3.45] | 4.20 [3.73, 4.68] | 2.33 |  |
| 3 | 0.5 | off | 2.64 [2.15, 3.15] | 3.10 [2.62, 3.59] | 3.83 [3.33, 4.34] | 2.64 |  |
| 3 | 0.5 | 20 | 2.76 [2.24, 3.31] | 3.02 [2.48, 3.58] | 3.65 [3.10, 4.21] | 2.76 |  |
| 3 | 0.5 | 100 | 2.80 [2.27, 3.36] | 3.16 [2.64, 3.68] | 3.92 [3.39, 4.46] | 2.80 | ◀ chosen |
| 3 | 1 | off | 2.12 [1.64, 2.62] | 2.21 [1.69, 2.71] | 2.45 [1.99, 2.89] | 2.12 |  |
| 3 | 1 | 20 | 1.90 [1.43, 2.36] | 1.88 [1.36, 2.40] | 2.06 [1.53, 2.60] | 1.88 |  |
| 3 | 1 | 100 | 2.10 [1.57, 2.63] | 2.17 [1.62, 2.72] | 2.35 [1.89, 2.82] | 2.10 |  |
| 3 | 2 | off | 1.48 [1.01, 1.92] | 1.44 [1.00, 1.86] | 1.52 [1.08, 1.93] | 1.44 |  |
| 3 | 2 | 20 | 1.55 [1.05, 2.06] | 1.36 [0.89, 1.81] | 1.42 [0.95, 1.87] | 1.36 |  |
| 3 | 2 | 100 | 1.55 [1.09, 2.00] | 1.41 [0.96, 1.83] | 1.50 [1.03, 1.93] | 1.41 |  |
| 4 | 0 | off | 2.64 [2.15, 3.15] | 3.10 [2.62, 3.59] | 3.83 [3.33, 4.34] | 2.64 | ◀ control |
| 4 | 0 | 20 | 2.79 [2.26, 3.36] | 3.09 [2.57, 3.61] | 3.78 [3.29, 4.27] | 2.79 |  |
| 4 | 0 | 100 | 2.77 [2.25, 3.33] | 3.19 [2.68, 3.71] | 3.90 [3.36, 4.45] | 2.77 |  |
| 4 | 0.5 | off | 2.45 [1.99, 2.93] | 2.69 [2.16, 3.23] | 3.11 [2.60, 3.61] | 2.45 |  |
| 4 | 0.5 | 20 | 2.31 [1.79, 2.84] | 2.21 [1.69, 2.74] | 2.63 [2.12, 3.13] | 2.21 |  |
| 4 | 0.5 | 100 | 2.33 [1.82, 2.87] | 2.40 [1.88, 2.94] | 2.74 [2.24, 3.23] | 2.33 |  |
| 4 | 1 | off | 1.78 [1.31, 2.25] | 1.78 [1.29, 2.26] | 1.87 [1.42, 2.31] | 1.78 |  |
| 4 | 1 | 20 | 1.50 [1.06, 1.93] | 1.56 [1.07, 2.05] | 1.66 [1.15, 2.16] | 1.50 |  |
| 4 | 1 | 100 | 1.47 [1.04, 1.88] | 1.46 [0.97, 1.93] | 1.64 [1.17, 2.09] | 1.46 |  |
| 4 | 2 | off | 1.48 [1.02, 1.93] | 1.42 [0.97, 1.85] | 1.52 [1.08, 1.93] | 1.42 |  |
| 4 | 2 | 20 | 1.56 [1.05, 2.07] | 1.36 [0.89, 1.81] | 1.40 [0.92, 1.87] | 1.36 |  |
| 4 | 2 | 100 | 1.52 [1.07, 1.98] | 1.38 [0.93, 1.80] | 1.52 [1.06, 1.95] | 1.38 |  |
| 5 | 0 | off | 2.45 [1.99, 2.93] | 2.69 [2.16, 3.23] | 3.11 [2.60, 3.61] | 2.45 |  |
| 5 | 0 | 20 | 2.64 [2.12, 3.20] | 2.65 [2.12, 3.19] | 3.11 [2.57, 3.63] | 2.64 |  |
| 5 | 0 | 100 | 2.69 [2.16, 3.24] | 2.74 [2.20, 3.28] | 3.19 [2.65, 3.72] | 2.69 |  |
| 5 | 0.5 | off | 1.78 [1.32, 2.24] | 1.76 [1.26, 2.25] | 1.84 [1.39, 2.28] | 1.76 |  |
| 5 | 0.5 | 20 | 1.85 [1.36, 2.34] | 1.77 [1.27, 2.26] | 1.84 [1.37, 2.31] | 1.77 |  |
| 5 | 0.5 | 100 | 1.80 [1.31, 2.28] | 1.86 [1.35, 2.36] | 1.95 [1.50, 2.37] | 1.80 |  |
| 5 | 1 | off | 1.48 [1.01, 1.92] | 1.44 [1.00, 1.86] | 1.51 [1.07, 1.92] | 1.44 |  |
| 5 | 1 | 20 | 1.55 [1.05, 2.06] | 1.33 [0.86, 1.79] | 1.38 [0.91, 1.83] | 1.33 |  |
| 5 | 1 | 100 | 1.55 [1.09, 2.00] | 1.41 [0.95, 1.83] | 1.52 [1.06, 1.95] | 1.41 |  |
| 5 | 2 | off | 1.48 [1.02, 1.93] | 1.42 [0.97, 1.85] | 1.52 [1.08, 1.93] | 1.42 |  |
| 5 | 2 | 20 | 1.60 [1.07, 2.11] | 1.36 [0.90, 1.81] | 1.40 [0.92, 1.88] | 1.36 |  |
| 5 | 2 | 100 | 1.52 [1.07, 1.98] | 1.39 [0.95, 1.81] | 1.55 [1.10, 1.97] | 1.39 |  |
