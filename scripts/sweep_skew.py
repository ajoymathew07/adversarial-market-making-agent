"""Sweep the skew agent's gamma on the development seeds; write a table and a trade-off plot.

Run with `make sweep`. Held-out seeds are never touched here: gamma is chosen from this output.
"""

from dataclasses import replace
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mm.config import load_config
from mm.eval.compare import paired_estimate
from mm.eval.plots import GRID_COLOUR, SERIES_COLOURS
from mm.eval.report import SUMMARY_METRICS, estimate, format_estimate, format_markdown
from mm.eval.runner import ScenarioResult, evaluate

GAMMAS = (0.0, 0.002, 0.005, 0.01, 0.015, 0.02, 0.03, 0.05)
SCENARIOS = ("base", "toxic")
N_STEPS = 2000
OUT = Path("docs/results/v1-skew")
COLUMNS = [c for c in SUMMARY_METRICS if not c[0].startswith("markout_")]
PAIRED = (("final_pnl", "Δ Final PnL vs naive"), ("sharpe", "Δ Sharpe vs naive"))

# gamma -> scenario -> result
Sweep = dict[float, dict[str, ScenarioResult]]


def run_sweep() -> tuple[dict[str, ScenarioResult], Sweep]:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    naive = {r.scenario: r for r in evaluate(SCENARIOS, seeds, N_STEPS, agent="naive")}
    sweep: Sweep = {}
    for gamma in GAMMAS:
        agent = replace(config.agent, type="skew", skew=replace(config.agent.skew, gamma=gamma))
        results = evaluate(SCENARIOS, seeds, N_STEPS, agent_config=agent)
        sweep[gamma] = {r.scenario: r for r in results}
    return naive, sweep


def scenario_table(
    scenario: str, naive: dict[str, ScenarioResult], sweep: Sweep
) -> list[list[str]]:
    header = ["γ", "Skew/lot", *(label for _, label in COLUMNS), *(label for _, label in PAIRED)]
    rows = [header]
    for gamma, results in sweep.items():
        result = results[scenario]
        cells = [format_estimate(estimate(result, column)) for column, _ in COLUMNS]
        paired = [
            format_estimate(paired_estimate(result, naive[scenario], column))
            for column, _ in PAIRED
        ]
        skew_per_lot = result.config.agent.skew.skew_per_lot
        rows.append([f"{gamma:g}", f"{skew_per_lot:.3g}", *cells, *paired])
    return rows


def plot_trade_off(sweep: Sweep, path: Path) -> None:
    fig = Figure(figsize=(9, 5))
    ax = fig.subplots()
    # Labels go above the line for the first scenario and below for the second, so they don't overlap.
    offsets = ((-12, 8), (6, -14))
    for scenario, colour, offset in zip(SCENARIOS, SERIES_COLOURS, offsets, strict=False):
        xs = [estimate(r[scenario], "mean_abs_position").mean for r in sweep.values()]
        ys = [estimate(r[scenario], "final_pnl").mean for r in sweep.values()]
        ax.plot(xs, ys, color=colour, linewidth=1.5, marker="o", label=scenario)
        for gamma, x, y in zip(sweep, xs, ys, strict=True):
            label = f"γ={gamma:g}"
            ax.annotate(label, (x, y), textcoords="offset points", xytext=offset, color=colour)
    ax.set_title(f"Skew agent: inventory risk vs PnL, dev seeds, {N_STEPS} steps")
    ax.set_xscale("log")  # most gammas sit at |q| of 3 to 8 lots; log spreads them out
    ax.set_xticks([3, 5, 10, 20, 40], labels=["3", "5", "10", "20", "40"])
    ax.minorticks_off()
    ax.set_xlabel("Mean |q| (lots, log scale)")
    ax.set_ylabel("Mean final PnL")
    ax.grid(color=GRID_COLOUR, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False)
    FigureCanvasAgg(fig)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main() -> None:
    naive, sweep = run_sweep()
    seeds = load_config().evaluation.dev_seeds
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {N_STEPS} steps; σ = 1, τ = 10, so skew/lot = 10γ "
        "ticks per lot. Mean [95% CI] over seeds; money in price units. Δ columns are paired "
        "per-seed differences (skew − naive) on the same markets."
    )
    sections = ["# v1 skew: γ sweep on development seeds", intro]
    for scenario in SCENARIOS:
        sections += [f"## {scenario}", format_markdown(scenario_table(scenario, naive, sweep))]
    sections.append("Plot: `dev-sweep.png` (mean |q| against mean final PnL, one point per γ).")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-sweep.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    plot_trade_off(sweep, OUT / "dev-sweep.png")
    print(f"Wrote {OUT / 'dev-sweep.md'} and {OUT / 'dev-sweep.png'}")


if __name__ == "__main__":
    main()
