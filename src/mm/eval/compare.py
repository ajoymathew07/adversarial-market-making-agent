"""Paired comparison of two agents run on the same scenario and seeds.

Every agent sees the same market for a given seed, so the per-seed difference (agent - baseline)
removes the market's randomness; its bootstrap CI is much tighter than comparing two averages.
"""

from mm.eval.runner import ScenarioResult
from mm.eval.stats import Estimate, bootstrap_ci

# (column in EpisodeMetrics.as_row(), label) compared between agents.
COMPARE_METRICS: tuple[tuple[str, str], ...] = (
    ("final_pnl", "Final PnL"),
    ("spread_capture", "Spread capture"),
    ("inventory_pnl", "Inventory PnL"),
    ("max_drawdown", "Max drawdown"),
    ("sharpe", "Sharpe"),
    ("mean_abs_position", "Mean |q|"),
    ("pct_time_at_limit", "% time at limit"),
    ("markout_informed_10", "Informed markout/lot, t=10"),
)


def paired_differences(agent: ScenarioResult, baseline: ScenarioResult, column: str) -> list[float]:
    """Per-seed agent - baseline for one metric. NaN where either side is NaN (no fills)."""
    if (agent.scenario, agent.seeds) != (baseline.scenario, baseline.seeds):
        raise ValueError("paired comparison needs the same scenario and seeds for both agents")
    return [
        a.as_row()[column] - b.as_row()[column]
        for a, b in zip(agent.metrics, baseline.metrics, strict=True)
    ]


def paired_estimate(agent: ScenarioResult, baseline: ScenarioResult, column: str) -> Estimate:
    """Mean per-seed difference with a percentile-bootstrap 95% CI."""
    settings = baseline.config.evaluation
    differences = paired_differences(agent, baseline, column)
    return bootstrap_ci(differences, settings.bootstrap_resamples, settings.bootstrap_seed)


def is_significant(est: Estimate) -> bool:
    """True when the CI excludes 0. A NaN estimate is never significant."""
    return est.low > 0 or est.high < 0


def pairs(runs: list[list[ScenarioResult]]) -> list[tuple[ScenarioResult, ScenarioResult]]:
    """(agent, baseline) per scenario for every run after the first; the first is the baseline."""
    baseline = runs[0]
    return [(a, b) for run in runs[1:] for a, b in zip(run, baseline, strict=True)]
