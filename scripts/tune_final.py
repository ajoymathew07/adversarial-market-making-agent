"""Jointly tune the v5 final agent on dev seeds; writes docs/results/v5-final/dev-search.md.

Run with `make tune`. Held-out seeds are never touched here. A seeded random search over the
grid below (N_CANDIDATES configs, drawn without replacement), always including the tuned
control (kalman_tuned) and the frozen v4 config, listed first in that order. Objective: the
worst case (lowest mean Sharpe) over the training scenarios; ties go to the earlier candidate.
Fixed, untuned: min_scale, max_scale, max_half_spread, ewma_halflife from [agent.final]; τ = 5.
The winner goes into [agent.final] by hand. Then an ablation of the winner (diagnostic only, not
candidates): each adaptive feature switched off, and the control with only the winner's v1
knobs (skew_per_lot, quote_size, base spread), to show where the gain comes from.
"""

import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, fields, replace
from itertools import product
from pathlib import Path

import numpy as np

from mm.config import AgentConfig, load_config
from mm.eval.report import estimate, format_estimate, format_markdown
from mm.eval.runner import evaluate

SCENARIOS = ("no_informed", "base", "toxic")
GRID = {
    "base_half_spread": (3, 4, 5, 6),
    "skew_per_lot": (0.02, 0.05, 0.1, 0.2),
    "quote_size": (2, 3, 5, 8),
    "uncertainty_weight": (0.0, 0.5, 1.0, 2.0),
    "intensity_halflife": (0.0, 20.0, 100.0),  # 0 = off
    "widen_per_tick": (0.0, 1.0, 2.0),
}
MARKOUT_HORIZON = 5
N_CANDIDATES = 200
SEARCH_SEED = 0  # the search's own generator, PCG64(SEARCH_SEED)
TOP = 10
OUT = Path("docs/results/v5-final")


@dataclass(frozen=True)
class Candidate:
    base_half_spread: int
    skew_per_lot: float
    quote_size: int
    uncertainty_weight: float
    intensity_halflife: float
    widen_per_tick: float

    def agent(self) -> AgentConfig:
        base = load_config().agent
        final = replace(
            base.final,
            base_half_spread=self.base_half_spread,
            skew_per_lot=self.skew_per_lot,
            quote_size=self.quote_size,
            uncertainty_weight=self.uncertainty_weight,
            intensity_halflife=self.intensity_halflife,
            widen_per_tick=self.widen_per_tick,
            markout_horizon=MARKOUT_HORIZON,
        )
        return replace(base, type="final", final=final)

    def cells(self) -> list[str]:
        halflife = "off" if self.intensity_halflife == 0 else f"{self.intensity_halflife:g}"
        return [
            str(self.base_half_spread),
            f"{self.skew_per_lot:g}",
            str(self.quote_size),
            f"{self.uncertainty_weight:g}",
            halflife,
            f"{self.widen_per_tick:g}",
        ]


KNOB_LABELS = ("Base", "skew_per_lot", "quote_size", "a", "Half-life", "c")


def control() -> Candidate:
    agent = load_config().agent
    skew = agent.skew
    return Candidate(
        agent.kalman_tuned.half_spread, skew.skew_per_lot, skew.quote_size, 0.0, 0.0, 0.0
    )


def v4() -> Candidate:
    agent = load_config().agent
    a = agent.adaptive
    return Candidate(
        a.base_half_spread,
        agent.skew.skew_per_lot,
        agent.skew.quote_size,
        a.uncertainty_weight,
        a.intensity_halflife,
        0.0,
    )


def candidates() -> list[Candidate]:
    fixed = [control(), v4()]
    grid = [
        Candidate(int(base), skew, int(size), a, halflife, c)
        for base, skew, size, a, halflife, c in product(*GRID.values())
    ]
    grid = [c for c in grid if c not in fixed]
    rng = np.random.Generator(np.random.PCG64(SEARCH_SEED))
    picks = rng.choice(len(grid), size=N_CANDIDATES - len(fixed), replace=False)
    return fixed + [grid[int(i)] for i in picks]


@dataclass(frozen=True)
class Row:
    candidate: Candidate
    sharpes: tuple[float, ...]  # mean Sharpe per training scenario
    cells: tuple[str, ...]  # formatted mean [95% CI] per training scenario

    @property
    def worst(self) -> float:
        return min(self.sharpes)


def score(candidate: Candidate) -> Row:
    config = load_config()
    results = evaluate(
        SCENARIOS, config.evaluation.dev_seeds, config.n_steps, agent_config=candidate.agent()
    )
    estimates = [estimate(r, "sharpe") for r in results]
    return Row(
        candidate, tuple(e.mean for e in estimates), tuple(format_estimate(e) for e in estimates)
    )


