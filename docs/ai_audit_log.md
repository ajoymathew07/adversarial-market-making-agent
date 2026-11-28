# AI Assistance Audit Log

Running record for section 8 of SUBMISSION.md. Add an entry whenever an AI tool produced
flawed logic, a wrong assumption, or a subtle bug.

**Tools used:** Claude Code (Claude Opus 5.5)

## Entries

<!--
### YYYY-MM-DD: short title
- **What the AI produced:**
- **What was wrong:**
- **How it was caught:**
- **Fix:**
-->

### 2026-11-27: CI pinned a Python version the runner can't install
- **What the AI produced:** the `static` CI job used `actions/setup-python` with `python-version: "3.13.9"` on `ubuntu-latest`.
- **What was wrong:** setup-python has no 3.13.9 build for the current `ubuntu-latest` image (Ubuntu 26.04), so the job failed before running any check. Local testing couldn't catch it because it only happens on GitHub's runner.
- **How it was caught:** the first GitHub Actions run on PR #2 failed with "version '3.13.9' ... was not found for Ubuntu 26.04".
- **Fix:** the job now runs inside the `python:3.13.9-slim` container, the same base image as the Dockerfile, so the exact version is guaranteed and matches the submission.

### 2026-11-28: Pushed a branch with failing tests after changing a config value
- **What the AI produced:** after setting the chosen γ = 0.005 in `config/default.toml`, the assistant ran the tests and the push in one shell command where the push didn't depend on the tests passing.
- **What was wrong:** two tests still asserted the old placeholder γ = 0.01 (one read the default config instead of fixing its own value), so they failed, and the branch was pushed anyway.
- **How it was caught:** the test output printed above the push result; no PR had been opened yet.
- **Fix:** the agent test now sets its own skew explicitly instead of relying on the config default; the config test asserts the chosen value. Pushes are now chained only after a passing test run.

### 2026-11-28: The agent's model was given the market's true parameters
- **What the AI produced:** the v2 design (written by the assistant) set `[agent.kalman]` (σ, arrival rate, sizes, fill sensitivity) and v1's σ to exactly the values in `[market]`, describing them as "the agent's own assumptions".
- **What was wrong:** a real market maker cannot know how takers behave. Copying the simulator's parameters (and its exact fill formula) made v2 right by construction and overstated its results. v1's σ and τ were copied too, although only their tuned product mattered.
- **How it was caught:** the author asked how a market maker would know R and H in practice.
- **Fix:** a standing rule in CLAUDE.md (no market knowledge in agents); every taker parameter is now estimated from the agent's own fills on training seeds (`make calibrate`), with an estimated-vs-true table as a simulation-only check; v1's skew is a single tuned parameter; the exponential fill shape is tested separately with non-exponential taker scenarios.

### 2026-11-28: Kalman filter froze at the position limit
- **What the AI produced:** the v2 filter capped each side's fill probability at 1 (`min(1, e^(−k·distance))`) and gave a capped side zero slope.
- **What was wrong:** at the +50 limit the gate removes the bid and the skewed ask sits below fair value, so the only quote is capped: H = 0, the gain is 0, fair value freezes and the agent stays stuck at the limit (about 60% of the episode on a few seeds). The leaked "oracle" parameters happened to hide it; calibrated parameters exposed it.
- **How it was caught:** calibration results showed a heavy fair-value-error tail on a handful of seeds; tracing one (held-out 1021) showed fv frozen at the limit.
- **Fix:** treat e^(−k·distance) as an arrival intensity (the standard Avellaneda–Stoikov form), not a capped probability, so H > 0 whenever a side rests. A regression test forces the agent to the limit and asserts fair value keeps updating and the agent leaves the limit.
