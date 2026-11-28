# 00: Project setup decisions

Small setup choices, grouped in one table. Major design decisions get their own file in this folder.

| # | Decision | Why | Rejected |
|---|----------|-----|----------|
| 1 | Every dependency pinned exactly; Docker installs with `--no-deps` | A missing pin fails the build instead of pulling a random version | Version ranges, uv/poetry lockfiles (extra tooling) |
| 2 | CI static job runs in `python:3.13.9-slim` | Same Python as the Dockerfile; setup-python has no 3.13.9 for ubuntu-latest | Loosening to 3.13 |
| 3 | Quality gates: 85% coverage on `src/mm`, mypy strict on `src/`, ruff | Evidence for the "tested" and "rigor" criteria | No gates |
| 4 | Architecture: separate engine/market/agent/risk/eval modules, one order gate, per-step invariant monitor, all parameters in one config | One place to prove correctness; constraints can be changed live via config | Checks spread across modules; invariants only in tests |
| 5 | Prices as integer ticks (`tick_size` in config, display per 100 face value); sizes as integer lots | Exact matching, no float-equality bugs; matches how exchange engines store prices; any tick grid (decimal, 1/32) is just a `tick_size` | Float, Decimal (slower, no benefit on a tick grid), yield-based quoting (needs price-yield conversion; not asked for) |
| 6 | All parameters in one commented TOML file (`config/default.toml`), loaded with stdlib `tomllib` into typed dataclasses with no defaults; strict loader; scenarios as overrides | One place to see and change every value, typo-safe, no new dependency | YAML (extra dependency), defaults scattered in per-module dataclasses |
| 7 | Shared `Side` enum in `mm/types.py` (BUY/SELL with `.sign`, `.opposite`) used everywhere | Industry convention (FIX `Side`, NautilusTrader `OrderSide`); removes `is_buy` branches | `is_buy: bool`, BuyOrder/SellOrder subclasses, naming it OrderType (means LIMIT/MARKET in trading) |
| 8 | Agent chosen by name: `[agent] type = "naive"` with one sub-table per agent (`[agent.naive]`); `make_agent` in `mm/agent/registry.py` maps the name to the class and lists valid names on a typo | Switching or comparing agents is a config or CLI change, not a code change; each agent keeps only its own parameters | Import paths in the config (fragile), one flat `[agent]` table shared by all agents |
| 9 | Incremental invariant checks (independent running ledger updated from new fills only) | O(n²) → O(n) per episode, measured in docs/results/perf-incremental-monitor.md, results unchanged | Recomputing from all fills every step; dropping the checks |
| 10 | Agents report their fair-value estimate in `Quote.fair_value` (logged only, never used by the gate or engine); evaluation measures its RMSE and bias against the true value, in ticks | Lets us test fair-value hypotheses directly | Inferring it from the quote mid (which includes the skew) |
