# 11: v5 tunes every knob jointly for the worst case

## Hypothesis

The knobs interact (base spread, skew_per_lot, quote_size, a, intensity_halflife, v3's c), so
tuning them jointly for the worst case beats tuning each alone.

## Agent

No new logic. `final` is v4's `AdaptiveMarketMaker` with v3's toxicity score as an optional
term: half_spread = clip(round_half_away(base + a·√P + c·T), base, max). `[agent.final]` holds
every knob; its own skew_per_lot and quote_size replace `[agent.skew]`'s. With the control's
knobs it equals `kalman_tuned` episode for episode (tested). `[agent] type = "final"`.

## Search

`make tune`: 200 configs, seeded (PCG64(0)) without replacement from base {3,4,5,6} ×
skew_per_lot {0.02,0.05,0.1,0.2} × quote_size {2,3,5,8} × a {0,0.5,1,2} × half-life {off,20,100}
× c {0,1,2}, τ = 5, plus the control and v4. Dev seeds, training scenarios, worst-case Sharpe.
Wall time 202 s, so no reduction to 120.

| | Config (base, skew, size, a, half-life, c) | Worst-case Sharpe (dev) |
|---|---|---|
| Control | 4, 0.05, 5, 0, off, 0 | 2.64 |
| v4 | 3, 0.05, 5, 0.5, 100, 0 | 2.80 |
| **Chosen** | 5, 0.2, 8, 0, 100, 1 | **4.23** |
| Ablation: control with skew_per_lot 0.2 only | 4, 0.2, 5, 0, off, 0 | 4.20 |
| Ablation: chosen with c = 0 | 5, 0.2, 8, 0, 100, 0 | 4.27 |

Almost all of the gain is skew_per_lot: v1's 0.05 was tuned at half-spread 2 and was never
re-tuned. c adds nothing (removing it scores slightly higher); intensity adds about +0.1; a = 0
wins. skew_per_lot and quote_size are at the edge of the grid, so the optimum may lie beyond.

## Held-out (`docs/results/v5-final/heldout.md`, `docs/results/summary.md`)

v5 has a significantly higher Sharpe than v2-tuned in every scenario (e.g. base 4.61 vs 3.23,
realistic_mix 3.01 vs 2.19) and half the max drawdown, but a significantly lower final PnL in
most (base 14.4 vs 16.4): the strong skew keeps inventory small, which removes variance and
some profit. Sharpe was the objective; on a PnL objective v5 would not win.

| Overfitting check | Dev worst case | Held-out worst case |
|---|---|---|
| Control | 2.64 | 2.79 |
| v4 | 2.80 | 2.87 |
| v5 | 4.23 | 4.27 |

No drop for v5, so no sign that the 200-config search overfit the dev seeds.

## Untuned choices

min_scale 0.25, max_scale 4, max_half_spread 8, ewma_halflife 50 lots, τ = 5, the search seed
and the grid itself. The argmax is frozen as the protocol says, even though its c = 0 ablation
scored marginally higher.
