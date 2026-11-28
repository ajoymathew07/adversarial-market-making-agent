# 09: v3 widens its spread when its own fills go against it

## Hypothesis

Widening the spread when the agent's recent fills keep going against it reduces adverse
selection by more than it costs in spread capture.

## First version and why it failed

It marked each fill against the agent's own fair value τ steps later: m = s·(fv(t+τ) − price).
The Kalman update moves fv against every fill as it absorbs it, so the score measured the
filter's own reaction rather than taker information, and it ranked no_informed as the most toxic.

## Mechanism (corrected)

v3 is v2 (Kalman fair value, v1 skew) with its own half-spread. A fill made in step s first
arrives in observation s + 1; the fv after that observation's update is the reference.

```
m = s · (fv(s + 1 + τ) − fv(s + 1))     ticks per lot; s = +1 buy, −1 sell
a ← d^w · a + (1 − d^w) · m             each fill of w lots once matured; a₀ = 0
d = 0.5^(1 / ewma_halflife)
T = max(0, −a)
half_spread = clip(round_half_away(base + c · T), base, max_half_spread)
bid, ask = r ∓ half_spread              r = v2's reservation price, unchanged
```

Only drift after the filter has absorbed the fill counts. Both sides widen equally, because
direction is already in fv and the skew. No size signal: our fills are censored at the quote
size, the signal vanishes once acted on (an informed trader splits its orders), and it would
overfit the simulator's sizes; BTCUSDT shows size is a weak, non-monotone signal
(`docs/results/realism/`).

## Control requirement

The 2-tick half-spread had never been tuned, so any widening could look like a gain. The
control is v2 with its own tuned half-spread (`kalman_tuned`, `[agent.kalman_tuned]`; v1 and
v2 keep `[agent.skew]`). `make sweep-toxicity`, dev seeds 0–29, training scenarios no_informed,
base, toxic, objective = worst-case mean Sharpe:

- control: half_spread ∈ {2, 3, 4, 5, 6};
- v3: base_half_spread ∈ {2, …, 6} × τ ∈ {5, 10, 20, 40} × c ∈ {0, 0.5, 1, 2, 4, 8}.

v3 counts as working only if its best beats the control's best.

## Verdict: no

| | Chosen | Worst-case Sharpe (dev) |
|---|---|---|
| Control | half_spread = 4 | 2.64 |
| v3 | base 4, τ = 5, c = 0 | 2.64 (identical: c = 0 is the control) |
| Best v3 with c > 0 | base 4, τ = 5, c = 0.5 | 2.61 |

Any widening lowers the worst case once the base spread is tuned. Detection also fails: mean T
on dev is 0.35 (no_informed) > 0.17 (base) > 0.05 (toxic), and across those 90 episodes its
correlation with the informed share of our lots is −0.83 (+0.45 within base, +0.26 within toxic).
Frozen values: `[agent.kalman_tuned] half_spread = 4`; `[agent.toxicity]` base 4, τ = 5, c = 0.
`ewma_halflife = 50` lots and `max_half_spread = 8` were not tuned and remain open choices.

Results: `docs/results/v3-toxicity/dev-sweep.md`, held-out `docs/results/v3-toxicity/heldout.md`.
