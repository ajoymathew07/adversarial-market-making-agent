"""Taker tolerance-shape stress test on the development seeds; writes
docs/results/stress-tolerance/dev.md.

Run with `make stress-tolerance`. Held-out seeds are never touched here. Each table is one
scenario with v1 (skew) as the baseline, v2 (kalman) marked against it, and naive for reference.
Every agent uses `config/default.toml` as is: [agent.kalman] was calibrated on exponential-taker
base dev seeds and is not re-estimated per scenario, since the agent does not know the scenario.
"""

from pathlib import Path

from mm.config import load_config
from mm.eval.report import SIDE_BY_SIDE_NOTE, format_markdown, side_by_side_table
from mm.eval.runner import evaluate

SCENARIOS = ("base", "uniform_takers", "heavy_tail_takers")
N_STEPS = 2000
OUT = Path("docs/results/stress-tolerance")
V1, V2, NAIVE = "v1 (skew)", "v2 (kalman, calibrated)", "naive (reference)"


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {N_STEPS} steps, informed share "
        f"{config.market.informed.share:g} in every scenario. Money in price units, fair-value "
        "error in ticks. v2 uses the `[agent.kalman]` calibrated on exponential-taker base dev "
        "seeds, unchanged in every scenario."
    )
    v1 = evaluate(SCENARIOS, seeds, N_STEPS, agent="skew")
    v2 = evaluate(SCENARIOS, seeds, N_STEPS, agent="kalman")
    naive = evaluate(SCENARIOS, seeds, N_STEPS, agent="naive")
    sections = [
        "# Stress: taker tolerance shape, development seeds",
        intro,
        SIDE_BY_SIDE_NOTE + " The naive column is not marked.",
    ]
    for skew_result, kalman_result, naive_result in zip(v1, v2, naive, strict=True):
        table = side_by_side_table((V1, skew_result), (V2, kalman_result), [(NAIVE, naive_result)])
        sections += [f"## {skew_result.scenario}", format_markdown(table)]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev.md'}")


if __name__ == "__main__":
    main()
