"""Run the agent over scenarios x seeds and collect per-episode metrics."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from mm.config import SimConfig, load_config
from mm.eval.metrics import EpisodeMetrics, episode_metrics
from mm.simulation import EpisodeResult, run_episode


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    seeds: tuple[int, ...]
    metrics: list[EpisodeMetrics]  # one per seed, in seed order
    example: EpisodeResult  # the first seed's full episode, for plots
    config: SimConfig  # the scenario's config; seed is that of the example


def evaluate(
    scenarios: Sequence[str],
    seeds: Sequence[int],
    n_steps: int,
    config_path: Path | None = None,
) -> list[ScenarioResult]:
    """Run every scenario of the config file on every seed, with n_steps per episode."""
    if not seeds:
        raise ValueError("at least one seed is required")
    results = []
    for name in scenarios:
        base = replace(load_config(config_path, scenario=name), n_steps=n_steps)
        configs = [replace(base, seed=seed) for seed in seeds]
        episodes = [run_episode(config) for config in configs]
        metrics = [
            episode_metrics(
                episode,
                tick_size=config.instrument.tick_size,
                fee_per_lot=config.engine.fee_per_lot,
                position_limit=config.risk.position_limit,
                horizons=config.evaluation.markout_horizons,
            )
            for episode, config in zip(episodes, configs, strict=True)
        ]
        results.append(ScenarioResult(name, tuple(seeds), metrics, episodes[0], configs[0]))
    return results
