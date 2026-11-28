"""Build an agent from its name in the config: `[agent] type = "naive"`."""

from collections.abc import Callable

from mm.agent.interface import Agent
from mm.agent.naive import NaiveMarketMaker
from mm.agent.skew import InventorySkewMarketMaker
from mm.config import AgentConfig, ConfigError

_FACTORIES: dict[str, Callable[[AgentConfig], Agent]] = {
    "naive": lambda config: NaiveMarketMaker(config.naive),
    "skew": lambda config: InventorySkewMarketMaker(config.skew),
}
AGENT_NAMES: tuple[str, ...] = tuple(_FACTORIES)


def make_agent(config: AgentConfig) -> Agent:
    """Return a fresh agent of type `config.type`, built from its own config section."""
    factory = _FACTORIES.get(config.type)
    if factory is None:
        raise ConfigError(f"unknown agent type {config.type!r}; known: {', '.join(AGENT_NAMES)}")
    return factory(config)
