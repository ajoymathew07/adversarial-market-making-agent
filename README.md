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

This builds the image and runs the end-to-end demo. To run the tests:

```bash
make test
```

Without Docker (Python 3.13 recommended):

```bash
make venv && make test-local
```

## Repository layout

```
├── README.md          this file
├── SUBMISSION.md      technical write-up in the brief's template
├── CLAUDE.md          project rules and PR conventions
├── Dockerfile         pinned container definition
├── Makefile           run / test entry points
├── requirements.txt   exact dependency pins
├── src/mm/            Python package
├── tests/             unit, edge-case and invariant tests
└── docs/              design specs and AI audit log
```

## Architecture

To be filled in as components land (simulator, agent, evaluation harness).
