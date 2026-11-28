"""Sweep v3's markout horizon τ and widening c on dev seeds; writes docs/results/v3-toxicity/dev-sweep.md.

Run with `make sweep-toxicity`. Held-out seeds are never touched here. The objective is the
worst-case mean Sharpe over the training scenarios; the argmax goes into [agent.toxicity] by hand.
Ties go to the first row in grid order (c = 0 rows are v2 and identical for every τ).
"""

from dataclasses import replace
from pathlib import Path

from mm.config import load_config
from mm.eval.report import estimate, format_estimate, format_markdown
from mm.eval.runner import evaluate

SCENARIOS = ("no_informed", "base", "toxic")
HORIZONS = (5, 10, 20)
WIDENINGS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
OUT = Path("docs/results/v3-toxicity")
CHOSEN = "◀ chosen"


def main() -> None:
    config = load_config()
    seeds, n_steps = config.evaluation.dev_seeds, config.n_steps
    rows: list[tuple[int, float, list[str], float]] = []
    for tau in HORIZONS:
        for c in WIDENINGS:
            toxicity = replace(config.agent.toxicity, markout_horizon=tau, widen_per_tick=c)
            agent = replace(config.agent, type="toxicity", toxicity=toxicity)
            results = evaluate(SCENARIOS, seeds, n_steps, agent_config=agent)
            sharpes = [estimate(r, "sharpe") for r in results]
            worst = min(s.mean for s in sharpes)
            rows.append((tau, c, [format_estimate(s) for s in sharpes], worst))
            print(f"tau={tau} c={c:g} worst-case Sharpe {worst:.3f}")
    best = max(range(len(rows)), key=lambda i: (rows[i][3], -i))
    table = [["τ (steps)", "c (ticks/tick)", *(f"Sharpe {s}" for s in SCENARIOS), "Worst case", ""]]
    for i, (tau, c, cells, worst) in enumerate(rows):
        table.append([str(tau), f"{c:g}", *cells, f"{worst:.2f}", CHOSEN if i == best else ""])
    tox = config.agent.toxicity
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {n_steps} steps, training scenarios "
        f"{', '.join(SCENARIOS)}. Mean Sharpe [95% CI] over seeds. Objective: the worst case "
        f"(lowest mean Sharpe) of the three; ties go to the first row. Fixed: ewma_halflife = "
        f"{tox.ewma_halflife:g} lots, max_half_spread = {tox.max_half_spread} ticks, base "
        f"half-spread {config.agent.skew.half_spread}. c = 0 is v2."
    )
    tau, c = rows[best][0], rows[best][1]
    sections = [
        "# v3 toxicity: τ × c sweep on development seeds",
        intro,
        format_markdown(table),
        f"Chosen: markout_horizon = {tau}, widen_per_tick = {c:g}.",
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-sweep.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Chosen tau={tau} c={c:g}; wrote {OUT / 'dev-sweep.md'}")


if __name__ == "__main__":
    main()
