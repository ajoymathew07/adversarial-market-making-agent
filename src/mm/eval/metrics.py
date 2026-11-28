"""Per-episode metrics from an EpisodeResult. Money is reported in price units (ticks x tick_size).

PnL decomposition (exact, by summation by parts):
    final PnL = spread capture + inventory PnL - fees
    spread capture = sum over fills of s * (V(t_fill) - price) * size
    inventory PnL  = sum_{t=0}^{T-1} q_t * (V(t+1) - V(t))
where s = +1 for an agent buy, -1 for a sell, and q_t is the position after step t's fills.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from mm.market import TakerKind
from mm.simulation import EpisodeResult, FillRecord

KINDS: tuple[TakerKind, ...] = ("noise", "informed")
GATE_RULES: tuple[str, ...] = ("size", "price_band", "self_cross", "position_clip")


@dataclass(frozen=True)
class EpisodeMetrics:
    final_pnl: float
    spread_capture: float
    inventory_pnl: float
    fees: float
    max_drawdown: float
    sharpe: float
    fill_rate: float  # lots filled / lots quoted
    mean_abs_position: float
    max_abs_position: int
    pct_time_at_limit: float  # % of steps with |q| == position_limit
    fills: dict[TakerKind, int]
    lots: dict[TakerKind, int]
    # Size-weighted average markout per lot, keyed by (kind, horizon) in kind-then-horizon
    # order; NaN when no fills.
    markouts: dict[tuple[TakerKind, int], float]
    gate_events: dict[str, int]

    def as_row(self) -> dict[str, float]:
        """Flatten every scalar into one CSV-ready row with stable column names."""
        row: dict[str, float] = {
            "final_pnl": self.final_pnl,
            "spread_capture": self.spread_capture,
            "inventory_pnl": self.inventory_pnl,
            "fees": self.fees,
            "max_drawdown": self.max_drawdown,
            "sharpe": self.sharpe,
            "fill_rate": self.fill_rate,
            "mean_abs_position": self.mean_abs_position,
            "max_abs_position": self.max_abs_position,
            "pct_time_at_limit": self.pct_time_at_limit,
        }
        for kind in KINDS:
            row[f"fills_{kind}"] = self.fills[kind]
            row[f"lots_{kind}"] = self.lots[kind]
        for (kind, horizon), value in self.markouts.items():
            row[f"markout_{kind}_{horizon}"] = value
        for rule in GATE_RULES:
            row[f"gate_{rule}"] = self.gate_events[rule]
        return row


def episode_metrics(
    result: EpisodeResult,
    tick_size: float,
    fee_per_lot: int,
    position_limit: int,
    horizons: Sequence[int],
) -> EpisodeMetrics:
    path = np.asarray(result.path)
    positions = np.array([step.position for step in result.steps])
    abs_positions = np.abs(positions)
    mtm = mark_to_market_path(result)
    lots_filled = sum(fill.size for fill in result.fills)
    lots_quoted = sum(step.bid_size + step.ask_size for step in result.steps)
    return EpisodeMetrics(
        final_pnl=result.final_pnl * tick_size,
        spread_capture=spread_capture(result.fills) * tick_size,
        inventory_pnl=inventory_pnl(positions, path) * tick_size,
        fees=fee_per_lot * lots_filled * tick_size,
        max_drawdown=max_drawdown(mtm) * tick_size,
        sharpe=sharpe(mtm),
        fill_rate=lots_filled / lots_quoted if lots_quoted else 0.0,
        mean_abs_position=float(abs_positions.mean()),
        max_abs_position=int(abs_positions.max()),
        pct_time_at_limit=100.0 * float(np.mean(abs_positions == position_limit)),
        fills={kind: sum(1 for f in result.fills if f.taker_kind == kind) for kind in KINDS},
        lots={kind: sum(f.size for f in result.fills if f.taker_kind == kind) for kind in KINDS},
        markouts={
            (kind, h): markout(result.fills, result.path, kind, h) * tick_size
            for kind in KINDS
            for h in horizons
        },
        gate_events={
            rule: sum(1 for entry in result.gate_events if entry.event.rule == rule)
            for rule in GATE_RULES
        },
    )


def spread_capture(fills: list[FillRecord]) -> float:
    """In ticks: how good each fill price was against the true value at that step."""
    return sum(f.side.sign * (f.true_value - f.price) * f.size for f in fills)


def inventory_pnl(positions: NDArray[np.int_], path: NDArray[np.float64]) -> float:
    """In ticks: sum of q_t * (V(t+1) - V(t)) over the episode's steps."""
    n_steps = len(positions)
    return float(np.dot(positions, np.diff(path[: n_steps + 1])))


def markout(fills: list[FillRecord], path: tuple[float, ...], kind: TakerKind, horizon: int) -> float:
    """In ticks per lot: size-weighted s * (V(t + horizon) - price) over fills of one kind.

    Fills whose t + horizon lies beyond the path are skipped; NaN if no fill remains.
    """
    total = 0.0
    lots = 0
    for f in fills:
        if f.taker_kind != kind or f.step + horizon >= len(path):
            continue
        total += f.side.sign * (path[f.step + horizon] - f.price) * f.size
        lots += f.size
    return total / lots if lots else math.nan


def mark_to_market_path(result: EpisodeResult) -> NDArray[np.float64]:
    """In ticks: m = 0 before the first step, then cash_t + q_t * V(t) after each step."""
    values = [step.cash + step.position * step.true_value for step in result.steps]
    return np.array([0.0, *values])


def max_drawdown(series: NDArray[np.float64]) -> float:
    """Largest peak-to-trough drop of the series (>= 0)."""
    return float(np.max(np.maximum.accumulate(series) - series))


def sharpe(series: NDArray[np.float64]) -> float:
    """mean / std of the per-step changes, times sqrt(number of changes); 0 if std is 0."""
    changes = np.diff(series)
    std = float(changes.std())
    if std == 0.0:
        return 0.0
    return float(changes.mean()) / std * math.sqrt(len(changes))
