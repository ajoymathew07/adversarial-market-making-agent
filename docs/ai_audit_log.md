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
