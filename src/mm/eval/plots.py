"""PNG plots of the evaluation, drawn on matplotlib's Agg canvas (no pyplot global state)."""

import math
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mm.eval.metrics import KINDS, mark_to_market_path
from mm.eval.runner import ScenarioResult
from mm.market import TakerKind

# Fixed categorical order, so a scenario or kind keeps its colour across plots.
SERIES_COLOURS = ("#2a78d6", "#eb6834", "#1baf7a")
GRID_COLOUR = "#e0e0e0"
ZERO_LINE_COLOUR = "#888888"


def write_plots(results: list[ScenarioResult], directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _plot_pnl_paths(results, directory / "pnl_paths.png")
    _plot_inventory_paths(results, directory / "inventory_paths.png")
    _plot_markouts(results, directory / "markouts.png")


def _plot_pnl_paths(results: list[ScenarioResult], path: Path) -> None:
    fig, ax = _new_figure()
    for result, colour in zip(results, SERIES_COLOURS, strict=False):
        pnl = mark_to_market_path(result.example)[1:] * result.config.instrument.tick_size
        ax.plot(pnl, color=colour, linewidth=1.5, label=result.scenario)
    _finish_path_axes(ax, results, "Mark-to-market PnL")
    _save(fig, path)


def _plot_inventory_paths(results: list[ScenarioResult], path: Path) -> None:
    fig, ax = _new_figure()
    for result, colour in zip(results, SERIES_COLOURS, strict=False):
        positions = [step.position for step in result.example.steps]
        ax.plot(positions, color=colour, linewidth=1.5, label=result.scenario)
    _finish_path_axes(ax, results, "Inventory (lots)")
    _save(fig, path)


def _plot_markouts(results: list[ScenarioResult], path: Path) -> None:
    fig = Figure(figsize=(4 * len(results), 4))
    axes = fig.subplots(1, len(results), sharey=True, squeeze=False)[0]
    for ax, result in zip(axes, results, strict=True):
        horizons = result.config.evaluation.markout_horizons
        for kind, colour in zip(KINDS, SERIES_COLOURS, strict=False):
            curve = [_mean_markout(result, kind, h) for h in horizons]
            if not all(math.isnan(v) for v in curve):
                ax.plot(horizons, curve, color=colour, linewidth=2, marker="o", label=kind)
        ax.axhline(0.0, color=ZERO_LINE_COLOUR, linewidth=1)
        ax.set_title(result.scenario)
        ax.set_xlabel("Horizon (steps)")
        _style(ax)
    axes[0].set_ylabel("Avg markout per lot")
    fig.suptitle(f"Markout by counterparty kind, mean over {len(results[0].seeds)} seeds")
    _save(fig, path)


def _mean_markout(result: ScenarioResult, kind: TakerKind, horizon: int) -> float:
    """Mean over seeds that have fills of this kind; NaN when none do."""
    values = [m.markouts[(kind, horizon)] for m in result.metrics]
    present = [v for v in values if not math.isnan(v)]
    return float(np.mean(present)) if present else math.nan


def _new_figure() -> tuple[Figure, Axes]:
    fig = Figure(figsize=(9, 4.5))
    return fig, fig.subplots()


def _finish_path_axes(ax: Axes, results: list[ScenarioResult], ylabel: str) -> None:
    ax.set_title(f"{ylabel}, seed {results[0].seeds[0]}")
    ax.set_xlabel("Step")
    ax.set_ylabel(ylabel)
    _style(ax)


def _style(ax: Axes) -> None:
    ax.grid(color=GRID_COLOUR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False)


def _save(fig: Figure, path: Path) -> None:
    FigureCanvasAgg(fig)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
