# 07: Agent parameters come from training seeds, not the market

## The leak

`[agent.kalman]` (σ, λ, s̄, E[s²], k) and `[agent.skew]` σ were copied from `[market]`. A real
market maker never knows how takers behave, so v2's results were optimistic.

## Rule

Agents never use the market's parameters or formulas. Every agent parameter is a stated choice or
is estimated/tuned on dev seeds, then frozen for held-out testing (CLAUDE.md).

## Calibration

A calibration agent (`mm.agent.calibration`) quotes each side at a random 1–5 ticks from its
centre, 10 lots, from its own RNG (`PCG64([seed, 1])`), so the market's path and takers are
unchanged (tested). Its centre is v1's skewed last trade price. Stopping one side at |q| ≥ 25
instead left it one-sided 81% of the time with its trade price 27 ticks (RMS) from V (σ̂ = 0.42);
with the skew that gap is 2.4 ticks.

From its own observations only (`mm.calibration`, base dev seeds 0–29): a least-squares line
through log(mean fills per quote) against distance gives λ̂ and k̂; fill sizes give ŝ and Ê[s²];
σ̂² is the mean squared 50-step change in the last trade price, divided by 50.

| | σ | λ | k | s̄ | E[s²] |
|---|---|---|---|---|---|
| Estimated | 1.04 | 1.01 | 0.38 | 3.50 | 16.44 |
| True | 1.00 | 1.00 | 0.60 | 3.00 | 11.00 |

The gaps are explained in `docs/results/calibration.md`.

## v1

γ, σ and τ only ever mattered through γσ²τ, which was tuned, so they are now one parameter,
`skew_per_lot = 0.05`. Results are byte-identical.

## Still assumed

The agent still assumes the exponential fill shape. The model-shape stress scenarios test that
separately.
