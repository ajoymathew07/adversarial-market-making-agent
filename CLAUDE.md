# CLAUDE.md

Context and rules for anyone (human or AI) working in this repo.

## Project

Submission for the Yubi Engineering Campus Challenge, **Problem 3: Adversarial Market-Making Agent**.
Build a market-making agent that quotes profitably while staying resilient to adverse selection and
toxic order flow, plus the simulated market it is developed and evaluated in.

- **Hard deadline:** Sunday 29 Nov 2026, 5:00 PM IST. No commits to the submitted branch after that.
- The author must defend every design decision live, so understanding beats feature count.

## Mandates from the brief (do not break these)

1. `make run` builds and runs everything end-to-end in under 3 minutes.
2. All dependencies pinned exactly (`requirements.txt`, Docker base image tag).
3. Automated tests prove core invariants (position limits, no self-cross, no double fills, PnL reconciles).
4. No hardcoded or overfitted logic: tune on one set of seeds, report on held-out seeds and unseen scenarios.
5. `SUBMISSION.md` follows the brief's template and stays under 800 words.

## Working rules

- **Design before code.** Each component gets a short spec in `docs/` that the author agrees to before implementation.
- **Explain non-obvious choices** in code comments or the relevant spec: why, not what.
- **Keep it simple and defensible.** Prefer a model the author can derive on a whiteboard over a cleverer one.
- **Determinism.** All randomness goes through an explicitly seeded `numpy.random.Generator`; never use global RNG state.
- **Log AI mistakes.** When AI-generated code or reasoning turns out wrong, add an entry to `docs/ai_audit_log.md`.

## Layout

```
src/mm/        Python package (simulator, agent, evaluation as they get added)
tests/         pytest suite: unit, edge-case and invariant tests
docs/          design specs and the AI audit log
```

## Commands

- `make run`: build the Docker image and run the end-to-end demo
- `make test`: run the test suite inside Docker
- `make venv && make test-local`: same tests in a local virtualenv

## Conventions

- Python 3.13, type hints on public functions, small modules with one responsibility.
- Prices are integer ticks inside the engine (no float equality on prices); convert only at the edges.
- Test names describe the behaviour: `test_order_never_fills_beyond_position_limit`.

## Git and PRs

- One PR per moderate change or feature, branched from `main`. The author reviews and merges; never merge yourself.
- Branch names: `feat/...`, `fix/...`, `chore/...`, `docs/...`.
- Commit messages: short imperative subject line, optional body explaining why.

### PR description template

Write it the way you'd explain the change to a teammate: plain sentences, no hype, no filler words
like "comprehensive" or "robust", no emoji. Keep it short enough to read in a minute.

```
## Why
One or two sentences on the problem this solves or the reason for the change.

## What
- The main changes, one bullet each, in plain words.

## Decisions worth a look
Anything a reviewer might question: a trade-off made, an alternative rejected and why.
Write "None" if there aren't any.

## How I checked it
The commands run and what they showed (tests, `make run`, a manual check).
```
