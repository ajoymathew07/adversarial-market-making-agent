# Decision records

Each design or tooling choice settled with the author gets a short record here, written in the
same PR that implements it. A record states the problem, what was chosen, what else was
considered and what it costs. They also serve as defence notes: the reasoning behind every choice
is written down before anyone asks about it.

## Template

```
# NNNN: Title
**Status:** Accepted (YYYY-MM-DD)
## Context
## Decision
## Alternatives considered
## Consequences
```

## Index

| Number | Title |
|--------|-------|
| [0001](0001-integer-tick-prices.md) | Integer tick prices in the engine |
| [0002](0002-exact-pins-no-deps.md) | Exact pins with `pip install --no-deps` |
| [0003](0003-ci-in-pinned-container.md) | CI static job runs in the pinned Python container |
| [0004](0004-quality-gates.md) | Quality gates: coverage, mypy, ruff |
| [0005](0005-architecture-rules.md) | Architecture rules |
