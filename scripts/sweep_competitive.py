"""Sweep the v6 competitive agent on dev seeds; writes docs/results/v6-competitive/dev-sweep.md.

Run with `make sweep-competitive`. Held-out seeds are never touched here. Full grid over
undercut_per_share (d), min_half_spread, share_halflife and base_half_spread; every other knob is
v5's [agent.final]. With d = 0 the minimum and the half-life do nothing, so d = 0 appears once
per base (base 5, d = 0 is v5 itself, the control). Objective: the worst case (lowest mean
Sharpe) over the training scenarios, competition against v1 included; ties go to the earlier
candidate. The winner goes into [agent.competitive] by hand. Then the detection check: mean
volume share and effective base per training scenario for the winner, for v5 if it is not the
winner, and for the best config with d > 0 (so the signal is seen even when d = 0 wins).
"""

import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

from mm.config import AgentConfig, CompetitionConfig, CompetitiveConfig, load_config
from mm.eval.heldout import bootstrap, per_seed
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import estimate, format_estimate, format_markdown
from mm.eval.runner import evaluate

SCENARIOS = ("no_informed", "base", "toxic", "vs_v1")
GRID = {
    "undercut_per_share": (0.0, 1.0, 2.0, 3.0, 4.0),
    "min_half_spread": (2, 3),
    "share_halflife": (50.0, 200.0),
    "base_half_spread": (4, 5),
}
OUT = Path("docs/results/v6-competitive")


@dataclass(frozen=True)
class Candidate:
    undercut_per_share: float
    min_half_spread: int
    share_halflife: float
    base_half_spread: int

    def agent(self) -> AgentConfig:
        base = load_config().agent
        competitive = CompetitiveConfig(
            final=replace(base.final, base_half_spread=self.base_half_spread),
            competition=CompetitionConfig(
                self.share_halflife, self.undercut_per_share, self.min_half_spread
            ),
        )
        return replace(base, type="competitive", competitive=competitive)

    def cells(self) -> list[str]:
        if self.undercut_per_share == 0:
            return ["0", "—", "—", str(self.base_half_spread)]
        return [
            f"{self.undercut_per_share:g}",
            str(self.min_half_spread),
            f"{self.share_halflife:g}",
            str(self.base_half_spread),
        ]


KNOB_LABELS = ("d", "Min", "Half-life", "Base")
FIRST = int(GRID["min_half_spread"][0]), float(GRID["share_halflife"][0])


def control() -> Candidate:
    """v5: d = 0 at v5's base (the minimum and half-life are then unused)."""
    return Candidate(0.0, FIRST[0], FIRST[1], load_config().agent.final.base_half_spread)


def candidates() -> list[Candidate]:
    grid = [
        Candidate(d, int(floor), halflife, int(base))
        for d, floor, halflife, base in product(*GRID.values())
        if d > 0 or (floor, halflife) == FIRST
    ]
    return [control(), *(c for c in grid if c != control())]


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


def detection(candidate: Candidate) -> list[list[str]]:
    """Per training scenario: mean volume share, effective base and quoted half-spread."""
    config = load_config()
    rows = [["Scenario", "Mean share", "Mean effective base (ticks)", "Mean half-spread (ticks)"]]
    for scenario in SCENARIOS:
        recorder = EpisodeRecorder()
        (result,) = evaluate(
            [scenario],
            config.evaluation.dev_seeds,
            config.n_steps,
            agent_config=candidate.agent(),
            agent_factory=recorder.factory,
        )
        run = (result, recorder)
        cells = [
            format_estimate(bootstrap(per_seed(run, key), result), 2)
            for key in ("share", "effective_base", "half_spread")
        ]
        rows.append([scenario, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    pool_of = candidates()
    start = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(score, pool_of))
    elapsed = time.perf_counter() - start
    ranked = sorted(rows, key=lambda r: (-r.worst, rows.index(r)))
    best, control_row = ranked[0], rows[0]
    print(f"swept {len(rows)} configs in {elapsed:.0f} s")
    print(f"best: {best.candidate}, worst-case Sharpe {best.worst:.3f}")
    best_undercut = next(r for r in ranked if r.candidate.undercut_per_share > 0)
    shown = [("the chosen config" + (" (= v5, the control)" if best is control_row else ""), best)]
    if best is not control_row:
        shown.append(("v5 (control)", control_row))
    shown.append(("the best config with d > 0", best_undercut))
    with ProcessPoolExecutor() as pool:
        detections = list(pool.map(detection, [r.candidate for _, r in shown]))

    header = ["Rank", *KNOB_LABELS, *[f"Sharpe {s}" for s in SCENARIOS], "Worst case", ""]
    table = [header]
    for rank, r in enumerate(ranked, start=1):
        tag = "v5 (control)" if r is control_row else ""
        table.append([str(rank), *r.candidate.cells(), *r.cells, f"{r.worst:.3f}", tag])

    final = config.agent.final
    sections = [
        "# v6 competitive spread: dev sweep",
        (
            f"Dev seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, training scenarios "
            f"{', '.join(SCENARIOS)}. Full grid: d ∈ {GRID['undercut_per_share']}, min ∈ "
            f"{GRID['min_half_spread']}, share half-life ∈ {GRID['share_halflife']} steps, base "
            f"∈ {GRID['base_half_spread']}; d = 0 once per base (min and half-life unused), "
            f"{len(rows)} configs. Every other knob is v5's [agent.final] (skew_per_lot "
            f"{final.skew_per_lot:g}, quote_size {final.quote_size}, a "
            f"{final.uncertainty_weight:g}, intensity_halflife {final.intensity_halflife:g}, c "
            f"{final.widen_per_tick:g}). Objective: the worst case (lowest mean Sharpe) of the "
            "four; ties go to the earlier candidate. Mean Sharpe [95% CI] over seeds. "
            f"Sweep wall time {elapsed:.0f} s."
        ),
        "## Result",
        (
            f"Best worst-case Sharpe {best.worst:.3f} at d = {best.candidate.undercut_per_share:g}, "
            f"min = {best.candidate.min_half_spread}, half-life = "
            f"{best.candidate.share_halflife:g}, base = {best.candidate.base_half_spread}; v5 "
            f"(control) {control_row.worst:.3f}, margin {best.worst - control_row.worst:+.3f}."
        ),
        "## All configs, ranked",
        format_markdown(table),
        "## Detection: volume share and spread (dev seeds)",
        (
            "Mean [95% CI] over seeds of each episode's per-step mean. The share is computed "
            "even with d = 0, where it does not change the quotes."
        ),
    ]
    for (label, r), table_rows in zip(shown, detections, strict=True):
        knobs = ", ".join(f"{k} {v}" for k, v in zip(KNOB_LABELS, r.candidate.cells(), strict=True))
        sections += [f"### {label} ({knobs})", format_markdown(table_rows)]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-sweep.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev-sweep.md'}")


if __name__ == "__main__":
    main()
