"""Build an agent from its name in the config: `[agent] type = "naive"`."""

from collections.abc import Callable
from dataclasses import replace

from mm.agent.calibration import CalibrationMarketMaker
from mm.agent.interface import Agent
from mm.agent.kalman import KalmanMarketMaker
from mm.agent.naive import NaiveMarketMaker
from mm.agent.skew import InventorySkewMarketMaker
from mm.agent.toxicity import ToxicityMarketMaker
from mm.config import ConfigError, SimConfig

_FACTORIES: dict[str, Callable[[SimConfig], Agent]] = {
    "naive": lambda config: NaiveMarketMaker(config.agent.naive),
    "skew": lambda config: InventorySkewMarketMaker(config.agent.skew),
    # v2 shares v1's [agent.skew] quoting settings; only its fair value differs.
    "kalman": lambda config: KalmanMarketMaker(config.agent.skew, config.agent.kalman),
    # The control for v3: v2 with its own tuned half-spread instead of [agent.skew]'s.
    "kalman_tuned": lambda config: KalmanMarketMaker(
        replace(config.agent.skew, half_spread=config.agent.kalman_tuned.half_spread),
        config.agent.kalman,
    ),
    # v3 is v2 plus a half-spread that widens on its own fills' markouts.
    "toxicity": lambda config: ToxicityMarketMaker(
        config.agent.skew, config.agent.kalman, config.agent.toxicity
    ),
    # Uses v1's skew, quotes the largest size the gate allows, seeds its RNG from the episode.
    "calibration": lambda config: CalibrationMarketMaker(
        config.agent.calibration,
        config.agent.skew.skew_per_lot,
        config.risk.max_order_size,
        config.seed,
    ),
}
AGENT_NAMES: tuple[str, ...] = tuple(_FACTORIES)


def make_agent(config: SimConfig) -> Agent:
    """Return a fresh agent of type `config.agent.type` for one episode of `config`."""
    factory = _FACTORIES.get(config.agent.type)
    if factory is None:
        raise ConfigError(
            f"unknown agent type {config.agent.type!r}; known: {', '.join(AGENT_NAMES)}"
        )
    return factory(config)
