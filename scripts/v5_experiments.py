"""v1 | v2 | v2-tuned | v4 | v5 on every scenario, held-out seeds, run once.

Writes docs/results/v5-final/heldout.md (docs/results/summary.md: make v6-experiments). Run with
`make v5-experiments` after `make tune` froze [agent.final]. Every agent uses
`config/default.toml` as is. ✔ is paired per seed on identical markets against each column's
baseline (COLUMNS); v5's is against v2-tuned. Also the overfitting check: dev worst-case Sharpe
over the training scenarios next to the held-out one, for v5, v4 and the control. The
## Interpretation section is hand-written and kept across reruns.
"""

from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from mm.config import load_config, scenario_names
from mm.eval.heldout import (
    Column,
    Run,
    baselines_note,
    run_column,
    side_by_side,
    write_with_interpretation,
)
from mm.eval.report import SIGNIFICANT, estimate, format_markdown
from mm.eval.runner import evaluate

TRAINING = ("no_informed", "base", "toxic")
COLUMNS = (
    Column("v1 (skew)", "skew", None),
    Column("v2 (kalman)", "kalman", 0),
    Column("v2-tuned (control)", "kalman_tuned", 1),
    Column("v4 (adaptive)", "adaptive", 2),
    Column("v5 (final)", "final", 2),
)
EXTRA = (
    ("lots_informed", "Informed lots filled / episode"),
    ("lots_noise", "Noise lots filled / episode"),
    ("half_spread", "Mean half-spread (ticks)"),
    ("intensity", "Mean ρ"),
)
OVERFIT = ("kalman_tuned", "adaptive", "final")
HELDOUT = Path("docs/results/v5-final/heldout.md")


def scenario_runs(scenario: str) -> list[Run]:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    return [run_column(c.agent, scenario, seeds, n_steps) for c in COLUMNS]


def dev_worst_case(agent: str) -> float:
    config = load_config()
    results = evaluate(TRAINING, config.evaluation.dev_seeds, config.n_steps, agent=agent)
    return min(estimate(r, "sharpe").mean for r in results)


def main() -> None:
    config = load_config()
    seeds, final = config.evaluation.heldout_seeds, config.agent.final
    adaptive = config.agent.adaptive
    halflife = "off" if final.intensity_halflife == 0 else f"{final.intensity_halflife:g} steps"
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, every scenario in the "
        f"config, run once after `make tune` froze [agent.final]: base_half_spread = "
        f"{final.base_half_spread}, skew_per_lot = {final.skew_per_lot:g}, quote_size = "
        f"{final.quote_size}, a = {final.uncertainty_weight:g}, intensity_halflife = {halflife}, "
        f"c = {final.widen_per_tick:g}, τ = {final.markout_horizon}. v4: base "
        f"{adaptive.base_half_spread}, a = {adaptive.uncertainty_weight:g}, intensity_halflife = "
        f"{adaptive.intensity_halflife:g}. v2-tuned half_spread = "
        f"{config.agent.kalman_tuned.half_spread}; v1, v2, v2-tuned and v4 keep [agent.skew] "
        f"skew_per_lot = {config.agent.skew.skew_per_lot:g} and quote_size = "
        f"{config.agent.skew.quote_size}. Training scenarios: {', '.join(TRAINING)}; the rest "
        "are unseen. Money in price units."
    )
    note = (
        f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference from the column's "
        f"baseline on identical markets has a 95% CI that excludes 0. Baselines: "
        f"{baselines_note(COLUMNS)}; v1 is unmarked."
    )
    names = scenario_names()
    with ProcessPoolExecutor() as pool:
        all_runs = list(pool.map(scenario_runs, names))
        dev = dict(zip(OVERFIT, pool.map(dev_worst_case, OVERFIT), strict=True))

    overfit = [
        [
            "Agent",
            "Dev worst-case Sharpe (seeds 0–29)",
            "Held-out worst-case Sharpe (seeds 1000–1029)",
            "Held-out − dev",
        ]
    ]
    training = [runs for name, runs in zip(names, all_runs, strict=True) if name in TRAINING]
    for agent in OVERFIT:
        i = [c.agent for c in COLUMNS].index(agent)
        held = min(estimate(runs[i][0], "sharpe").mean for runs in training)
        overfit.append(
            [COLUMNS[i].label, f"{dev[agent]:.3f}", f"{held:.3f}", f"{held - dev[agent]:+.3f}"]
        )

    sections = ["# v5 final: held-out evaluation", intro, note]
    sections += [
        "## Overfitting check (training scenarios, worst case of the three mean Sharpes)",
        format_markdown(overfit),
    ]
    for scenario, runs in zip(names, all_runs, strict=True):
        kind = "training" if scenario in TRAINING else "unseen"
        sections += [f"## {scenario} ({kind})", format_markdown(side_by_side(runs, COLUMNS, EXTRA))]
    write_with_interpretation(HELDOUT, "\n\n".join(sections))

    print(f"Wrote {HELDOUT}")


if __name__ == "__main__":
    main()