def ablations(best: Candidate) -> list[tuple[str, Candidate]]:
    off = replace(best, uncertainty_weight=0.0, intensity_halflife=0.0, widen_per_tick=0.0)
    ctrl = control()
    return [
        ("chosen", best),
        ("chosen, c = 0", replace(best, widen_per_tick=0.0)),
        ("chosen, intensity off", replace(best, intensity_halflife=0.0)),
        ("chosen, a = 0", replace(best, uncertainty_weight=0.0)),
        ("chosen, all three adaptive features off", off),
        ("control with the chosen skew_per_lot", replace(ctrl, skew_per_lot=best.skew_per_lot)),
        (
            "control with the chosen skew_per_lot and quote_size",
            replace(ctrl, skew_per_lot=best.skew_per_lot, quote_size=best.quote_size),
        ),
    ]


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    pool_of = candidates()
    start = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(score, pool_of))
    elapsed = time.perf_counter() - start
    ranked = sorted(rows, key=lambda r: (-r.worst, rows.index(r)))
    best, control_row, v4_row = ranked[0], rows[0], rows[1]
    print(f"searched {len(rows)} configs in {elapsed:.0f} s")
    print(f"best: {best.candidate}, worst-case Sharpe {best.worst:.3f}")
    named = ablations(best.candidate)
    with ProcessPoolExecutor() as pool:
        ablation_rows = list(pool.map(score, [c for _, c in named]))
    ablation = [["Variant", *KNOB_LABELS, *[f"Sharpe {s}" for s in SCENARIOS], "Worst case"]]
    for (name, _), r in zip(named, ablation_rows, strict=True):
        ablation.append([name, *r.candidate.cells(), *r.cells, f"{r.worst:.3f}"])

    sharpe_cols = [f"Sharpe {s}" for s in SCENARIOS]
    header = ["Rank", *KNOB_LABELS, *sharpe_cols, "Worst case", ""]
    top = [header]
    for rank, r in enumerate(ranked[:TOP], start=1):
        tag = "control" if r is control_row else ("v4" if r is v4_row else "")
        top.append([str(rank), *r.candidate.cells(), *r.cells, f"{r.worst:.3f}", tag])
    reference = [header]
    for r in (control_row, v4_row):
        tag = "control" if r is control_row else "v4"
        reference.append(
            [str(ranked.index(r) + 1), *r.candidate.cells(), *r.cells, f"{r.worst:.3f}", tag]
        )

    sensitivity = [["Knob", "Value", "Candidates", "Best worst-case Sharpe"]]
    for knob, label in zip(fields(Candidate), KNOB_LABELS, strict=True):
        for value in GRID[knob.name]:
            matching = [r for r in rows if getattr(r.candidate, knob.name) == value]
            shown = "off" if knob.name == "intensity_halflife" and value == 0 else f"{value:g}"
            best_here = f"{max(r.worst for r in matching):.3f}" if matching else "—"
            sensitivity.append([label, shown, str(len(matching)), best_here])

    final = config.agent.final
    sections = [
        "# v5 final: joint robust tuning, development seeds",
        (
            f"Dev seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, training scenarios "
            f"{', '.join(SCENARIOS)}. Seeded random search (PCG64({SEARCH_SEED})) of "
            f"{len(rows)} configs drawn without replacement from the "
            f"{int(np.prod([len(v) for v in GRID.values()]))}-point grid, always including the "
            "control (kalman_tuned) and the frozen v4 config. Objective: the worst case (lowest "
            "mean Sharpe) of the three; ties go to the earlier candidate. Mean Sharpe [95% CI] "
            f"over seeds. Fixed: τ = {MARKOUT_HORIZON}; untuned choices min_scale = "
            f"{final.min_scale:g}, max_scale = {final.max_scale:g}, max_half_spread = "
            f"{final.max_half_spread}, ewma_halflife = {final.ewma_halflife:g} lots. "
            f"Search wall time {elapsed:.0f} s."
        ),
        "## Result",
        (
            f"Best worst-case Sharpe {best.worst:.3f}; margin over v4 "
            f"{best.worst - v4_row.worst:+.3f} (v4 {v4_row.worst:.3f}) and over the control "
            f"{best.worst - control_row.worst:+.3f} (control {control_row.worst:.3f}). The top "
            "configs differ by less than their 95% CIs, so their order is not meaningful."
        ),
        f"## Top {TOP}",
        format_markdown(top),
        "## The control and v4 in this search",
        format_markdown(reference),
        "## Sensitivity: best worst-case Sharpe per knob value",
        "Over all searched configs with that value, nothing else held fixed.",
        format_markdown(sensitivity),
        "## Ablation of the chosen config (diagnostic, not candidates)",
        format_markdown(ablation),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-search.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev-search.md'}")


if __name__ == "__main__":
    main()
