"""Side-by-side held-out tables shared by the v4, v5 and v6 experiment scripts.

One column per agent, plain values (never differences). A column with a baseline gets ✔ on a
metric when the per-seed difference from that baseline, on identical markets, has a 95% CI
that excludes 0. The same layout as `scripts/v3_experiments.py`.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from mm.eval.compare import is_significant, paired_estimate
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import SIGNIFICANT, SUMMARY_METRICS, decimals_for, estimate, format_estimate
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import Estimate, bootstrap_ci

INTERPRETATION_HEADING = "## Interpretation"
# Per-seed values the recorder (not EpisodeMetrics) provides.
RECORDED = ("half_spread", "intensity", "share", "effective_base")


@dataclass(frozen=True)
class Column:
    label: str  # e.g. "v2-tuned (control)"
    agent: str  # registry name
    baseline: int | None  # index of the column its ✔ is against; None: unmarked


Run = tuple[ScenarioResult, EpisodeRecorder]


def run_column(agent: str, scenario: str, seeds: Sequence[int], n_steps: int) -> Run:
    recorder = EpisodeRecorder()
    (result,) = evaluate([scenario], seeds, n_steps, agent=agent, agent_factory=recorder.factory)
    return result, recorder


def per_seed(run: Run, key: str) -> list[float]:
    """One value per seed: an EpisodeMetrics column, or a recorded mean (empty if none)."""
    result, recorder = run
    if key == "half_spread":
        return recorder.mean_half_spread()
    if key == "intensity":
        return recorder.mean_intensity()
    if key == "share":
        return recorder.mean_share()
    if key == "effective_base":
        return recorder.mean_effective_base()
    return [m.as_row()[key] for m in result.metrics]


def bootstrap(values: list[float], result: ScenarioResult) -> Estimate:
    settings = result.config.evaluation
    return bootstrap_ci(values, settings.bootstrap_resamples, settings.bootstrap_seed)


def baselines_note(columns: Sequence[Column]) -> str:
    """'B against A; C against B', naming each marked column's baseline."""
    return "; ".join(
        f"{c.label} against {columns[c.baseline].label}" for c in columns if c.baseline is not None
    )


def side_by_side(
    runs: Sequence[Run],
    columns: Sequence[Column],
    extra: Sequence[tuple[str, str]] = (),
) -> list[list[str]]:
    """Header plus one row per summary metric and per `extra` (key, label)."""
    rows = [["Metric (mean [95% CI])", *(c.label for c in columns)]]
    for key, label in [*SUMMARY_METRICS, *extra]:
        values = [per_seed(run, key) for run in runs]
        decimals = decimals_for(key) if key not in RECORDED else 2
        cells = []
        for i, (column, run) in enumerate(zip(columns, runs, strict=True)):
            if not values[i]:
                cells.append("—")
                continue
            if key in RECORDED:
                cell = format_estimate(bootstrap(values[i], run[0]), decimals)
            else:
                cell = format_estimate(estimate(run[0], key), decimals)
            b = column.baseline
            if b is not None and values[b]:
                if key in RECORDED:
                    deltas = [x - y for x, y in zip(values[i], values[b], strict=True)]
                    diff = bootstrap(deltas, run[0])
                else:
                    diff = paired_estimate(run[0], runs[b][0], key)
                if is_significant(diff):
                    cell += f" {SIGNIFICANT}"
            cells.append(cell)
        rows.append([label, *cells])
    return rows


def write_with_interpretation(path: Path, body: str) -> None:
    """Write `body`, then the hand-written section from INTERPRETATION_HEADING on.

    The section is kept across reruns; a new file gets the heading followed by TBD.
    """
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    at = text.find(INTERPRETATION_HEADING)
    kept = text[at:] if at >= 0 else f"{INTERPRETATION_HEADING}\n\nTBD\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip("\n") + "\n\n" + kept, encoding="utf-8")
