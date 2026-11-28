"""v1 | v2 | v2-tuned | v3 on every scenario, held-out seeds; writes docs/results/v3-toxicity/heldout.md.

Run with `make v3-experiments`, once, after `make sweep-toxicity` froze [agent.kalman_tuned] and
[agent.toxicity]. Every agent uses `config/default.toml` as is. ✔ is paired per seed on identical
markets against each column's baseline (BASELINES). The ## Interpretation section is
hand-written and kept across reruns.
"""

from pathlib import Path

from mm.config import load_config, scenario_names
from mm.eval.compare import is_significant, paired_estimate
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import (
    SIGNIFICANT,
    SUMMARY_METRICS,
    decimals_for,
    estimate,
    format_estimate,
    format_markdown,
)
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import Estimate, bootstrap_ci

TRAINING = ("no_informed", "base", "toxic")
# (column label, registry name, index of the column it is marked against, or None)
AGENTS = (
    ("v1 (skew)", "skew", None),
    ("v2 (kalman)", "kalman", 0),
    ("v2-tuned (control)", "kalman_tuned", 1),
    ("v3 (toxicity)", "toxicity", 2),
)
OUT = Path("docs/results/v3-toxicity")
INTERPRETATION_HEADING = "## Interpretation"
EXTRA = (
    ("lots_informed", "Informed lots filled / episode"),
    ("lots_noise", "Noise lots filled / episode"),
    ("half_spread", "Mean half-spread (ticks)"),
    ("toxicity", "Mean toxicity T (ticks)"),
)

Run = tuple[ScenarioResult, EpisodeRecorder]


def run_agent(name: str, scenario: str, seeds: tuple[int, ...], n_steps: int) -> Run:
    recorder = EpisodeRecorder()
    (result,) = evaluate([scenario], seeds, n_steps, agent=name, agent_factory=recorder.factory)
    return result, recorder


def per_seed(run: Run, key: str) -> list[float]:
    result, recorder = run
    if key == "half_spread":
        return recorder.mean_half_spread()
    if key == "toxicity":
        return recorder.mean_toxicity()
    return [m.as_row()[key] for m in result.metrics]


def bootstrap(values: list[float], result: ScenarioResult) -> Estimate:
    settings = result.config.evaluation
    return bootstrap_ci(values, settings.bootstrap_resamples, settings.bootstrap_seed)


def scenario_table(runs: list[Run]) -> list[list[str]]:
    """One column per agent; each marked against its baseline column."""
    rows = [["Metric (mean [95% CI])", *(label for label, _, _ in AGENTS)]]
    for column, label in SUMMARY_METRICS:
        cells = [format_estimate(estimate(r, column), decimals_for(column)) for r, _ in runs]
        for i, (_, _, baseline) in enumerate(AGENTS):
            if baseline is not None:
                diff = paired_estimate(runs[i][0], runs[baseline][0], column)
                if is_significant(diff):
                    cells[i] += f" {SIGNIFICANT}"
        rows.append([label, *cells])
    for key, label in EXTRA:
        values = [per_seed(run, key) for run in runs]
        cells = [
            format_estimate(bootstrap(v, run[0])) if v else "—"
            for v, run in zip(values, runs, strict=True)
        ]
        for i, (_, _, baseline) in enumerate(AGENTS):
            if baseline is not None and values[i] and values[baseline]:
                deltas = [a - b for a, b in zip(values[i], values[baseline], strict=True)]
                if is_significant(bootstrap(deltas, runs[i][0])):
                    cells[i] += f" {SIGNIFICANT}"
        rows.append([label, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    tox, tuned = config.agent.toxicity, config.agent.kalman_tuned
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {n_steps} steps, every scenario in the config. "
        f"Frozen from the dev sweep: v2-tuned half_spread = {tuned.half_spread}; v3 "
        f"base_half_spread = {tox.base_half_spread}, markout_horizon = {tox.markout_horizon}, "
        f"widen_per_tick = {tox.widen_per_tick:g}, ewma_halflife = {tox.ewma_halflife:g} lots, "
        f"max_half_spread = {tox.max_half_spread}. v1 and v2 keep [agent.skew] half_spread = "
        f"{config.agent.skew.half_spread}. Training scenarios (used by the sweep): "
        f"{', '.join(TRAINING)}; the rest are unseen. Money in price units; fair-value error, "
        "half-spread and T in ticks."
    )
    baselines = "; ".join(
        f"{label} against {AGENTS[b][0]}" for label, _, b in AGENTS if b is not None
    )
    note = (
        f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference from the column's "
        f"baseline on identical markets has a 95% CI that excludes 0. Baselines: {baselines}; "
        "v1 is unmarked. T is v3's own score, averaged over each episode's steps."
    )
    detection = [["Scenario", "Mean T, v3 (ticks)", "Mean half-spread, v3 (ticks)"]]
    sections = ["# v3 toxicity: held-out evaluation", intro, note]
    tables: list[str] = []
    for scenario in scenario_names():
        runs = [run_agent(name, scenario, seeds, n_steps) for _, name, _ in AGENTS]
        v3 = runs[-1]
        detection.append(
            [
                scenario,
                format_estimate(bootstrap(per_seed(v3, "toxicity"), v3[0])),
                format_estimate(bootstrap(per_seed(v3, "half_spread"), v3[0])),
            ]
        )
        kind = "training" if scenario in TRAINING else "unseen"
        tables += [f"## {scenario} ({kind})", format_markdown(scenario_table(runs))]
        print(f"done {scenario}")
    sections += ["## Detection: v3's toxicity score by scenario", format_markdown(detection)]
    sections += tables
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "heldout.md"
    path.write_text("\n\n".join(sections) + "\n" + _kept_interpretation(path), encoding="utf-8")
    print(f"Wrote {path}")


def _kept_interpretation(path: Path) -> str:
    """The hand-written section from INTERPRETATION_HEADING on, kept across reruns."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    at = text.find(INTERPRETATION_HEADING)
    return "\n" + text[at:] if at >= 0 else f"\n{INTERPRETATION_HEADING}\n\nTBD\n"


if __name__ == "__main__":
    main()
