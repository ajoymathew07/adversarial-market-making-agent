"""Console summary, results/report.md and results/episodes.csv."""

import csv
import hashlib
import math
from collections.abc import Sequence
from pathlib import Path

from mm.eval.compare import COMPARE_METRICS, is_significant, paired_estimate, pairs
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
    ("fair_value_rmse", "Fair-value RMSE (ticks)"),
    ("fair_value_bias", "Fair-value bias (ticks)"),
)
MARKOUT_DECIMALS = 4
PAIRED_NOTE = (
    "Per-seed differences (agent − baseline) on identical markets; "
    "significant when the 95% CI excludes 0."
)
SIGNIFICANT = "✔"
SIDE_BY_SIDE_NOTE = (
    f"Mean [95% CI] over seeds. {SIGNIFICANT} on the agent's value: the per-seed difference "
    "from the baseline on identical markets has a 95% CI that excludes 0."
)


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


def comparison_title(agent: ScenarioResult, baseline: ScenarioResult) -> str:
    return f"{agent.agent} − {baseline.agent}: {agent.scenario}"


def comparison_table(agent: ScenarioResult, baseline: ScenarioResult) -> list[list[str]]:
    """One row per compared metric: mean per-seed difference [95% CI] and significance."""
    rows = [["Metric", "Mean difference [95% CI]", "Significant"]]
    for column, label in COMPARE_METRICS:
        est = paired_estimate(agent, baseline, column)
        significant = "n/a" if math.isnan(est.mean) else ("yes" if is_significant(est) else "no")
        rows.append([label, format_estimate(est, decimals_for(column)), significant])
    return rows


def side_by_side_table(
    baseline: tuple[str, ScenarioResult],
    agent: tuple[str, ScenarioResult],
    references: Sequence[tuple[str, ScenarioResult]] = (),
) -> list[list[str]]:
    """One row per summary metric; columns baseline | agent | references, each labelled.

    The agent's value is marked when its paired difference from the baseline is significant.
    Reference columns are shown as they are, unmarked.
    """
    columns = [baseline, agent, *references]
    rows = [["Metric (mean [95% CI])", *(label for label, _ in columns)]]
    for column, label in SUMMARY_METRICS:
        decimals = decimals_for(column)
        cells = [format_estimate(estimate(result, column), decimals) for _, result in columns]
        if is_significant(paired_estimate(agent[1], baseline[1], column)):
            cells[1] += f" {SIGNIFICANT}"
        rows.append([label, *cells])
    return rows


def write_report(runs: list[list[ScenarioResult]], n_steps: int, path: Path) -> None:
    """Summary and markout sections per agent, then a side-by-side section per pair."""
    sections = [
        "# Evaluation report",
        header(runs[0], n_steps)
        + ". Money in price units; markouts per lot; fair-value error in ticks.",
    ]
    for results in runs:
        agent = results[0].agent
        sections += [
            f"## Summary: {agent}",
            format_markdown(summary_table(results)),
            f"## Markouts by counterparty kind and horizon: {agent}",
            format_markdown(markout_table(results)),
        ]
    for agent_result, baseline in pairs(runs):
        table = side_by_side_table(
            (baseline.agent, baseline), (agent_result.agent, agent_result)
        )
        sections += [
            f"## {baseline.agent} vs {agent_result.agent}: {agent_result.scenario}",
            SIDE_BY_SIDE_NOTE,
            format_markdown(table),
        ]
    path.write_text("\n\n".join(sections) + "\n", encoding="utf-8")


def write_episodes_csv(results: list[ScenarioResult], path: Path) -> None:
    """One row per agent x scenario x seed with every scalar metric."""
    columns = list(results[0].metrics[0].as_row())
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["agent", "scenario", "seed", *columns])
        for result in results:
            for seed, metrics in zip(result.seeds, result.metrics, strict=True):
                row = metrics.as_row()
                cells = (repr(row[c]) for c in columns)
                writer.writerow([result.agent, result.scenario, seed, *cells])


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
