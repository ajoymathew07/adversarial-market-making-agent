# Performance: incremental invariant checks

Apple M5 (arm64), macOS, local venv Python 3.14.3 (no 3.13 on the host; Docker 3.13.9 gives the
same held-out digest). `make bench`: `run_episode`, base scenario, median of 3 runs.
Before = `0ecf663`, after = this branch.

| n_steps | before (s) | after (s) | speed-up | steps/s before | steps/s after |
|--------:|-----------:|----------:|---------:|---------------:|--------------:|
| 500     | 0.021      | 0.005     | 4x       | 23,931         | 94,498        |
| 2000    | 0.129      | 0.020     | 6x       | 15,488         | 102,073       |
| 8000    | 0.768      | 0.073     | 11x      | 10,411         | 109,276       |
| 32000   | 11.954     | 0.286     | 42x      | 2,677          | 111,729       |

Held-out evaluation (`python -m mm`, wall clock incl. startup and plots, median of 3):
12.89 s before, 2.39 s after (5.4x).

Growth: before, each 4x in n_steps cost 6.0-15.6x more time (steps/s fell from 23,931 to 2,677);
after, each 4x cost 3.7-4.0x (steps/s stayed between 94,000 and 112,000).

Byte-identity: held-out `episodes.csv` sha256 `a74bd0cae61179bca4e38c8965cf95842c32d4cce90a8a1b3889b22e85639670` before and after (local and
Docker); `make determinism` passes.
