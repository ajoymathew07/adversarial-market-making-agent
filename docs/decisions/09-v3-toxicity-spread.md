# 09: v3 widens its spread when its own fills go against it

## Hypothesis

Widening the spread when the agent's recent fills keep going against it reduces adverse
selection by more than it costs in spread capture.

## Mechanism

v3 is v2 (Kalman fair value, v1 skew, `[agent.skew]`) with one change: the half-spread.

```
m = s · (fv(t_fill + τ) − price)        per-lot markout in ticks; s = +1 buy, −1 sell
a ← d^w · a + (1 − d^w) · m             each fill of w lots once τ steps have passed
d = 0.5^(1 / ewma_halflife),  a₀ = 0
T = max(0, −a)                          toxicity score, ticks
half_spread = clip(round_half_away(base + c · T), base, max_half_spread)
bid, ask = r ∓ half_spread              r = v2's reservation price, unchanged
```

Fills younger than τ steps are pending and not scored. The update weights lot by lot, so an old
markout's weight halves every `ewma_halflife` lots of matured fills. Starting at a = 0 means no
evidence of toxicity at the open; the score restarts each episode. With c = 0, v3 is v2 exactly
(tested).

## Why these choices

| Choice | Why | Rejected |
|---|---|---|
| Markout against the agent's own later fv | The agent sees no true value and no taker labels; its fv is its best view of where the price went | True-value markout (a leak); taker kind (not observable) |
| Both sides widen equally | Toxicity says "fills are bad", not which way the value moves; direction is already in fv and the skew | One-sided widening (doubles up on fv's signal) |
| No size signal | Our fills are censored at the quote size; it vanishes once acted on (an informed trader just splits its orders); it would overfit the simulator's 5–10 lot informed sizes. BTCUSDT shows size is a weak, non-monotone signal (`docs/results/realism/`) | Widen on large fills |

## Tuning

`make sweep-toxicity`: τ ∈ {5, 10, 20} × c ∈ {0, 0.5, 1, 2, 4, 8} on dev seeds 0–29, training
scenarios no_informed, base, toxic. Objective: the worst-case mean Sharpe of the three; ties go
to the first row. Result in `docs/results/v3-toxicity/dev-sweep.md`.

## Values

| Key | Value | Source |
|---|---|---|
| markout_horizon (τ) | 20 steps | dev sweep (worst-case Sharpe 0.71; c = 0 gives −0.05) |
| widen_per_tick (c) | 4 | dev sweep |
| ewma_halflife | 50 lots | a choice, not tuned; v5 searches it |
| max_half_spread | 8 ticks | a choice, not tuned |

Held-out results (seeds 1000–1029, every scenario): `docs/results/v3-toxicity/heldout.md`
(`make v3-experiments`).
