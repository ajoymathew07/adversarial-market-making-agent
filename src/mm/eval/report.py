"""Console summary, results/report.md and results/episodes.csv."""

import csv
import hashlib
import math
from pathlib import Path

from mm.eval.metrics import KINDS
from mm.eval.runner import ScenarioResult
from mm.eval.stats import Estimate, bootstrap_ci

# (column in EpisodeMetrics.as_row(), label) for the summary table.
SUMMARY_METRICS: tuple[tuple[str, str], ...] = (
    ("final_pnl", "Final PnL"),
    ("spread_capture", "Spread capture"),
    ("inventory_pnl", "Inventory PnL"),
    ("max_drawdown", "Max drawdown"),
    ("sharpe", "Sharpe"),
    ("markout_informed_10", "Informed markout/lot, t=10"),
    ("markout_noise_10", "Noise markout/lot, t=10"),
    ("mean_abs_position", "Mean |q|"),
    ("pct_time_at_limit", "% time at limit"),
)
MARKOUT_DECIMALS = 4


def estimate(result: ScenarioResult, column: str) -> Estimate:
    settings = result.config.evaluation
    values = [m.as_row()[column] for m in result.metrics]
    return bootstrap_ci(values, settings.bootstrap_resamples, settings.bootstrap_seed)


def format_estimate(est: Estimate, decimals: int = 2) -> str:
    if math.isnan(est.mean):
        return "n/a"
    return f"{est.mean:.{decimals}f} [{est.low:.{decimals}f}, {est.high:.{decimals}f}]"


def decimals_for(column: str) -> int:
    # Per-lot markouts are fractions of a tick, so they need more digits than PnL.
    return MARKOUT_DECIMALS if column.startswith("markout_") else 2


def summary_table(results: list[ScenarioResult]) -> list[list[str]]:
    """Header row plus one row per summary metric; one column per scenario."""
    rows = [["Metric (mean [95% CI])", *(r.scenario for r in results)]]
    for column, label in SUMMARY_METRICS:
        cells = [format_estimate(estimate(r, column), decimals_for(column)) for r in results]
        rows.append([label, *cells])
    return rows


def markout_table(results: list[ScenarioResult]) -> list[list[str]]:
    rows = [["Kind", "Horizon", *(r.scenario for r in results)]]
    for kind in KINDS:
        for horizon in results[0].config.evaluation.markout_horizons:
            column = f"markout_{kind}_{horizon}"
            cells = [format_estimate(estimate(r, column), MARKOUT_DECIMALS) for r in results]
            rows.append([kind, str(horizon), *cells])
    return rows


def format_console(rows: list[list[str]]) -> str:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(row, widths, strict=True)) for row in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def format_markdown(rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(cell.replace("|", "\\|") for cell in row) + " |" for row in rows]
    lines.insert(1, "|" + "---|" * len(rows[0]))
    return "\n".join(lines)


def header(results: list[ScenarioResult], n_steps: int) -> str:
    seeds = results[0].seeds
    return f"{len(seeds)} seeds ({seeds[0]}..{seeds[-1]}), {n_steps} steps per episode"


def write_report(results: list[ScenarioResult], n_steps: int, path: Path) -> None:
    text = "\n\n".join(
        [
            "# Evaluation report",
            header(results, n_steps) + ". Money in price units; markouts per lot.",
            "## Summary",
            format_markdown(summary_table(results)),
            "## Markouts by counterparty kind and horizon",
            format_markdown(markout_table(results)),
        ]
    )
    path.write_text(text + "\n")


def write_episodes_csv(results: list[ScenarioResult], path: Path) -> None:
    """One row per scenario x seed with every scalar metric."""
    columns = list(results[0].metrics[0].as_row())
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scenario", "seed", *columns])
        for result in results:
            for seed, metrics in zip(result.seeds, result.metrics, strict=True):
                row = metrics.as_row()
                writer.writerow([result.scenario, seed, *(repr(row[c]) for c in columns)])


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
