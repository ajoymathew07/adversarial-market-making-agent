"""Tune v3 and its tuned-spread control on dev seeds; writes docs/results/v3-toxicity/dev-sweep.md.

Run with `make sweep-toxicity`. Held-out seeds are never touched here. Both searches use the
same objective, the worst-case mean Sharpe over the training scenarios:
- control: v2 (kalman) with half-spread h in HALF_SPREADS;
- v3: base half-spread h in HALF_SPREADS × τ in HORIZONS × c in WIDENINGS.
v3 counts as working only if its best beats the control's best. Ties go to the first config in
grid order. The winners go into [agent.kalman_tuned] and [agent.toxicity] by hand. Then a
detection check: v3's mean toxicity per training scenario and its per-episode correlation with
the share of the agent's lots that went to informed takers (from the simulation's fill records).
"""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

import numpy as np

from mm.config import AgentConfig, load_config
from mm.eval.compare import paired_estimate
from mm.eval.recording import EpisodeRecorder, informed_lot_share
from mm.eval.report import estimate, format_estimate, format_markdown
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import bootstrap_ci

SCENARIOS = ("no_informed", "base", "toxic")
HALF_SPREADS = (2, 3, 4, 5, 6)
HORIZONS = (5, 10, 20, 40)
WIDENINGS = (0.0, 0.5, 1.0, 2.0, 4.0, 8.0)
OUT = Path("docs/results/v3-toxicity")
CHOSEN = "◀ chosen"


@dataclass(frozen=True)
class Setting:
    half_spread: int
    horizon: int | None = None  # None: the control
    widening: float | None = None

    def agent(self) -> AgentConfig:
        base = load_config().agent
        if self.horizon is None:
            tuned = replace(base.kalman_tuned, half_spread=self.half_spread)
            return replace(base, type="kalman_tuned", kalman_tuned=tuned)
        assert self.widening is not None
        toxicity = replace(
            base.toxicity,
            base_half_spread=self.half_spread,
            markout_horizon=self.horizon,
            widen_per_tick=self.widening,
        )
        return replace(base, type="toxicity", toxicity=toxicity)


@dataclass(frozen=True)
class Row:
    setting: Setting
    sharpes: tuple[str, ...]  # formatted mean [95% CI] per training scenario
    worst: float  # lowest mean Sharpe of the training scenarios


def run(setting: Setting) -> list[ScenarioResult]:
    config = load_config()
    return evaluate(
        SCENARIOS, config.evaluation.dev_seeds, config.n_steps, agent_config=setting.agent()
    )


def score(setting: Setting) -> Row:
    sharpes = [estimate(r, "sharpe") for r in run(setting)]
    return Row(setting, tuple(format_estimate(s) for s in sharpes), min(s.mean for s in sharpes))


def best(rows: list[Row]) -> Row:
    return max(rows, key=lambda r: (r.worst, -rows.index(r)))


def detection(setting: Setting) -> tuple[list[list[str]], list[list[str]]]:
    """Mean T per training scenario, and corr(mean T, informed lot share) per episode."""
    config = load_config()
    settings = config.evaluation
    scores: list[float] = []
    shares: list[float] = []
    mean_table = [["Scenario", "Mean T (ticks)", "Mean half-spread (ticks)", "Informed lot share"]]
    corr_table = [["Episodes", "n", "corr(mean T, informed lot share)"]]
    for scenario in SCENARIOS:
        recorder = EpisodeRecorder()
        (result,) = evaluate(
            [scenario],
            settings.dev_seeds,
            config.n_steps,
            agent_config=setting.agent(),
            agent_factory=recorder.factory,
        )
        t, share = recorder.mean_toxicity(), informed_lot_share(result)
        cells = [
            bootstrap_ci(v, settings.bootstrap_resamples, settings.bootstrap_seed)
            for v in (t, recorder.mean_half_spread(), share)
        ]
        mean_table.append([scenario, *(format_estimate(c, 3) for c in cells)])
        if scenario != "no_informed":  # share is 0 in every episode there
            corr_table.append([scenario, str(len(t)), f"{np.corrcoef(t, share)[0, 1]:.3f}"])
        scores += t
        shares += share
    pooled = f"{np.corrcoef(scores, shares)[0, 1]:.3f}"
    corr_table.append([f"pooled ({', '.join(SCENARIOS)})", str(len(scores)), pooled])
    return mean_table, corr_table


