"""Our agents against a competing maker, held-out seeds; writes docs/results/competition/heldout.md.

Run with `make competition`. One table per scenario (vs_v1, vs_tuned, vs_final), one column per agent of
ours. Every agent and competitor uses `config/default.toml` as is (see docs/decisions/12).
The ## Interpretation section is hand-written and kept across reruns.
"""

import math
from collections.abc import Callable
from pathlib import Path

from mm.config import load_config
from mm.eval.metrics import EpisodeMetrics
from mm.eval.report import format_estimate, format_markdown
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import bootstrap_ci

SCENARIOS = ("vs_v1", "vs_tuned", "vs_final")
AGENTS = (
    ("v1 (skew)", "skew"),
    ("v2 (kalman)", "kalman"),
    ("v2-tuned", "kalman_tuned"),
    ("v5 (final)", "final"),
)
OUT = Path("docs/results/competition")
INTERPRETATION_HEADING = "## Interpretation"

PerSeed = Callable[[ScenarioResult], list[float]]


def ours(column: str) -> PerSeed:
    return lambda result: [m.as_row()[column] for m in result.metrics]


def competitor(column: str) -> PerSeed:
    return lambda result: [m.as_row()[column] for m in result.competitor_metrics]


def volume_share(result: ScenarioResult) -> list[float]:
    """Per seed: % of all lots filled by makers that were ours (NaN when neither filled)."""
    shares = []
    for mine, theirs in zip(result.metrics, result.competitor_metrics, strict=True):
        total = lots(mine) + lots(theirs)
        shares.append(100 * lots(mine) / total if total else math.nan)
    return shares


def lots(metrics: EpisodeMetrics) -> int:
    return metrics.lots["noise"] + metrics.lots["informed"]


ROWS: tuple[tuple[str, PerSeed], ...] = (
    ("Our final PnL", ours("final_pnl")),
    ("Our Sharpe", ours("sharpe")),
    ("Our noise lots filled", ours("lots_noise")),
    ("Our informed lots filled", ours("lots_informed")),
    ("Competitor final PnL", competitor("final_pnl")),
    ("Our % of maker volume", volume_share),
)


def table(results: list[ScenarioResult]) -> list[list[str]]:
    settings = results[0].config.evaluation
    rows = [["Metric (mean [95% CI])", *(label for label, _ in AGENTS)]]
    for label, per_seed in ROWS:
        cells = [
            format_estimate(
                bootstrap_ci(per_seed(r), settings.bootstrap_resamples, settings.bootstrap_seed)
            )
            for r in results
        ]
        rows.append([label, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {n_steps} steps, informed share "
        f"{config.market.informed.share:g}. Each column is one agent of ours against the "
        "scenario's competitor; both use their frozen config. Money in price units; lots per "
        "episode. Mean [95% CI] over seeds."
    )
    sections = ["# Competing makers, held-out seeds", intro]
    runs = {name: evaluate(SCENARIOS, seeds, n_steps, agent=name) for _, name in AGENTS}
    for i, scenario in enumerate(SCENARIOS):
        competitor_name = load_config(scenario=scenario).market.competitor
        results = [runs[name][i] for _, name in AGENTS]
        sections += [
            f"## {scenario} (competitor: {competitor_name})",
            format_markdown(table(results)),
        ]
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
