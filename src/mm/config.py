"""Typed schema for `config/default.toml` and its strict loader.

Every parameter value lives in the TOML file. The dataclasses here have no defaults: they give
each value a type, check its range and derive the quantities the code uses.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mm.engine.units import price_to_ticks

# src/mm/config.py -> repo root (or /app in Docker) -> config/default.toml
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"


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
class SimConfig:
    """Everything one episode needs, built from the config file."""

    instrument: InstrumentConfig
    engine: EngineConfig


def load_config(path: Path | None = None) -> SimConfig:
    """Read the config file (default: `config/default.toml`) into typed objects."""
    with (path or DEFAULT_CONFIG_PATH).open("rb") as handle:
        return build_config(tomllib.load(handle))


def build_config(raw: dict[str, Any]) -> SimConfig:
    """Build the typed config from parsed TOML. Raises ValueError naming any bad key."""
    root = _Table(raw, "")
    config = SimConfig(
        instrument=_instrument(root.get_table("instrument")),
        engine=_engine(root.get_table("engine")),
    )
    root.reject_unread()
    return config


def _instrument(table: "_Table") -> InstrumentConfig:
    return InstrumentConfig(
        tick_size=table.get_float("tick_size"),
        initial_price=table.get_float("initial_price"),
    )


def _engine(table: "_Table") -> EngineConfig:
    return EngineConfig(fee_per_lot=table.get_int("fee_per_lot"))


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
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{self._full(key)!r} must be an integer, got {value!r}")
        return value

    def get_float(self, key: str) -> float:
        value = self._get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigError(f"{self._full(key)!r} must be a number, got {value!r}")
        return float(value)

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
