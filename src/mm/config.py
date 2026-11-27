"""Typed schema for `config/default.toml` and its strict loader.

Every parameter value lives in the TOML file. The dataclasses here have no defaults: they give
each value a type, check its range and derive the quantities the code uses.
"""

import copy
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mm.engine.units import price_to_ticks

# src/mm/config.py -> repo root (or /app in Docker) -> config/default.toml
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"

# The noise-taker fill probability is calibrated at this distance from the true value.
FILL_PROB_REFERENCE_TICKS = 2.0


class ConfigError(ValueError):
    """The config file has an unknown, missing or wrongly typed key."""


@dataclass(frozen=True)
class InstrumentConfig:
    tick_size: float  # price of one tick, quoted per 100 face value
    initial_price: float  # in price units, not ticks

    def __post_init__(self) -> None:
        if self.tick_size <= 0:
            raise ValueError("tick_size must be > 0")
        if self.initial_price <= 0:
            raise ValueError("initial_price must be > 0")

    @property
    def initial_price_ticks(self) -> int:
        return price_to_ticks(self.initial_price, self.tick_size)


@dataclass(frozen=True)
class EngineConfig:
    fee_per_lot: int  # ticks per filled lot


@dataclass(frozen=True)
class TrueValueConfig:
    sigma: float  # std of each step's move, in ticks

    def __post_init__(self) -> None:
        if self.sigma < 0:
            raise ValueError("sigma must be >= 0")


@dataclass(frozen=True)
class NoiseConfig:
    rate: float  # mean arrivals per step
    size_min: int
    size_max: int
    fill_prob_at_2_ticks: float

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError("noise rate must be >= 0")
        if not 1 <= self.size_min <= self.size_max:
            raise ValueError("noise sizes must satisfy 1 <= min <= max")
        if not 0 < self.fill_prob_at_2_ticks < 1:
            raise ValueError("fill_prob_at_2_ticks must be in (0, 1)")

    @property
    def tolerance_rate(self) -> float:
        """k in P(fill at distance d) = exp(-k * d), from the calibration point."""
        return -math.log(self.fill_prob_at_2_ticks) / FILL_PROB_REFERENCE_TICKS


@dataclass(frozen=True)
class InformedConfig:
    share: float  # expected fraction of all takers
    lookahead: int  # steps ahead they see the true value
    edge_threshold: float  # minimum edge they need, in ticks
    size_min: int
    size_max: int

    def __post_init__(self) -> None:
        if not 0 <= self.share < 1:
            raise ValueError("informed share must be in [0, 1)")
        if self.lookahead < 1:
            raise ValueError("informed lookahead must be >= 1")
        if self.edge_threshold < 0:
            raise ValueError("informed edge_threshold must be >= 0")
        if not 1 <= self.size_min <= self.size_max:
            raise ValueError("informed sizes must satisfy 1 <= min <= max")


@dataclass(frozen=True)
class MarketConfig:
    true_value: TrueValueConfig
    noise: NoiseConfig
    informed: InformedConfig

    @property
    def informed_rate(self) -> float:
        """Mean informed takers per step, so that informed / all takers = informed.share."""
        return self.noise.rate * self.informed.share / (1 - self.informed.share)


@dataclass(frozen=True)
class SimConfig:
    """Everything one episode needs, built from the config file."""

    instrument: InstrumentConfig
    engine: EngineConfig
    market: MarketConfig


def load_config(path: Path | None = None, scenario: str = "base") -> SimConfig:
    """Read the config file (default: `config/default.toml`) with one scenario applied."""
    return build_config(_read(path), scenario)


def scenario_names(path: Path | None = None) -> tuple[str, ...]:
    """The scenarios defined in the config file, in file order."""
    return tuple(_scenarios(_read(path)))


def build_config(raw: dict[str, Any], scenario: str = "base") -> SimConfig:
    """Build the typed config from parsed TOML. Raises ValueError naming any bad key."""
    root = _Table(_apply_scenario(raw, scenario), "")
    config = SimConfig(
        instrument=_instrument(root.get_table("instrument")),
        engine=_engine(root.get_table("engine")),
        market=_market(root.get_table("market")),
    )
    root.reject_unread()
    return config


