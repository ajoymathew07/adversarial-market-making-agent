# 10: v4 adapts to the flow intensity and to its own uncertainty

## Hypothesis

v2's noise model was calibrated once on base. In bursty or fat-tailed markets, tracking the
current flow intensity and the filter's own uncertainty should make it overreact less to noise
bursts and quote wider when unsure.

## Mechanism

v4 (`adaptive`, `[agent.adaptive]`) is the tuned control (v2 fair value, v1 skew, its own base
spread) with two optional features, both from the agent's own observations only.

```
o = own filled lots last step          e = expected_flow(λ, fv, posted quotes).lots
O ← d·O + (1 − d)·o,  E ← d·E + (1 − d)·e,   d = 0.5^(1 / intensity_halflife)
ρ = clip(O / E, min_scale, max_scale)        ρ = 1 while E = 0, or when intensity_halflife = 0
filter: λ → λ·ρ in expected_flow, so h, H and R all scale with ρ
half_spread = clip(round_half_away(base + a·√P), base, max_half_spread)     P = posterior var
```

The filter at an observation uses the ρ from the observations before it, so a fill does not set
its own noise level. (4, 0, off) quotes exactly as `kalman_tuned` (tested, episode for episode).

## Sweep

`make sweep-adaptive`, dev seeds 0–29, training scenarios, worst-case mean Sharpe; base ∈ {3, 4,
5} × a ∈ {0, 0.5, 1, 2} × intensity_halflife ∈ {off, 20, 100}.

| | Config | Worst-case Sharpe (dev) |
|---|---|---|
| Control | (4, 0, off) | 2.64 |
| Best, intensity on, a = 0 | (4, 0, 20) | 2.79 |
| **Chosen** | (3, 0.5, 100) | **2.80** (+0.16) |
| Diagnostic: control with constant λ × 0.6 / 0.8 | | 2.76 / 2.71 |

- The uncertainty term is almost a constant: P settles near its steady state, so a = 0.5 adds
  about one tick and base 3 + 0.5·√P ≈ 4 (mean half-spread 4.03–4.10). (3, 0.5, off) is
  identical to the control. a ≥ 1 always loses.
- ρ averages 0.70–0.88 on training scenarios, not 1: the calibrated model overpredicts our fills
  at a 4-tick spread. A constant λ factor of 0.6–0.8 recovers most of the gain, so most of it is
  a level correction of λ, not tracking.

## Detection (dev, bursty_takers, chosen config)

| | Value |
|---|---|
| Mean ρ, busy / calm steps | 0.83 / 0.71 (true busy/calm rate ratio 6) |
| corr(ρ_t, busy_t), per episode | 0.23 [0.20, 0.26] |
| Fair-value RMSE, control → v4 | bursty 2.28 → 2.31, realistic_mix 2.42 → 2.44 (not significant) |

ρ moves in the right direction but weakly and slowly (half-life 100 steps against 20-step busy
spells), and it does not improve the fair value.

## Verdict: a small, mostly level-correction gain; tracking is weak

Held-out (`docs/results/v4-adaptive/heldout.md`): worst-case Sharpe over the training scenarios
2.87 against the control's 2.79; no training-scenario Sharpe difference is significant. On
unseen scenarios v4 is significantly better in bursty_takers (3.17 vs 2.96), realistic_mix (2.45
vs 2.19) and heavy_tail_takers (2.99 vs 2.86), and significantly worse in uniform_takers (1.89
vs 2.08). Fair-value RMSE is slightly worse almost everywhere. The hypothesis' mechanism (better
fair value in bursty markets) is not what we see; the gain in bursty markets comes with a wider
average spread (4.2–4.5) instead.

## Untuned choices

min_scale = 0.25, max_scale = 4, max_half_spread = 8; the filter uses the previous ρ; the
expected lots use the calibrated λ (ρ = 1) at the fair value the quotes were placed around.
