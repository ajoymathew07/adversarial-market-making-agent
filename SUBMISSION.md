**Submission Header:** Problem 3 – Adversarial Market-Making Agent
**Candidate Name:** Ajoy Mathew
**Institution & Roll Identifier:** IIT Madras | CS23B101
**GitHub Repository Link:** https://github.com/ajoymathew07/adversarial-market-making-agent
**Target Commit Hash:** TBD

<!-- Strict limit: 800 words for the sections below. -->

## 1. Problem Definition

A market maker quotes a bid and an ask and earns the spread from uninformed traders. Informed traders know where the price is heading, so trading with them loses money: adverse selection. The goal is an agent that stays profitable against toxic flow, and against competing makers, within a position limit. No data is given, so I built the market simulator too. Results must hold on held-out seeds and unseen scenarios.

## 2. Solution Approach with Use Case

1. `make run` evaluates v1, v2, v2-tuned and the final agent (v5) on 30 held-out seeds in 13 scenarios.
2. It prints means with 95% bootstrap CIs and paired per-seed comparisons on identical markets.
3. It writes a report, CSV and plots to `results/`.

Each version tests one hypothesis against a tuned control. I tune on dev seeds 0–29 for worst-case Sharpe across training scenarios, then report once on seeds 1000–1029. Agents estimate taker behaviour from their own fills; they never read simulator parameters.

## 3. User Interface Design

- **CLI:** `python -m mm --agents skew,final --seeds heldout --scenarios base toxic`; the first agent is the baseline.
- **Config:** every parameter lives in `config/default.toml`; scenarios are override tables.
- **Outputs:** `report.md`, `episodes.csv`, and plots of PnL, inventory and markouts by taker kind.

## 4. System Architecture & Technical Approach

- **Market:** hidden value V is a random walk (σ = 1 tick). Noise takers fill a quote d ticks away with probability e^(−kd). Informed takers see V(t+10).
- **v1:** Avellaneda–Stoikov reservation price, with quotes skewed against inventory.
- **v2:** Kalman-filter fair value from order-flow imbalance.
- **v5 (final):** v2 with a 5-tick half-spread, strong skew (0.2 ticks/lot) and online flow intensity, tuned jointly.
- **Book:** FIFO queues per integer-tick price; exact price-time matching.
- **Monitor:** incremental, O(n) per episode.

## 5. Invariants, Concurrency & Edge Conditions

| Invariant | Enforced by |
|---|---|
| Position limit, sane orders | `apply_gate`, the only path to the book; clips to worst-case capacity |
| No self-cross, post-only against other makers | gate rejects crossing quotes |
| No double fills, PnL reconciles, uncrossed book | monitor after every step, for every maker; halts on violation |
| Determinism | seeded generators; CI compares digests |

The loop is single-threaded. Tests cover price-band edges, partial fills, FIFO ties, tampered cash, an agent held at the limit, competitor priority and self-play.

## 6. Empirical Benchmarks & Performance Metrics

Held-out seeds 1000–1029, 2000 steps each, 15% informed takers, PnL in price units. ✔: the paired difference from v2-tuned excludes 0.

| Scenario | Sharpe v1 | v2 | v2-tuned | v5 | PnL v2-tuned | v5 |
|---|---|---|---|---|---|---|
| base | 0.18 | 1.10 | 3.23 | 4.61 ✔ | 16.4 | 14.4 ✔ |
| toxic | 0.41 | 2.80 | 4.01 | 5.19 ✔ | 20.8 | 17.2 ✔ |
| realistic_mix (unseen) | −0.54 | 0.17 | 2.19 | 3.01 ✔ | 10.9 | 9.3 ✔ |
| vs_v1 competitor | −1.17 | −1.17 | 0.08 | 0.29 ✔ | −0.4 | 0.5 |

- v5's Sharpe is significantly above v2-tuned's in all 13 scenarios (v4 edges it against v1). Drawdown halves in the solo scenarios, but PnL is lower than v2-tuned's in most. Its dev and held-out worst case match (4.23, 4.27), so there's no overfitting.
- Negative results: toxicity widening (v3), regime tracking (v4) and undercutting rivals (v6) did not beat their controls.
- Throughput: about 75,000 steps/s with v5 (`make bench`, Apple M5, Python 3.14).

## 7. Trade-Off Analysis & Scalability Limits

- **Simulator over data:** ground truth for adverse selection. A BTCUSDT check confirmed exponential fill decay and found bursty arrivals, heavy-tailed sizes and fat tails, now stress scenarios.
- **Sharpe over PnL:** v5 trades profit for stability.
- **Discrete steps, Python:** readable and deterministic, with one-step latency.
- **10× scale:** the single-core loop dominates. Seeds are independent, so the sweeps already use a process pool; long episodes would need vectorised taker generation.
- **Limitation:** noise flow never moves V.

## 8. AI Assistance Audit Log

Claude Code (Claude Opus 5.5) orchestrated implementation subagents. I settled designs in chat and reviewed and merged every PR.

- **Parameter leak:** agents used the simulator's true parameters, so v2 was right by construction. I caught it by asking how a real market maker would know them. Fix: a no-market-knowledge rule and calibration from training seeds.
- **Kalman lock:** capping fill probability gave zero slope at the position limit, so fair value froze. Fix: uncapped intensity and a regression test.
- **v3 markout:** fills were marked against a fair value the filter moves because of the fill, so the score ranked no-informed markets most toxic. Caught by a detection check and a fixed-spread control.

Full log: `docs/ai_audit_log.md`.