def _read(path: Path | None) -> dict[str, Any]:
    with (path or DEFAULT_CONFIG_PATH).open("rb") as handle:
        return tomllib.load(handle)


def _apply_scenario(raw: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Return a copy of `raw` without [scenarios], with the scenario's overrides applied.

    Overrides use dotted keys, e.g. {"market.informed.share" = 0.40}.
    """
    raw = copy.deepcopy(raw)
    scenarios = _scenarios(raw)
    del raw["scenarios"]
    if scenario not in scenarios:
        raise ConfigError(f"unknown scenario {scenario!r}; known: {', '.join(scenarios)}")
    overrides = scenarios[scenario]
    if not isinstance(overrides, dict):
        raise ConfigError(f"'scenarios.{scenario}' must be a table")
    for dotted, value in overrides.items():
        *parents, last = dotted.split(".")
        table: Any = raw
        for part in parents:
            table = table.get(part) if isinstance(table, dict) else None
        if not isinstance(table, dict) or last not in table:
            raise ConfigError(f"scenario {scenario!r} overrides unknown key {dotted!r}")
        table[last] = value
    return raw


def _scenarios(raw: dict[str, Any]) -> dict[str, Any]:
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, dict):
        raise ConfigError("missing config table 'scenarios'")
    return scenarios


def _instrument(table: "_Table") -> InstrumentConfig:
    return InstrumentConfig(
        tick_size=table.get_float("tick_size"),
        initial_price=table.get_float("initial_price"),
    )


def _engine(table: "_Table") -> EngineConfig:
    return EngineConfig(fee_per_lot=table.get_int("fee_per_lot"))


def _market(table: "_Table") -> MarketConfig:
    noise = table.get_table("noise")
    noise_min, noise_max = noise.get_int_pair("size")
    informed = table.get_table("informed")
    informed_min, informed_max = informed.get_int_pair("size")
    return MarketConfig(
        true_value=TrueValueConfig(sigma=table.get_table("true_value").get_float("sigma")),
        noise=NoiseConfig(
            rate=noise.get_float("rate"),
            size_min=noise_min,
            size_max=noise_max,
            fill_prob_at_2_ticks=noise.get_float("fill_prob_at_2_ticks"),
        ),
        informed=InformedConfig(
            share=informed.get_float("share"),
            lookahead=informed.get_int("lookahead"),
            edge_threshold=informed.get_float("edge_threshold"),
            size_min=informed_min,
            size_max=informed_max,
        ),
    )


class _Table:
    """One TOML table, read strictly: each key must exist with the expected type.

    Keys that are never read are reported by `reject_unread`, so a typo cannot be ignored.
    """

    def __init__(self, values: dict[str, Any], name: str) -> None:
        self._values = values
        self._name = name
        self._unread = set(values)
        self._children: list[_Table] = []

    def get_table(self, key: str) -> "_Table":
        value = self._get(key)
        if not isinstance(value, dict):
            raise ConfigError(f"{self._full(key)!r} must be a table")
        child = _Table(value, self._full(key))
        self._children.append(child)
        return child

    def get_int(self, key: str) -> int:
        value = self._get(key)
        if not _is_int(value):
            raise ConfigError(f"{self._full(key)!r} must be an integer, got {value!r}")
        return int(value)

    def get_float(self, key: str) -> float:
        value = self._get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigError(f"{self._full(key)!r} must be a number, got {value!r}")
        return float(value)

    def get_int_pair(self, key: str) -> tuple[int, int]:
        value = self._get(key)
        if not (isinstance(value, list) and len(value) == 2 and all(map(_is_int, value))):
            raise ConfigError(f"{self._full(key)!r} must be [min, max] integers, got {value!r}")
        return int(value[0]), int(value[1])

    def reject_unread(self) -> None:
        if self._unread:
            raise ConfigError(f"unknown config key {self._full(min(self._unread))!r}")
        for child in self._children:
            child.reject_unread()

    def _get(self, key: str) -> Any:
        if key not in self._values:
            raise ConfigError(f"missing config key {self._full(key)!r}")
        self._unread.discard(key)
        return self._values[key]

    def _full(self, key: str) -> str:
        return f"{self._name}.{key}" if self._name else key


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
