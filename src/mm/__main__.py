"""Entry point for `python -m mm`: one episode of the base scenario with the v0 agent."""

from collections import Counter

from mm.config import load_config
from mm.simulation import EpisodeResult, run_episode


def summarise(result: EpisodeResult, tick_size: float) -> str:
    fills_by_kind = Counter(fill.taker_kind for fill in result.fills)
    max_abs_position = max((abs(step.position) for step in result.steps), default=0)
    lines = [
        "Scenario base, seed 0, v0 naive agent",
        f"Final PnL: {result.final_pnl * tick_size:.2f}",
        f"Fills: noise {fills_by_kind['noise']}, informed {fills_by_kind['informed']}",
        f"Final position: {result.final_position}",
        f"Max |position|: {max_abs_position}",
        f"Gate events: {len(result.gate_events)}",
    ]
    return "\n".join(lines)


def main() -> None:
    config = load_config(scenario="base")
    result = run_episode(config)
    print(summarise(result, config.instrument.tick_size))


if __name__ == "__main__":
    main()
