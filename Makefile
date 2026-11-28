IMAGE := mm-agent
PYTHON ?= python3

.PHONY: build run determinism calibrate sweep v2-experiments sweep-toxicity v3-experiments sweep-adaptive v4-experiments tune v5-experiments stress-tolerance stress-realistic competition realism-data realism test venv test-local lint typecheck coverage checks verify bench clean

build:
	docker build -t $(IMAGE) .

# v1, v2, v2-tuned and v5 on held-out seeds, every scenario (agent list: the Dockerfile CMD).
# Results (report.md, episodes.csv, plots/) land in ./results on the host.
run: build
	mkdir -p results
	docker run --rm -v "$(CURDIR)/results:/app/results" $(IMAGE)

# Run a short evaluation twice in the container; fail if the episodes.csv digests differ.
DETERMINISM_ARGS := --seeds dev --scenarios base --steps 300 --out /tmp/determinism --digest
determinism: build
	@first=$$(docker run --rm $(IMAGE) python -m mm $(DETERMINISM_ARGS) | grep sha256); \
	second=$$(docker run --rm $(IMAGE) python -m mm $(DETERMINISM_ARGS) | grep sha256); \
	echo "run 1: $$first"; \
	echo "run 2: $$second"; \
	if [ -z "$$first" ] || [ "$$first" != "$$second" ]; then \
		echo "determinism check failed"; exit 1; \
	fi; \
	echo "determinism check passed"

# Estimate [agent.kalman] from the calibration agent's own observations on base dev seeds.
calibrate:
	PYTHONPATH=src .venv/bin/python scripts/calibrate.py

# skew_per_lot sweep for the skew agent on dev seeds only; writes docs/results/v1-skew/.
sweep:
	PYTHONPATH=src .venv/bin/python scripts/sweep_skew.py

# v2 (kalman) vs v1, gain sensitivity and robustness on dev seeds only; writes docs/results/v2-kalman/dev.md.
v2-experiments:
	PYTHONPATH=src .venv/bin/python scripts/v2_experiments.py

# v3 (toxicity) tau x c grid on dev seeds, training scenarios only; writes docs/results/v3-toxicity/dev-sweep.md.
sweep-toxicity:
	PYTHONPATH=src .venv/bin/python scripts/sweep_toxicity.py

# v1 | v2 | v3 on every scenario, held-out seeds, run once after the sweep;
# writes docs/results/v3-toxicity/heldout.md.
v3-experiments:
	PYTHONPATH=src .venv/bin/python scripts/v3_experiments.py

# v4 (adaptive) base x a x intensity_halflife grid on dev seeds, training scenarios only, plus the
# detection check; writes docs/results/v4-adaptive/dev-sweep.md.
sweep-adaptive:
	PYTHONPATH=src .venv/bin/python scripts/sweep_adaptive.py

# v1 | v2 | v2-tuned | v4 on every scenario, held-out seeds, run once after the sweep;
# writes docs/results/v4-adaptive/heldout.md.
v4-experiments:
	PYTHONPATH=src .venv/bin/python scripts/v4_experiments.py

# v5 (final) seeded random search over every knob on dev seeds, training scenarios only;
# writes docs/results/v5-final/dev-search.md.
tune:
	PYTHONPATH=src .venv/bin/python scripts/tune_final.py

# v1 | v2 | v2-tuned | v4 | v5 on every scenario, held-out seeds, run once after make tune;
# writes docs/results/v5-final/heldout.md and docs/results/summary.md.
v5-experiments:
	PYTHONPATH=src .venv/bin/python scripts/v5_experiments.py

# naive, skew and kalman under different noise-taker tolerance shapes, dev seeds only;
# writes docs/results/stress-tolerance/dev.md.
stress-tolerance:
	PYTHONPATH=src .venv/bin/python scripts/stress_tolerance.py

# skew vs kalman on base and the realism stress scenarios, held-out seeds;
# writes docs/results/stress-realistic/heldout.md.
stress-realistic:
	PYTHONPATH=src .venv/bin/python scripts/stress_realistic.py

# skew, kalman, kalman_tuned and final against a competing maker (vs_v1, vs_tuned, vs_final),
# held-out seeds;
# writes docs/results/competition/heldout.md.
competition:
	PYTHONPATH=src .venv/bin/python scripts/competition.py

# One day of Binance BTCUSDT aggTrades for the realism check, verified against Binance's checksum.
REALISM_URL := https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2026-11-25.zip
realism-data:
	mkdir -p data/binance
	cd data/binance && curl -fsSLO $(REALISM_URL) && curl -fsSLO $(REALISM_URL).CHECKSUM \
		&& shasum -a 256 -c BTCUSDT-aggTrades-2026-11-25.zip.CHECKSUM

# Simulator taker flow vs BTCUSDT trades (not a backtest); writes docs/results/realism/.
realism:
	PYTHONPATH=src .venv/bin/python scripts/realism_check.py --data data/binance/BTCUSDT-aggTrades-2026-11-25.zip

test: build
	docker run --rm $(IMAGE) python -m pytest -q

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

test-local:
	PYTHONPATH=src .venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .

typecheck:
	.venv/bin/mypy

coverage:
	PYTHONPATH=src .venv/bin/python -m pytest -q --cov --cov-report=term-missing

checks:
	python3 scripts/ci_checks.py all

# Local one-shot of everything the static CI job runs.
verify: checks lint typecheck coverage

# Median run_episode time on the base scenario for growing n_steps (local venv).
bench:
	PYTHONPATH=src .venv/bin/python scripts/bench.py

clean:
	rm -rf .venv .pytest_cache .hypothesis
