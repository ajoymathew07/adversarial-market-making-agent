# 12: Competing makers

## Why

The brief runs submissions "against live opposing agents", and the bonus track is a head-to-head
tournament. Until now only our agent quoted (decision 02, option A), so a tighter competitor
taking all the flow was never tested. Our best agent quotes a tuned 4-tick half-spread.

## Design

`market.competitor` is `"none"` (base) or a registry name. The competitor is built by the same
registry from the same `[agent.*]` sections.

| Rule | What it means |
|------|---------------|
| Fair competitor | Own owner id, `Account`, `apply_gate` call (same `[risk]`), `InvariantMonitor` and `Observation` (own fills, posted quotes, position). Either monitor halts the run. |
| Public data | Both see the same `last_step_trades` and `last_trade_price`, which include the other's trades. Neither sees V or the other's quotes. |
| Posting order | Each step both cancel, then post. Who posts first (time priority at equal prices) is drawn with p = 1/2 from `PCG64([seed, market.posting_order_stream])`, stream 2 (1 is calibration, 7 is the realism jitter). |
| Post-only across makers | The gate gets the other maker's best bid and ask; a side that would cross them is rejected as `cross_book`, so makers never trade with each other. Self-cross is unchanged. |
| Takers | Unchanged: `match_ioc` fills best price, then FIFO, across owners. |
| Base unchanged | `"none"` builds nothing extra and draws no extra numbers; the base digest is unchanged. |

Scenarios: `vs_v1` (competitor `skew`, half-spread 2) and `vs_tuned` (competitor `kalman_tuned`,
half-spread 4), otherwise base (15% informed).

The competitor's record is `EpisodeResult.competitor` (same format, same path) and
`ScenarioResult.competitor_metrics`; `episodes.csv` keeps its columns and reports our agent only.

## Limitation

No book-depth visibility: like the existing `Observation`, a maker sees only trades and its own
quotes, so it cannot see that it is being undercut except through fewer fills.

## Results

`make competition` writes `docs/results/competition/heldout.md` (held-out seeds, skew, kalman and
kalman_tuned in both scenarios).
