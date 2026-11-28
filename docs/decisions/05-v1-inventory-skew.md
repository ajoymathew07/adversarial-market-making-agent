# 05: v1 inventory skew

## Problem

v0 ignores its position. On held-out seeds it sits at the ±50 limit 24% (no_informed), 34% (base)
and 48% (toxic) of the time, and inventory PnL (-7.28 base, -17.19 toxic) cancels most of its
spread capture (10.59, 17.66). See `docs/results/v0-naive/report.md`.

## Change

v1 changes one thing: it quotes around the Avellaneda–Stoikov reservation price

```
r = centre − q · γ · σ² · τ
```

with centre = last trade price and q = position. Inventory is risk, so when long the agent lowers
its own price: the ask gets hit more and the bid less, pulling q back to zero. γ is risk aversion;
σ (ticks per step) and τ (steps) are the agent's own assumptions in `[agent.skew]`, not the
market's σ, which the agent cannot observe. Quotes are r ± 2 ticks, 5 lots per side.

## Rounding

The shift q·γσ²τ is rounded to whole ticks with **halves away from zero** (changed from the
originally agreed "nearest tick, half up"). With γ = 0.005 exact halves occur at q = ±10, ±30, ±50:

| Rule | q = +10 | q = −10 | q = +30 | q = +50 | Problem |
|---|---|---|---|---|---|
| Half up | 0 | −1 | 2 | 3 | Longs and shorts skew differently: a directional bias |
| Half to even (`round`) | 0 | 0 | 2 | 2 | 30 and 50 lots get the same skew |
| **Half away from zero** | **1** | **−1** | **2** | **3** | Symmetric and monotonic |

At an exact half it rounds toward more skew, i.e. faster unwinding: the risk-averse choice. The
spread stays exactly 2 ticks each side and γ = 0 still reproduces v0. Rounding the bid down and
the ask up was rejected for v1: it widens the spread by a tick about half the time, which would
change two things at once.

Price skew only. Size skew was rejected for now so the comparison with v0 isolates one change.
The full GLFT optimal spread was rejected because its closed form needs fill-intensity parameters
the agent would have to estimate live.

## γ

**γ = 0.005** (0.05 ticks of shift per lot), chosen on dev seeds 0–29 only
(`docs/results/v1-skew/dev-sweep.md`). It is the only γ with positive mean PnL in both base and
toxic, and it has the best worst-case Sharpe across the two (0.31). γ = 0.01 was best in toxic
alone but slightly negative in base; γ ≥ 0.02 skews so far that spread capture collapses.
Held-out seeds were run once, after the choice (`docs/results/v1-skew/heldout/`).