def paired_table(v3: Setting, control: Setting) -> list[list[str]]:
    rows = [["Scenario", "Sharpe, control", "Sharpe, v3", "Δ Sharpe v3 − control (paired)"]]
    for a, b in zip(run(v3), run(control), strict=True):
        rows.append(
            [
                a.scenario,
                format_estimate(estimate(b, "sharpe")),
                format_estimate(estimate(a, "sharpe")),
                format_estimate(paired_estimate(a, b, "sharpe")),
            ]
        )
    return rows


def label(s: Setting) -> str:
    if s.horizon is None:
        return f"control half_spread = {s.half_spread}"
    return f"v3 base_half_spread = {s.half_spread}, τ = {s.horizon}, c = {s.widening:g}"


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    controls = [Setting(h) for h in HALF_SPREADS]
    grid = [Setting(h, t, c) for h, t, c in product(HALF_SPREADS, HORIZONS, WIDENINGS)]
    with ProcessPoolExecutor() as pool:
        control_rows = list(pool.map(score, controls))
        v3_rows = list(pool.map(score, grid))
    control, v3 = best(control_rows), best(v3_rows)
    print(f"control best: {label(control.setting)}, worst-case Sharpe {control.worst:.3f}")
    print(f"v3 best: {label(v3.setting)}, worst-case Sharpe {v3.worst:.3f}")

    sharpe_cols = [f"Sharpe {s}" for s in SCENARIOS]
    control_table = [["Half-spread", *sharpe_cols, "Worst case", ""]]
    for r in control_rows:
        mark = CHOSEN if r is control else ""
        control_table.append([str(r.setting.half_spread), *r.sharpes, f"{r.worst:.2f}", mark])
    per_base = [["Base half-spread", "τ", "c", *sharpe_cols, "Worst case", ""]]
    for h in HALF_SPREADS:
        r = best([row for row in v3_rows if row.setting.half_spread == h])
        s = r.setting
        mark = CHOSEN if r is v3 else ""
        per_base.append(
            [str(h), str(s.horizon), f"{s.widening:g}", *r.sharpes, f"{r.worst:.2f}", mark]
        )
    grid_table = [["Base half-spread", "τ", "c", *sharpe_cols, "Worst case", ""]]
    for r in v3_rows:
        s = r.setting
        mark = CHOSEN if r is v3 else ""
        grid_table.append(
            [
                str(s.half_spread),
                str(s.horizon),
                f"{s.widening:g}",
                *r.sharpes,
                f"{r.worst:.2f}",
                mark,
            ]
        )

    margin = v3.worst - control.worst
    verdict = "yes" if margin > 0 else "no"
    tox = config.agent.toxicity
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, training scenarios "
        f"{', '.join(SCENARIOS)}. Mean Sharpe [95% CI] over seeds. Objective for both searches: "
        "the worst case (lowest mean Sharpe) of the three; ties go to the first config in grid "
        f"order. Fixed for v3: ewma_halflife = {tox.ewma_halflife:g} lots, max_half_spread = "
        f"{tox.max_half_spread} ticks (untuned choices). v3 with c = 0 is the control at the same "
        "half-spread."
    )
    mean_table, corr_table = detection(v3.setting)
    sections = [
        "# v3 toxicity: tuning against a tuned-spread control, development seeds",
        intro,
        "## Verdict",
        (
            f"Does v3 beat the tuned-spread control? **{verdict}**. Best worst-case Sharpe: v3 "
            f"{v3.worst:.3f} ({label(v3.setting)}) against control {control.worst:.3f} "
            f"({label(control.setting)}), a margin of {margin:+.3f}."
        ),
        format_markdown(paired_table(v3.setting, control.setting)),
        "## Control: v2 (kalman) with a tuned half-spread",
        format_markdown(control_table),
        "## v3: best τ and c for each base half-spread",
        format_markdown(per_base),
        "## Detection check for the chosen v3",
        (
            "Mean over each episode's steps; informed lot share = informed lots / all lots the agent "
            "filled, from the simulation's fill records (never seen by the agent)."
        ),
        format_markdown(mean_table),
        format_markdown(corr_table),
        "## v3: full grid",
        format_markdown(grid_table),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-sweep.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev-sweep.md'}")


if __name__ == "__main__":
    main()
