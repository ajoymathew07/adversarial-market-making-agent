# 0002: Exact pins with `pip install --no-deps`

**Status:** Accepted (2026-11-27)

## Context
The brief requires all dependencies to be pinned exactly. Pinning only direct dependencies still
lets pip pick any version of their transitive dependencies.

## Decision
`requirements.txt` (runtime and tests, used in Docker) and `requirements-dev.txt` (dev tools
only) list every package, transitive ones included, as `name==version`. Docker and CI install them
with `pip install --no-deps`, so a missing pin fails the build loudly instead of pulling an
unpinned version. `scripts/ci_checks.py pins` enforces the format.

## Alternatives considered
- Version ranges: not reproducible, and against the brief.
- Lockfile tools (uv, poetry, pip-tools): good, but rejected to keep tooling minimal and the
  setup easy to explain.

## Consequences
Builds are reproducible. Adding a library means re-freezing in a fresh venv and copying the new
lines by hand.
