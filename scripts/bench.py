"""Time run_episode on the base scenario for growing n_steps. Run with `make bench`."""

import platform
import statistics
import time
from dataclasses import replace

from mm.config import load_config
from mm.simulation import run_episode

STEP_COUNTS = (500, 2000, 8000, 32000)
REPEATS = 3


def median_seconds(n_steps: int) -> float:
    config = replace(load_config(scenario="base"), n_steps=n_steps)
    timings = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        run_episode(config)
        timings.append(time.perf_counter() - start)
    return statistics.median(timings)


def main() -> None:
    print(f"Python {platform.python_version()} on {platform.machine()}, {REPEATS} repeats")
    print("| n_steps | median s | steps/s |")
    print("|--------:|---------:|--------:|")
    for n_steps in STEP_COUNTS:
        seconds = median_seconds(n_steps)
        print(f"| {n_steps} | {seconds:.3f} | {n_steps / seconds:,.0f} |")


if __name__ == "__main__":
    main()
