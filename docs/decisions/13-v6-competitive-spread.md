# 13: v6 narrows its spread when its volume share falls (rejected: d = 0 wins)

## Hypothesis

Against v1 (half-spread 2) a fixed 4-tick agent keeps 21% of maker volume and makes about zero
(decision 12). If the agent narrows its spread when its share of traded volume drops, and goes
back to its tuned width when alone, it keeps flow against tighter rivals without losing its edge
alone.

## Agent

`competitive` is v5's `AdaptiveMarketMaker` with one optional term (`mm.agent.competition`),
from its own Observation only:

    share = EWMA(own fill lots) / EWMA(public trade lots)   (1 before any trade; ≡ 1 alone)
    effective base = clip(round_half_away(base − d·(1 − share)), min_half_spread, base)

The effective base replaces v5's base; v4's intensity, v3's c·T, skew and size are unchanged.
`[agent.competitive]` repeats v5's knobs plus `share_halflife`, `undercut_per_share` (d) and
`min_half_spread`. With d = 0 it equals `final` episode for episode (tested).

## Sweep (`docs/results/v6-competitive/dev-sweep.md`)

Dev seeds, training scenarios no_informed, base, toxic and vs_v1, worst-case Sharpe. Full grid d
{0..4} × min {2,3} × half-life {50,200} × base {4,5}, d = 0 once per base (34 configs).

| Config (d, min, half-life, base) | Sharpe vs_v1 (dev) | Worst case (dev) |
|---|---|---|
| **v5 = chosen** (0, —, —, 5) | 0.11 | **0.113** |
| Best d > 0 (1, 2, 50, 5) | −0.01 | −0.006 |
| v5 at base 4 (0, —, —, 4) | −0.01 | −0.007 |
| Most aggressive (4, 2, 200, 4) | −3.16 | −3.158 |

The signal works: share is 1.00 alone and 0.16 in vs_v1. The response does not: every d > 0
lowers Sharpe in vs_v1, roughly more so as d grows. The likely reason (consistent with decision
12, where v1 and v2 lose money at 2 ticks in vs_v1): the extra flow won by quoting tighter does
not earn enough spread to cover the informed lots that come with it. The solo scenarios are
unchanged since share ≡ 1. So the frozen v6 is v5.

## Held-out (`docs/results/v6-competitive/heldout.md`)

v6 equals v5 in every scenario (no ✔). Overfitting check: worst case 0.113 dev, 0.293 held-out
for both. Undercutting war (vs_competitive): with d = 0 it is v5 self-play (6.92 / 7.33 PnL). The
not-chosen d = 1 config, as a diagnostic, does not race to the floor: against itself its base
averages 4.5 and both stay profitable (6.57 / 6.25), slightly below v5 self-play; against v1 it
lifts its volume share to 23% but its PnL falls to −0.21.

## Default

v5 stays the default and `make run` keeps its four agents: v6 at its argmax is v5, so switching
adds a name, not a behaviour.

## Untuned choices

The grid, the half-away rounding, and EWMAs per observation (not per lot).
