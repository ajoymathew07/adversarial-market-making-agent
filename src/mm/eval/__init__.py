"""Evaluation: per-episode metrics, cross-seed statistics, reports and plots."""

from mm.eval.metrics import EpisodeMetrics, episode_metrics
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import Estimate, bootstrap_ci

__all__ = [
    "EpisodeMetrics",
    "Estimate",
    "ScenarioResult",
    "bootstrap_ci",
    "episode_metrics",
    "evaluate",
]
