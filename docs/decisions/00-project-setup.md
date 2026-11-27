# 00: Project setup decisions

Small setup choices, grouped in one table. Major design decisions get their own file in this folder.

| # | Decision | Why | Rejected |
|---|----------|-----|----------|
| 1 | Every dependency pinned exactly; Docker installs with `--no-deps` | A missing pin fails the build instead of pulling a random version | Version ranges, uv/poetry lockfiles (extra tooling) |
| 2 | CI static job runs in `python:3.13.9-slim` | Same Python as the Dockerfile; setup-python has no 3.13.9 for ubuntu-latest | Loosening to 3.13 |
| 3 | Quality gates: 85% coverage on `src/mm`, mypy strict on `src/`, ruff | Evidence for the "tested" and "rigor" criteria | No gates |
| 4 | Architecture: separate engine/market/agent/risk/eval modules, one order gate, per-step invariant monitor, all parameters in one config | One place to prove correctness; constraints can be changed live via config | Checks spread across modules; invariants only in tests |
