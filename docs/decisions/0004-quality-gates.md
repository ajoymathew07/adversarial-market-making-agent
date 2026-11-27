# 0004: Quality gates: coverage, mypy, ruff

**Status:** Accepted (2026-11-27)

## Context
The brief judges rigor and testing. Claims like "well tested" need evidence that CI checks on
every change.

## Decision
- Line coverage of at least 85% on `src/mm`, excluding `__main__.py` (`.coveragerc`).
- mypy strict on `src/` and `scripts/`; tests get the same checks except that annotations are
  optional (`mypy.ini`).
- ruff lint with import sorting (`ruff.toml`).

All three run in the CI `static` job and locally via `make verify`.

## Alternatives considered
- No coverage gate: coverage would drift silently as code lands.
- A higher threshold such as 95% from the start: pushes towards tests written for the number.
- Strict typing on tests as well: adds noise for little safety.

## Consequences
A drop in coverage or a type error fails CI. 85% is a starting point and can be raised once the
core modules exist.
