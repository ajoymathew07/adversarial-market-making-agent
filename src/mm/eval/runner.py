"""Run one agent over scenarios x seeds and collect per-episode metrics."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from mm.agent import Agent
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
    # The competing maker's metrics per seed when the scenario has one (decision 12), else empty.
    competitor_metrics: list[EpisodeMetrics] = field(default_factory=list)


def evaluate(
    scenarios: Sequence[str],
    seeds: Sequence[int],
    n_steps: int,
    config_path: Path | None = None,
    agent: str | None = None,
    agent_config: AgentConfig | None = None,
    agent_factory: Callable[[SimConfig], Agent] | None = None,
) -> list[ScenarioResult]:
    """Run one agent (default: the config's [agent] type) on every scenario and seed.

    `agent_config` replaces the file's [agent] section, e.g. to sweep a parameter.
    `agent_factory`, if given, builds each episode's agent instead of the registry, e.g. to wrap
    it and record its internal state; episodes run in scenario-then-seed order.
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
        episodes = [
            run_episode(config, agent_factory(config) if agent_factory else None)
            for config in configs
        ]
        metrics = [_metrics(e, c) for e, c in zip(episodes, configs, strict=True)]
        competitor_metrics = [
            _metrics(e.competitor, c)
            for e, c in zip(episodes, configs, strict=True)
            if e.competitor is not None
        ]
        results.append(
            ScenarioResult(
                agent_name,
                name,
                tuple(seeds),
                metrics,
                episodes[0],
                configs[0],
                competitor_metrics,
            )
        )
    return results


def _metrics(episode: EpisodeResult, config: SimConfig) -> EpisodeMetrics:
    return episode_metrics(
        episode,
        tick_size=config.instrument.tick_size,
        fee_per_lot=config.engine.fee_per_lot,
        position_limit=config.risk.position_limit,
        horizons=config.evaluation.markout_horizons,
    )
