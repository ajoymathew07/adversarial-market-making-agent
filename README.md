# Adversarial Market-Making Agent

Yubi Engineering Campus Challenge, Problem 3.

A market-making agent that quotes both sides of a limit order book, earning the spread from
uninformed flow while detecting and defending against informed (toxic) flow. The repo also contains
the agent-based market simulator used to develop and evaluate it, since the brief provides no data.

> Status: simulator, risk layer, evaluation harness and agents v0–v2 are in place, with design decisions in `docs/decisions/` and results in `docs/results/`.

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

| Module | Role |
|--------|------|
| `mm.engine` | Limit order book (price-time priority, integer ticks), IOC matching, account |
| `mm.market` | Hidden true-value path, noise and informed takers, arrival regimes |
| `mm.agent` | Quoting strategies, the `Agent` interface and the registry that builds them by name |
| `mm.risk` | Order gate (the only path to the book) and the runtime invariant monitor |
| `mm.eval` | Metrics, bootstrap CIs, paired comparisons, reports, plots and the CLI |

One step of `mm.simulation.run_episode`:

```
       observation          position, cash, own fills, last trades (no V, no taker kind)
            |
       agent.quote          bid/ask price and size, fair-value estimate
            |
       order gate           reject bad size or price, reject a crossed quote, clip to the limit
            |
       book                 cancel the agent's orders, post the gated bid and ask
            |
V(t) -> takers              noise and informed (sees V(t+10)) IOC orders
            |
       fills -> account     position and cash
            |
       invariant monitor    halt on any violation, then record the step
```

### Agents

Selected with `[agent] type` in the config or `--agents a,b` on the CLI.

| Name | Version | Idea |
|------|---------|------|
| `naive` | v0 | Fixed 2-tick half-spread around the last trade price; no inventory awareness |
| `skew` | v1 | Avellaneda–Stoikov reservation price: shift quotes against inventory (`skew_per_lot`, tuned on dev seeds) |
| `kalman` | v2 | v1's skew around a Kalman-filter fair value driven by order-flow imbalance |
| `calibration` | helper | Quotes at random distances so `make calibrate` can estimate `[agent.kalman]` from its own fills |
| | v3–v5 | in progress |

### Scenarios

Defined under `[scenarios]` in `config/default.toml`, each as overrides of the base values.

| Scenario | Change from base |
|----------|------------------|
| `no_informed` | informed share 0 |
| `base` | none (informed share 0.15) |
| `toxic` | informed share 0.40 |
| `uniform_takers` | noise tolerance uniform (hard cutoff) |
| `heavy_tail_takers` | noise tolerance lognormal |
| `bursty_takers` | Markov calm/busy noise arrivals, same mean rate |
| `heavy_tail_sizes` | lognormal noise sizes, same mean |
| `fat_tail_value` | Student-t value steps, same std |
| `realistic_mix` | the last three together |

## Commands

| Target | What it does |
|--------|--------------|
| `make build` | Build the Docker image |
| `make run` | Build and evaluate on held-out seeds in every scenario; writes `results/` |
| `make determinism` | Run a short evaluation twice in Docker and compare `episodes.csv` digests |
| `make test` | Run the test suite in Docker |
| `make venv` | Create `.venv` with pinned runtime and dev dependencies |
| `make test-local` | Run the test suite in the local venv |
| `make lint` | ruff |
| `make typecheck` | mypy, strict on `src/` |
| `make coverage` | Tests with coverage, fails under 85% on `src/mm` |
| `make checks` | Repository checks (layout, pins, word count) |
| `make verify` | checks, lint, typecheck and coverage |
| `make calibrate` | Estimate `[agent.kalman]` on base dev seeds and print it next to the true values |
| `make sweep` | v1 `skew_per_lot` sweep on dev seeds; writes `docs/results/v1-skew/` |
| `make v2-experiments` | v2 vs v1, gain sensitivity and robustness on dev seeds |
| `make stress-tolerance` | v0–v2 under different noise tolerance shapes, dev seeds |
| `make stress-realistic` | v1 vs v2 on base and the realism scenarios, held-out seeds |
| `make realism-data` | Download one day of Binance BTCUSDT aggTrades and verify its checksum |
| `make realism` | Compare simulated taker flow with the BTCUSDT data |
| `make bench` | Median `run_episode` time for growing `n_steps` |
| `make clean` | Remove `.venv` and test caches |
