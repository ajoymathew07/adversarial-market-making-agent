"""v2-tuned | v5 | v6 on every scenario, held-out seeds, run once.

Writes docs/results/v6-competitive/heldout.md and docs/results/summary.md. Run with
`make v6-experiments` after `make sweep-competitive` froze [agent.competitive]. Every agent uses
`config/default.toml` as is. ✔ is paired per seed on identical markets: v6 against v5, v5
against v2-tuned. Also the overfitting check (dev vs held-out worst-case Sharpe over the training
scenarios) and the undercutting-war check (vs_competitive, v6 self-play, an unseen scenario).
Because the frozen v6 has d = 0, the war check also runs the best d > 0 config from the dev sweep
as a diagnostic (not a candidate; nothing is chosen from it). The summary adds v1, v2 and v4 so
it keeps its earlier columns. The ## Interpretation section is hand-written and kept across reruns.
"""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

from mm.config import AgentConfig, CompetitionConfig, load_config, scenario_names
from mm.eval.compare import is_significant, paired_estimate
from mm.eval.heldout import (
    Column,
    Run,
    baselines_note,
    bootstrap,
    per_seed,
    run_column,
    side_by_side,
    write_with_interpretation,
)
from mm.eval.metrics import EpisodeMetrics
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import SIGNIFICANT, estimate, format_estimate, format_markdown
from mm.eval.runner import ScenarioResult, evaluate

TRAINING = ("no_informed", "base", "toxic", "vs_v1")
V5_TRAINING = ("no_informed", "base", "toxic")  # v1–v5 never trained on vs_v1
COLUMNS = (
    Column("v2-tuned", "kalman_tuned", None),
    Column("v5 (final)", "final", 0),
    Column("v6 (competitive)", "competitive", 1),
)
EXTRA = (
    ("lots_informed", "Informed lots filled / episode"),
    ("lots_noise", "Noise lots filled / episode"),
    ("half_spread", "Mean half-spread (ticks)"),
    ("share", "Mean volume share (v6)"),
    ("effective_base", "Mean effective base (ticks, v6)"),
)
# Summary columns: (short label, registry name); ✔ on v5 against v2-tuned, on v6 against v5.
SUMMARY_AGENTS = (
    ("v1", "skew"),
    ("v2", "kalman"),
    ("v2-tuned", "kalman_tuned"),
    ("v4", "adaptive"),
    ("v5", "final"),
    ("v6", "competitive"),
)
SUMMARY_BASELINES = {"final": "kalman_tuned", "competitive": "final"}
OVERFIT = ("final", "competitive")
WAR = ("vs_v1", "vs_competitive")
# The best d > 0 config of docs/results/v6-competitive/dev-sweep.md (rank 2), other knobs v5's.
DIAGNOSTIC = CompetitionConfig(share_halflife=50.0, undercut_per_share=1.0, min_half_spread=2)
DIAGNOSTIC_BASE = 5
HELDOUT = Path("docs/results/v6-competitive/heldout.md")
SUMMARY = Path("docs/results/summary.md")


def scenario_runs(scenario: str) -> dict[str, Run]:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    return {agent: run_column(agent, scenario, seeds, n_steps) for _, agent in SUMMARY_AGENTS}


def dev_worst_case(agent: str) -> float:
    config = load_config()
    results = evaluate(TRAINING, config.evaluation.dev_seeds, config.n_steps, agent=agent)
    return min(estimate(r, "sharpe").mean for r in results)


def diagnostic_agent() -> AgentConfig:
    agent = load_config().agent
    final = replace(agent.competitive.final, base_half_spread=DIAGNOSTIC_BASE)
    competitive = replace(agent.competitive, final=final, competition=DIAGNOSTIC)
    return replace(agent, type="competitive", competitive=competitive)


def war_run(spec: tuple[str, bool]) -> Run:
    """One held-out war-check run: (scenario, use the diagnostic d > 0 config)."""
    scenario, diagnostic = spec
    config = load_config()
    recorder = EpisodeRecorder()
    (result,) = evaluate(
        [scenario],
        config.evaluation.heldout_seeds,
        config.n_steps,
        agent="competitive",
        agent_config=diagnostic_agent() if diagnostic else None,
        agent_factory=recorder.factory,
    )
    return result, recorder


def lots(metrics: EpisodeMetrics) -> int:
    return metrics.lots["noise"] + metrics.lots["informed"]


def maker_share(result: ScenarioResult) -> list[float]:
    """Per seed: % of all maker lots that were ours."""
    pairs = zip(result.metrics, result.competitor_metrics, strict=True)
    return [100 * lots(m) / (lots(m) + lots(c)) if lots(m) + lots(c) else 0.0 for m, c in pairs]


