# 0005: Architecture rules

**Status:** Accepted (2026-11-27)

## Context
Correctness rests on a few invariants, and constraints may change during the live defence.

## Decision
- **Module boundaries:** engine, market, agent, risk and eval are separate modules that talk
  through small typed interfaces, so each part can be tested alone.
- **Single order gate:** every agent order passes one function in `mm.risk` that enforces limits,
  no self-cross, sanity and rate limits. One place to prove correct.
- **Runtime invariant monitor:** after every step, check PnL reconciliation, position limits, no
  double fills and an uncrossed book; halt on violation. Bugs surface in every run.
- **Config-driven parameters:** all tunables live in one typed config object, so a changed
  constraint is a config edit, not a code change.

## Alternatives considered
Checks spread across agent and engine, or invariants tested only in pytest: simpler at first,
harder to trust.

## Consequences
More plumbing up front; the gate and monitor add per-step cost.
