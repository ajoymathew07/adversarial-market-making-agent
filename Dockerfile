FROM python:3.13.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .
# --no-deps: every package, transitive ones included, is pinned in requirements.txt,
# so the install fails loudly instead of silently pulling an unpinned version.
RUN pip install --no-deps -r requirements.txt

COPY config/ config/
COPY src/ src/
COPY tests/ tests/

# make run: v1, v2, v2-tuned and v5 (the final agent) on held-out seeds in every scenario,
# v1 as the baseline.
CMD ["python", "-m", "mm", "--agents", "skew,kalman,kalman_tuned,final"]