def war_table(runs: list[Run], labels: list[str]) -> list[list[str]]:
    def cell(run: Run, values: list[float]) -> str:
        return format_estimate(bootstrap(values, run[0]), 2)

    rows = [["Metric (mean [95% CI])", *labels]]
    getters = (
        ("Our final PnL", lambda r: [m.final_pnl for m in r[0].metrics]),
        ("Our Sharpe", lambda r: [m.sharpe for m in r[0].metrics]),
        ("Competitor final PnL", lambda r: [m.final_pnl for m in r[0].competitor_metrics]),
        ("Competitor Sharpe", lambda r: [m.sharpe for m in r[0].competitor_metrics]),
        ("Our % of maker volume", lambda r: maker_share(r[0])),
        ("Our mean volume share", lambda r: per_seed(r, "share")),
        ("Our mean effective base (ticks)", lambda r: per_seed(r, "effective_base")),
        ("Our mean half-spread (ticks)", lambda r: per_seed(r, "half_spread")),
    )
    for label, get in getters:
        rows.append([label, *(cell(run, get(run)) for run in runs)])
    return rows


def summary_table(names: tuple[str, ...], all_runs: list[dict[str, Run]]) -> list[list[str]]:
    """Mean Sharpe and Final PnL per agent and scenario, ✔ per SUMMARY_BASELINES."""
    rows = [
        [
            "Scenario",
            *(f"Sharpe {s}" for s, _ in SUMMARY_AGENTS),
            *(f"Final PnL {s}" for s, _ in SUMMARY_AGENTS),
        ]
    ]
    for scenario, runs in zip(names, all_runs, strict=True):
        cells = []
        for column in ("sharpe", "final_pnl"):
            for _, agent in SUMMARY_AGENTS:
                cell = f"{estimate(runs[agent][0], column).mean:.2f}"
                baseline = SUMMARY_BASELINES.get(agent)
                if baseline is not None:
                    diff = paired_estimate(runs[agent][0], runs[baseline][0], column)
                    if is_significant(diff):
                        cell += f" {SIGNIFICANT}"
                cells.append(cell)
        if scenario in V5_TRAINING:
            kind = ""
        elif scenario in TRAINING:
            kind = " (training for v6 only)"
        else:
            kind = " (unseen)"
        rows.append([scenario + kind, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds, competitive = config.evaluation.heldout_seeds, config.agent.competitive
    c = competitive.competition
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, every scenario in the "
        f"config, run once after `make sweep-competitive` froze [agent.competitive]: "
        f"base_half_spread = {competitive.final.base_half_spread}, d = "
        f"{c.undercut_per_share:g}, min_half_spread = {c.min_half_spread}, share_halflife = "
        f"{c.share_halflife:g} steps; every other knob is v5's. Training scenarios: "
        f"{', '.join(TRAINING)}; the rest are unseen. Money in price units."
    )
    note = (
        f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference from the column's "
        f"baseline on identical markets has a 95% CI that excludes 0. Baselines: "
        f"{baselines_note(COLUMNS)}; v2-tuned is unmarked."
    )
    names = scenario_names()
    war_specs = [(s, False) for s in WAR] + [(s, True) for s in WAR]
    with ProcessPoolExecutor() as pool:
        all_runs = list(pool.map(scenario_runs, names))
        dev = dict(zip(OVERFIT, pool.map(dev_worst_case, OVERFIT), strict=True))
        war = list(pool.map(war_run, war_specs))

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
        label = next(col.label for col in COLUMNS if col.agent == agent)
        held = min(estimate(runs[agent][0], "sharpe").mean for runs in training)
        overfit.append([label, f"{dev[agent]:.3f}", f"{held:.3f}", f"{held - dev[agent]:+.3f}"])

    d = DIAGNOSTIC
    war_labels = [f"v6 frozen, {s}" for s in WAR] + [f"diagnostic d > 0, {s}" for s in WAR]
    sections = ["# v6 competitive spread: held-out evaluation", intro, note]
    sections += [
        "## Overfitting check (training scenarios, worst case of the four mean Sharpes)",
        format_markdown(overfit),
        "## Undercutting-war check (vs_competitive is v6 self-play, unseen)",
        (
            f"Our agent and the competitor both run the config named in the column. The "
            f"diagnostic config is the dev sweep's best with d > 0 (d = "
            f"{d.undercut_per_share:g}, min = {d.min_half_spread}, half-life = "
            f"{d.share_halflife:g}, base = {DIAGNOSTIC_BASE}); it was not chosen and is shown "
            "only to see what undercutting does against v1 and against itself."
        ),
        format_markdown(war_table(war, war_labels)),
    ]
    for scenario, runs in zip(names, all_runs, strict=True):
        kind = "training" if scenario in TRAINING else "unseen"
        column_runs = [runs[col.agent] for col in COLUMNS]
        sections += [
            f"## {scenario} ({kind})",
            format_markdown(side_by_side(column_runs, COLUMNS, EXTRA)),
        ]
    write_with_interpretation(HELDOUT, "\n\n".join(sections))

    summary = [
        "# Results summary (held-out seeds)",
        (
            f"Mean over held-out seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps. "
            f"{SIGNIFICANT} on v5: its per-seed difference from v2-tuned has a 95% CI that "
            f"excludes 0; {SIGNIFICANT} on v6: the same against v5. Full tables with CIs: "
            "`docs/results/v5-final/heldout.md` and `docs/results/v6-competitive/heldout.md`."
        ),
        format_markdown(summary_table(names, all_runs)),
    ]
    SUMMARY.write_text("\n\n".join(summary) + "\n", encoding="utf-8")
    print(f"Wrote {HELDOUT} and {SUMMARY}")


if __name__ == "__main__":
    main()
