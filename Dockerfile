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

COPY src/ src/
COPY tests/ tests/

CMD ["python", "-m", "mm"]
