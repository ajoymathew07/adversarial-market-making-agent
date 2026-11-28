# 04: Evaluation

## PnL decomposition

Final PnL splits exactly into three parts (summation by parts, tested to float tolerance):

```
final PnL      = spread capture + inventory PnL - fees
spread capture = sum over fills of s * (V(t_fill) - price) * size
inventory PnL  = sum over t of q_t * (V(t+1) - V(t))
```

s is +1 for an agent buy and -1 for a sell; q_t is the position after step t. It shows where money
is made or lost. Adverse selection shows up as good fill prices (positive spread capture) followed
by inventory losses, because informed takers leave the agent holding the wrong side.

## Markouts by counterparty kind

For each fill and horizon τ in {0, 1, 5, 10, 20}: s * (V(t+τ) - price) per lot, size-weighted,
reported separately for noise and informed fills. Evaluation may read the hidden taker kind; the
agent never does.

## Other metrics

Max drawdown and Sharpe (per-step mean / std × √T, unannualised) of the mark-to-market path
cash_t + q_t × V(t); fill counts, lots and fill rate; mean and max |q| and time at the limit;
gate events by rule. Money is in price units.

## Seeds and confidence intervals

Each scenario runs 30 seeds. Every metric is reported as the mean with a 95% percentile-bootstrap
interval (10,000 resamples, fixed seed). It needs only numpy and assumes no normality.

Development seeds 0–29 are for tuning; held-out seeds 1000–1029 are only for reported numbers, so
tuning cannot overfit them. `make run` uses the held-out set. Seed ranges, markout horizons and
bootstrap settings are set under `[evaluation]` in `config/default.toml`.

## Paired comparison

`--agents naive,other` runs every agent on the same scenario × seed grid; the first is the
baseline. The market's random draws never depend on the agent, so the same seed gives every agent
the same true-value path and the same takers. The per-seed difference (agent − baseline) therefore
removes the market's randomness, and its bootstrap CI is much tighter than comparing two separate
averages. We report the mean difference with a 95% percentile-bootstrap CI on those differences
for PnL, its parts, drawdown, Sharpe, inventory and informed markout at τ=10. A difference is
significant when its CI excludes 0.

## Output

A console summary per agent, comparison tables, `results/report.md`, `results/episodes.csv` (one
row per agent × scenario × seed) and
matplotlib plots: PnL and inventory paths for one seed, and markout curves by kind.

## Determinism

`make determinism` (also a CI step) runs a short evaluation twice in Docker and fails if the
SHA-256 of `episodes.csv` differs.
