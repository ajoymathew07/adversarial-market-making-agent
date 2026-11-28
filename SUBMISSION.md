**Submission Header:** Problem 3 – Adversarial Market-Making Agent
**Candidate Name:** Ajoy Mathew
**Institution & Roll Identifier:** IIT Madras | CS23B101
**GitHub Repository Link:** https://github.com/ajoymathew07/adversarial-market-making-agent
**Target Commit Hash:** TBD

<!-- Strict limit: 800 words for the sections below. -->

## 1. Problem Definition

A market maker quotes a bid and an ask and earns the spread from uninformed traders. Informed traders know where the price is heading, so trades with them lose money afterwards: adverse selection. The goal is an agent that stays profitable against this toxic flow within a position limit, plus a simulated market to test it in, since no data is given. Results must hold on held-out seeds and unseen scenarios.

## 2. Solution Approach with Use Case

1. `make run` evaluates the configured agent on 30 held-out seeds in every scenario.
2. It prints means with 95% bootstrap CIs and paired per-seed differences between agents.
3. It writes a report, CSV and plots to `results/`.

Trade-offs: each agent version changes one thing, so its effect is measurable. I tune on dev seeds 0–29 and report on 1000–1029. Taker parameters come from the agent's own fills, not the simulator.

## 3. User Interface Design

- **CLI:** `python -m mm --agents naive,skew,kalman --seeds heldout --scenarios base toxic`; the first agent is the baseline.
- **Make targets:** listed in the README.
- **Config:** every parameter is in `config/default.toml`; scenarios are override tables, so changing a limit is a config edit.
- **Outputs:** `report.md`, `episodes.csv` (one row per agent, scenario and seed) and plots of PnL, inventory and markouts by taker kind.

## 4. System Architecture & Technical Approach

- **Value:** V(t+1) = V(t) + σε (σ = 1 tick), hidden from the agent.
- **Noise takers:** exponential tolerance: a quote d ticks from V fills with probability e^(−kd).
- **Informed takers:** 15% of arrivals; see V(t+10), need 1 tick of edge.
- **v1:** quotes ±2 ticks around the Avellaneda–Stoikov reservation price r = last trade − q·skew.
- **v2:** centres on a Kalman-filter fair value updated by order-flow imbalance.
- **Calibration:** a log-linear fit of fills against quote distance on training seeds gives arrival rate and k.
- **Book:** FIFO queues per integer-tick price and a sorted price list: exact matching.
- **Monitor:** updated from new fills only, O(n) not O(n²).

## 5. Invariants, Concurrency & Edge Conditions

| Invariant | Enforced by |
|---|---|
| Single gate, position limit | `apply_gate`, the only path to the book, clips size to capacity |
| No self-cross | gate rejects bid ≥ ask; the book raises on a crossing post |
| No double fills, PnL reconciles, uncrossed book | monitor after every step; halts on violation |
| Determinism | one seeded generator; CI compares output digests |

The loop is single-threaded: no races. Tests cover price-band edges, crossed quotes, partial fills, FIFO ties, overfills, tampered cash, random order flow, an agent held at the limit and every scenario.

## 6. Empirical Benchmarks & Performance Metrics

TBD: final held-out benchmark table (v1–v5) goes here.

## 7. Trade-Off Analysis & Scalability Limits

- **Simulator:** gives ground truth to measure adverse selection. A BTCUSDT check found bursty arrivals, heavy-tailed sizes and fat tails; these are now stress scenarios.
- **Only our maker:** every fill is attributable; no competition for flow.
- **Discrete steps:** one-step quote latency.
- **Python:** readable. Recomputing invariants each step took 11.95 s for 32,000 steps; incremental checks take 0.29 s. At 10× scale the single-core loop dominates; seeds are independent, so a process pool would fix it.
- **Limitation:** noise flow never moves V.

## 8. AI Assistance Audit Log

Claude Code (Claude Opus 5.5) orchestrated implementation subagents; I settled designs in chat and reviewed and merged every PR.

- **Parameter leak:** the agents used the simulator's true parameters, so v2 was right by construction. I caught it by asking how a real market maker would know them. Fix: a no-market-knowledge rule and calibration on training seeds.
- **Kalman lock:** capping fill probability at 1 gave zero slope at the position limit, so fair value froze (one seed: 60% of the episode at the limit). Fix: an uncapped arrival intensity and a regression test.
- **CI and pushes:** a Python version the runner lacked; two pushes after failing checks. Fixed with the Docker base image and by reading exit codes.

Full log: `docs/ai_audit_log.md`.
