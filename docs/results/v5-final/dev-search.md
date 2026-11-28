# v5 final: joint robust tuning, development seeds

Dev seeds 0..29, 2000 steps, training scenarios no_informed, base, toxic. Seeded random search (PCG64(0)) of 200 configs drawn without replacement from the 2304-point grid, always including the control (kalman_tuned) and the frozen v4 config. Objective: the worst case (lowest mean Sharpe) of the three; ties go to the earlier candidate. Mean Sharpe [95% CI] over seeds. Fixed: τ = 5; untuned choices min_scale = 0.25, max_scale = 4, max_half_spread = 8, ewma_halflife = 50 lots. Search wall time 202 s.

## Result

Best worst-case Sharpe 4.230; margin over v4 +1.432 (v4 2.798) and over the control +1.593 (control 2.636). The top configs differ by less than their 95% CIs, so their order is not meaningful.

## Top 10

| Rank | Base | skew_per_lot | quote_size | a | Half-life | c | Sharpe no_informed | Sharpe base | Sharpe toxic | Worst case |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 5 | 0.2 | 8 | 0 | 100 | 1 | 4.23 [3.82, 4.66] | 4.60 [4.21, 5.00] | 5.14 [4.82, 5.46] | 4.230 |  |
| 2 | 3 | 0.2 | 5 | 0.5 | off | 0 | 4.20 [3.72, 4.68] | 5.44 [5.00, 5.89] | 6.55 [6.16, 6.93] | 4.198 |  |
| 3 | 3 | 0.2 | 8 | 0.5 | 100 | 2 | 4.17 [3.70, 4.63] | 4.85 [4.48, 5.23] | 5.72 [5.38, 6.04] | 4.168 |  |
| 4 | 3 | 0.2 | 8 | 0.5 | 20 | 2 | 4.13 [3.70, 4.57] | 4.86 [4.47, 5.26] | 5.71 [5.43, 6.01] | 4.132 |  |
| 5 | 4 | 0.2 | 8 | 0.5 | 20 | 0 | 3.94 [3.50, 4.38] | 4.16 [3.73, 4.59] | 4.91 [4.58, 5.24] | 3.941 |  |
| 6 | 4 | 0.2 | 8 | 0.5 | 100 | 1 | 3.85 [3.46, 4.24] | 4.22 [3.80, 4.63] | 5.00 [4.67, 5.33] | 3.848 |  |
| 7 | 6 | 0.2 | 5 | 0 | 100 | 1 | 3.71 [3.29, 4.14] | 3.95 [3.49, 4.40] | 4.14 [3.75, 4.52] | 3.709 |  |
| 8 | 3 | 0.2 | 5 | 1 | off | 1 | 3.64 [3.23, 4.06] | 3.74 [3.33, 4.14] | 4.00 [3.61, 4.37] | 3.639 |  |
| 9 | 6 | 0.2 | 8 | 0 | 100 | 2 | 3.59 [3.14, 4.03] | 3.81 [3.37, 4.26] | 4.14 [3.81, 4.46] | 3.586 |  |
| 10 | 4 | 0.2 | 8 | 0.5 | 20 | 2 | 3.51 [3.13, 3.88] | 4.08 [3.67, 4.50] | 4.79 [4.47, 5.12] | 3.507 |  |

## The control and v4 in this search

| Rank | Base | skew_per_lot | quote_size | a | Half-life | c | Sharpe no_informed | Sharpe base | Sharpe toxic | Worst case |  |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 31 | 4 | 0.05 | 5 | 0 | off | 0 | 2.64 [2.15, 3.15] | 3.10 [2.62, 3.59] | 3.83 [3.33, 4.34] | 2.636 | control |
| 27 | 3 | 0.05 | 5 | 0.5 | 100 | 0 | 2.80 [2.27, 3.36] | 3.16 [2.64, 3.68] | 3.92 [3.39, 4.46] | 2.798 | v4 |

## Sensitivity: best worst-case Sharpe per knob value

Over all searched configs with that value, nothing else held fixed.

| Knob | Value | Candidates | Best worst-case Sharpe |
|---|---|---|---|
| Base | 3 | 46 | 4.198 |
| Base | 4 | 48 | 3.941 |
| Base | 5 | 51 | 4.230 |
| Base | 6 | 55 | 3.709 |
| skew_per_lot | 0.02 | 47 | 1.411 |
| skew_per_lot | 0.05 | 56 | 2.798 |
| skew_per_lot | 0.1 | 50 | 3.477 |
| skew_per_lot | 0.2 | 47 | 4.230 |
| quote_size | 2 | 42 | 3.101 |
| quote_size | 3 | 49 | 3.398 |
| quote_size | 5 | 44 | 4.198 |
| quote_size | 8 | 65 | 4.230 |
| a | 0 | 46 | 4.230 |
| a | 0.5 | 52 | 4.198 |
| a | 1 | 54 | 3.639 |
| a | 2 | 48 | 2.546 |
| Half-life | off | 70 | 4.198 |
| Half-life | 20 | 55 | 4.132 |
| Half-life | 100 | 75 | 4.230 |
| c | 0 | 57 | 4.198 |
| c | 1 | 72 | 4.230 |
| c | 2 | 71 | 4.168 |

## Ablation of the chosen config (diagnostic, not candidates)

| Variant | Base | skew_per_lot | quote_size | a | Half-life | c | Sharpe no_informed | Sharpe base | Sharpe toxic | Worst case |
|---|---|---|---|---|---|---|---|---|---|---|
| chosen | 5 | 0.2 | 8 | 0 | 100 | 1 | 4.23 [3.82, 4.66] | 4.60 [4.21, 5.00] | 5.14 [4.82, 5.46] | 4.230 |
| chosen, c = 0 | 5 | 0.2 | 8 | 0 | 100 | 0 | 4.27 [3.84, 4.70] | 4.59 [4.21, 4.99] | 5.14 [4.82, 5.46] | 4.266 |
| chosen, intensity off | 5 | 0.2 | 8 | 0 | off | 1 | 4.04 [3.61, 4.48] | 4.51 [4.12, 4.91] | 5.16 [4.84, 5.47] | 4.037 |
| chosen, a = 0 | 5 | 0.2 | 8 | 0 | 100 | 1 | 4.23 [3.82, 4.66] | 4.60 [4.21, 5.00] | 5.14 [4.82, 5.46] | 4.230 |
| chosen, all three adaptive features off | 5 | 0.2 | 8 | 0 | off | 0 | 4.16 [3.76, 4.58] | 4.55 [4.17, 4.94] | 5.16 [4.84, 5.47] | 4.165 |
| control with the chosen skew_per_lot | 4 | 0.2 | 5 | 0 | off | 0 | 4.20 [3.72, 4.68] | 5.44 [5.00, 5.89] | 6.55 [6.16, 6.93] | 4.198 |
| control with the chosen skew_per_lot and quote_size | 4 | 0.2 | 8 | 0 | off | 0 | 4.05 [3.59, 4.53] | 4.92 [4.52, 5.32] | 5.70 [5.35, 6.05] | 4.051 |
