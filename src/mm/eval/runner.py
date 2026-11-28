"""Run one agent over scenarios x seeds and collect per-episode metrics."""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from mm.config import AgentConfig, SimConfig, load_config
from mm.eval.metrics import EpisodeMetrics, episode_metrics
from mm.simulation import EpisodeResult, run_episode


@dataclass(frozen=True)
class ScenarioResult:
    agent: str
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
    agent: str | None = None,
    agent_config: AgentConfig | None = None,
) -> list[ScenarioResult]:
    """Run one agent (default: the config's [agent] type) on every scenario and seed.

    `agent_config` replaces the file's [agent] section, e.g. to sweep a parameter.
    """
    if not seeds:
        raise ValueError("at least one seed is required")
    results = []
    for name in scenarios:
        base = replace(load_config(config_path, scenario=name), n_steps=n_steps)
        if agent_config is not None:
            base = replace(base, agent=agent_config)
        agent_name = agent or base.agent.type
        base = replace(base, agent=replace(base.agent, type=agent_name))
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
        results.append(
            ScenarioResult(agent_name, name, tuple(seeds), metrics, episodes[0], configs[0])
        )
    return results
