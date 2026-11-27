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
- **The author confirms every design decision before it is used.** No choice with a real alternative (data representation, model, parameter, interface, tooling) goes into code, this file or `docs/decisions/` until the author has explicitly confirmed it in chat. A recommendation is not a confirmation. When unsure whether something counts, ask.
- **Keep it simple and defensible.** Prefer a model the author can derive on a whiteboard over a cleverer one.
- **Determinism.** All randomness goes through an explicitly seeded `numpy.random.Generator`; never use global RNG state.
- **Orchestration.** The main session handles design discussion and review; implementation and testing go to subagents where practical, and their output is checked before a PR is opened.
- **Log AI mistakes.** When AI-generated code or reasoning turns out wrong, add an entry to `docs/ai_audit_log.md`.
- **Record decisions** in `docs/decisions/`, in the same PR that implements them. Small setup choices go as a row in `00-project-setup.md`. Major design decisions (models, market structure, strategy) get their own numbered file (`01-...md`, `02-...md`) with the justification they need.

## Architecture rules

- **Module boundaries:** `mm.engine` (order book, matching), `mm.market` (true-value process, counterparty bots, scenarios), `mm.agent` (quoting strategy), `mm.risk` (order gate, invariant monitor), `mm.eval` (metrics, benchmarks, reports). Modules talk through small typed interfaces; the agent never reaches into engine internals.
- **Single order gate:** every order the agent sends goes through one function in `mm.risk` that enforces position limits, no self-cross, size/price sanity and order-rate limits. No other path to the engine.
- **Runtime invariant monitor:** after every simulation step, check PnL reconciliation, position limits, no double fills and an uncrossed book; halt the run on any violation. Runs in every simulation, not only in tests.
- **Config-driven parameters:** all parameter values live in `config/default.toml`; their typed schema and the loader live in `mm/config.py`; no magic numbers in logic. Changing a constraint (e.g. position limit, tick size, latency) must be a config change, not a code change.

## Layout

```
config/        default.toml: every parameter value, commented
src/mm/        Python package (simulator, agent, evaluation as they get added)
tests/         pytest suite: unit, edge-case and invariant tests
docs/          design specs, decisions/, AI audit log
scripts/       repository checks run by CI (layout, pins, word count)
```

## Commands

- `make run`: build the Docker image and run the end-to-end demo
- `make test`: run the test suite inside Docker
- `make venv && make test-local`: same tests in a local virtualenv
- `make verify`: all static checks plus coverage locally (checks, lint, typecheck, coverage)
- `make typecheck`: mypy (strict on `src/`)
- `make coverage`: tests with coverage, fails under 85% on `src/mm`
- `make lint`: ruff
- `make checks`: repository checks (layout, pins, word count)

## Conventions

- Python 3.13, full type hints (mypy strict on src/), small modules with one responsibility.
- Test names describe the behaviour: `test_order_never_fills_beyond_position_limit`.

## Git and PRs

- **Decide first, then build.** Every design choice is discussed and settled with the author in chat
  before implementation starts. Open questions are asked in chat, never left in a PR. A PR only
  carries out decisions the author has already agreed to.
- One PR per moderate change or feature, branched from `main`. The author reviews and merges; never merge yourself.
- Branch names: `feat/...`, `fix/...`, `chore/...`, `docs/...`.
- Commit messages: short imperative subject line, optional body.

### PR description template

Plain, concise sentences. No hype, no filler words, no emoji.

```
## Summary
One or two sentences on what this PR adds.

## Changes made
- `path/or/module`: what was added and the function or logic it uses.

## Testing
| Test | Status |
|------|--------|
| `tests/test_x.py::test_name` | Pass |

## Notes
Anything the reviewer should know (follow-ups, known limitations). Omit if empty.
```
