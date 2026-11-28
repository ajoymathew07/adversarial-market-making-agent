IMAGE := mm-agent
PYTHON ?= python3

.PHONY: build run determinism test venv test-local lint typecheck coverage checks verify clean

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

clean:
	rm -rf .venv .pytest_cache .hypothesis
