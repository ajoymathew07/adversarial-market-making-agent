IMAGE := mm-agent
PYTHON ?= python3

.PHONY: build run test venv test-local lint checks clean

build:
	docker build -t $(IMAGE) .

run: build
	docker run --rm $(IMAGE)

test: build
	docker run --rm $(IMAGE) python -m pytest -q

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt -r requirements-dev.txt

test-local:
	PYTHONPATH=src .venv/bin/python -m pytest -q

lint:
	.venv/bin/ruff check .

checks:
	python3 scripts/ci_checks.py all

clean:
	rm -rf .venv .pytest_cache .hypothesis
