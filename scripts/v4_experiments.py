"""v1 | v2 | v2-tuned | v4 on every scenario, held-out seeds.

Writes docs/results/v4-adaptive/heldout.md.

Run with `make v4-experiments`, once, after `make sweep-adaptive` froze [agent.adaptive]. Every
agent uses `config/default.toml` as is. ✔ is paired per seed on identical markets against each
column's baseline (COLUMNS); v4's is against v2-tuned. The ## Interpretation section is
hand-written and kept across reruns.
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
from mm.eval.report import SIGNIFICANT, format_markdown

TRAINING = ("no_informed", "base", "toxic")
COLUMNS = (
    Column("v1 (skew)", "skew", None),
    Column("v2 (kalman)", "kalman", 0),
    Column("v2-tuned (control)", "kalman_tuned", 1),
    Column("v4 (adaptive)", "adaptive", 2),
)
EXTRA = (
    ("lots_informed", "Informed lots filled / episode"),
    ("lots_noise", "Noise lots filled / episode"),
    ("half_spread", "Mean half-spread (ticks)"),
    ("intensity", "Mean ρ"),
)
PATH = Path("docs/results/v4-adaptive/heldout.md")


def scenario_runs(scenario: str) -> list[Run]:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    return [run_column(c.agent, scenario, seeds, n_steps) for c in COLUMNS]


def main() -> None:
    config = load_config()
    seeds, adaptive = config.evaluation.heldout_seeds, config.agent.adaptive
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, every scenario in the "
        f"config. Frozen from the dev sweep: v4 base_half_spread = {adaptive.base_half_spread}, "
        f"uncertainty_weight = {adaptive.uncertainty_weight:g}, intensity_halflife = "
        f"{adaptive.intensity_halflife:g} steps; untuned choices min_scale = "
        f"{adaptive.min_scale:g}, max_scale = {adaptive.max_scale:g}, max_half_spread = "
        f"{adaptive.max_half_spread}. v2-tuned half_spread = "
        f"{config.agent.kalman_tuned.half_spread}; v1 and v2 keep [agent.skew] half_spread = "
        f"{config.agent.skew.half_spread}. Training scenarios (used by the sweep): "
        f"{', '.join(TRAINING)}; the rest are unseen. Money in price units; fair-value error "
        "and half-spread in ticks."
    )
    note = (
        f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference from the column's "
        f"baseline on identical markets has a 95% CI that excludes 0. Baselines: "
        f"{baselines_note(COLUMNS)}; v1 is unmarked. ρ is v4's own intensity scale, averaged "
        "over each episode's steps."
    )
    sections = ["# v4 adaptive: held-out evaluation", intro, note]
    names = scenario_names()
    with ProcessPoolExecutor() as pool:
        all_runs = list(pool.map(scenario_runs, names))
    for scenario, runs in zip(names, all_runs, strict=True):
        kind = "training" if scenario in TRAINING else "unseen"
        sections += [f"## {scenario} ({kind})", format_markdown(side_by_side(runs, COLUMNS, EXTRA))]
    write_with_interpretation(PATH, "\n\n".join(sections))
    print(f"Wrote {PATH}")


if __name__ == "__main__":
    main()
