# Adversarial Market-Making Agent

Yubi Engineering Campus Challenge, Problem 3.

A market-making agent that quotes both sides of a limit order book, earning the spread from
uninformed flow while detecting and defending against informed (toxic) flow. The repo also contains
the agent-based market simulator used to develop and evaluate it, since the brief provides no data.

> Status: repository scaffold. Components are added one PR at a time; see `docs/` for design specs.

## Quick start

Requires Docker.

```bash
make run
```

This builds the image, evaluates v1 (`skew`, the baseline), v2 (`kalman`), v2-tuned
(`kalman_tuned`) and the final agent v5 (`final`) on the held-out seeds in every scenario, prints a
summary and writes `results/report.md`, `results/episodes.csv` and `results/plots/`. To run the tests:

```bash
make test
```

Without Docker (Python 3.13 recommended):

```bash
make venv && make test-local
```

Realism check of the simulated taker flow against one day of Binance BTCUSDT trades (not part of `make run`; writes `docs/results/realism/`): `make realism-data && make realism`.

## Repository layout

```
├── README.md          this file
├── SUBMISSION.md      technical write-up in the brief's template
├── CLAUDE.md          project rules and PR conventions
├── Dockerfile         pinned container definition
├── Makefile           run / test entry points
├── requirements.txt   exact dependency pins
├── config/            default.toml: every simulation parameter, commented
├── scripts/           repository checks used by CI (`make checks`)
├── src/mm/            Python package
├── tests/             unit, edge-case and invariant tests
└── docs/              design specs, decisions, AI audit log
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every pull request and on pushes to `main`:

- Layout: required files and directories exist (`make checks`)
- Pins: every requirement is `name==version` and the Docker base image has an exact tag (`make checks`)
- Word count: `SUBMISSION.md` report body stays within 800 words (`make checks`)
- Lint: `ruff check .` (`make lint`)
- Type check: `mypy`, strict on `src/` (`make typecheck`)
- Coverage: at least 85% line coverage on `src/mm` (`make coverage`)
- Run time: `make run` from a cold Docker cache finishes in under 3 minutes (`make run`)
- Tests: the pytest suite inside Docker (`make test`)
- Dependency consistency: `pip check` inside the image
- Determinism: a short evaluation run twice in Docker gives the same `episodes.csv` SHA-256 (`make determinism`)

`make verify` runs all the static checks (repository checks, lint, type check, coverage) locally.

## Architecture

To be filled in as components land (simulator, agent, evaluation harness).
