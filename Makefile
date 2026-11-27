IMAGE := mm-agent
PYTHON ?= python3

.PHONY: build run test venv test-local clean

build:
	docker build -t $(IMAGE) .

run: build
	docker run --rm $(IMAGE)

test: build
	docker run --rm $(IMAGE) python -m pytest -q

venv:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -r requirements.txt

test-local:
	PYTHONPATH=src .venv/bin/python -m pytest -q

clean:
	rm -rf .venv .pytest_cache .hypothesis
