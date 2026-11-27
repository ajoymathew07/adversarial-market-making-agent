# Decisions

One line per settled choice: what we chose, why, and what we rejected.

| # | Decision | Why | Rejected |
|---|----------|-----|----------|
| 1 | Prices are integer ticks inside the engine | No float-equality bugs when matching orders | Floats, Decimal |
| 2 | Every dependency pinned exactly; Docker installs with `--no-deps` | A missing pin fails the build instead of pulling a random version | Version ranges, uv/poetry lockfiles (extra tooling) |
| 3 | CI static job runs in `python:3.13.9-slim` | Same Python as the Dockerfile; setup-python has no 3.13.9 for ubuntu-latest | Loosening to 3.13 |
| 4 | Quality gates: 85% coverage on `src/mm`, mypy strict on `src/`, ruff | Evidence for the "tested" and "rigor" criteria | No gates |
| 5 | Architecture: separate engine/market/agent/risk/eval modules, one order gate, per-step invariant monitor, all parameters in one config | One place to prove correctness; constraints can be changed live via config | Checks spread across modules; invariants only in tests |
