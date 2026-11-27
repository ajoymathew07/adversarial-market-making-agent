# 0003: CI static job runs in the pinned Python container

**Status:** Accepted (2026-11-27)

## Context
The first CI run used `actions/setup-python` with Python 3.13.9 and failed: there is no 3.13.9
build for the current `ubuntu-latest` runner (see `docs/ai_audit_log.md`).

## Decision
The `static` job runs inside `python:3.13.9-slim`, the same base image as the Dockerfile.

## Alternatives considered
- Loosen the version to `3.13`: rejected, since checks would then run on a different patch
  release from the one the submission ships with.

## Consequences
CI checks run on exactly the Python the submission uses, giving parity with Docker. The slim image
has few system tools, so any step needing extra packages must install them.
