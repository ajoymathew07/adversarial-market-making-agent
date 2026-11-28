"""Realism stress scenarios on the held-out seeds; writes docs/results/stress-realistic/heldout.md.

Run with `make stress-realistic`. Each table is one scenario with v1 (skew) as the baseline and
v2 (kalman) marked against it. Both agents use `config/default.toml` as is: their parameters were
set on base dev seeds and are not tuned on these scenarios (see docs/decisions/08).
"""

from pathlib import Path

from mm.config import load_config
from mm.eval.report import SIDE_BY_SIDE_NOTE, format_markdown, side_by_side_table
from mm.eval.runner import evaluate

SCENARIOS = ("base", "bursty_takers", "heavy_tail_sizes", "fat_tail_value", "realistic_mix")
OUT = Path("docs/results/stress-realistic")
V1, V2 = "v1 (skew)", "v2 (kalman)"
INTERPRETATION_HEADING = "## Interpretation"


def main() -> None:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    intro = (
        "Agents were calibrated on base dev seeds and not tuned on these scenarios. "
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {n_steps} steps, informed share "
        f"{config.market.informed.share:g} in every scenario. Money in price units, fair-value "
        "error in ticks."
    )
    v1 = evaluate(SCENARIOS, seeds, n_steps, agent="skew")
    v2 = evaluate(SCENARIOS, seeds, n_steps, agent="kalman")
    sections = ["# Stress: realism scenarios, held-out seeds", intro, SIDE_BY_SIDE_NOTE]
    for skew_result, kalman_result in zip(v1, v2, strict=True):
        table = side_by_side_table((V1, skew_result), (V2, kalman_result))
        sections += [f"## {skew_result.scenario}", format_markdown(table)]
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "heldout.md"
    path.write_text("\n\n".join(sections) + "\n" + _kept_interpretation(path), encoding="utf-8")
    print(f"Wrote {path}")


def _kept_interpretation(path: Path) -> str:
    """The hand-written section from INTERPRETATION_HEADING on, kept across reruns."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    at = text.find(INTERPRETATION_HEADING)
    return "\n" + text[at:] if at >= 0 else f"\n{INTERPRETATION_HEADING}\n\nTBD\n"


if __name__ == "__main__":
    main()
