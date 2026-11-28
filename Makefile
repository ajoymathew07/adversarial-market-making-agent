IMAGE := mm-agent
PYTHON ?= python3

.PHONY: build run determinism sweep test venv test-local lint typecheck coverage checks verify bench clean

build:
	docker build -t $(IMAGE) .

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

# Gamma sweep for the skew agent on dev seeds only; writes docs/results/v1-skew/.
sweep:
	PYTHONPATH=src .venv/bin/python scripts/sweep_skew.py

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
