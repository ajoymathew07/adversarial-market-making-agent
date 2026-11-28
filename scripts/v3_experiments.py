"""v1 | v2 | v3 on every scenario, held-out seeds; writes docs/results/v3-toxicity/heldout.md.

Run with `make v3-experiments`, once, after `make sweep-toxicity` froze [agent.toxicity]. Every
agent uses `config/default.toml` as is. ✔ marks v2 against v1 and v3 against v2 (paired per seed
on identical markets). The ## Interpretation section is hand-written and kept across reruns.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from mm.agent import Agent, Observation, Quote, ToxicityMarketMaker, make_agent
from mm.config import SimConfig, load_config, scenario_names
from mm.eval.compare import is_significant, paired_estimate
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
AGENTS = (("v1 (skew)", "skew"), ("v2 (kalman)", "kalman"), ("v3 (toxicity)", "toxicity"))
OUT = Path("docs/results/v3-toxicity")
INTERPRETATION_HEADING = "## Interpretation"
# Extra per-episode values: (key, label). Lots come from the metrics, the rest from the recorder.
LOTS = (
    ("lots_informed", "Informed lots filled / episode"),
    ("lots_noise", "Noise lots filled / episode"),
)
RECORDED = (("half_spread", "Mean half-spread (ticks)"), ("toxicity", "Mean toxicity T (ticks)"))


@dataclass
class Recorded:
    """Per-episode means of what the agent quoted, in seed order."""

    half_spread: list[float] = field(default_factory=list)
    toxicity: list[float] = field(default_factory=list)  # v3 only


class Recorder:
    """Wraps an agent and records its half-spread and, for v3, its toxicity score each step."""

    def __init__(self, inner: Agent) -> None:
        self.inner = inner
        self.half_spreads: list[float] = []
        self.scores: list[float] = []

    def quote(self, obs: Observation) -> Quote:
        quote = self.inner.quote(obs)
        if quote.bid_price is not None and quote.ask_price is not None:
            self.half_spreads.append((quote.ask_price - quote.bid_price) / 2)
        if isinstance(self.inner, ToxicityMarketMaker):
            self.scores.append(self.inner.toxicity)
        return quote


def recording_factory(record: Recorded) -> tuple[Callable[[SimConfig], Agent], Callable[[], None]]:
    """An agent factory for `evaluate`, and a flush that stores the last episode's means."""
    current: list[Recorder] = []

    def flush() -> None:
        if current:
            done = current.pop()
            record.half_spread.append(sum(done.half_spreads) / len(done.half_spreads))
            if done.scores:
                record.toxicity.append(sum(done.scores) / len(done.scores))

    def factory(config: SimConfig) -> Agent:
        flush()
        current.append(Recorder(make_agent(config)))
        return current[-1]

    return factory, flush


def run_agent(
    name: str, scenario: str, seeds: tuple[int, ...], n_steps: int
) -> tuple[ScenarioResult, Recorded]:
    record = Recorded()
    factory, flush = recording_factory(record)
    (result,) = evaluate([scenario], seeds, n_steps, agent=name, agent_factory=factory)
    flush()
    return result, record


def per_seed(result: ScenarioResult, record: Recorded, key: str) -> list[float]:
    if key.startswith("lots_"):
        return [m.as_row()[key] for m in result.metrics]
    return list(getattr(record, key))


def bootstrap(values: list[float], result: ScenarioResult) -> Estimate:
    settings = result.config.evaluation
    return bootstrap_ci(values, settings.bootstrap_resamples, settings.bootstrap_seed)


def scenario_table(runs: list[tuple[ScenarioResult, Recorded]]) -> list[list[str]]:
    """Columns v1 | v2 | v3; v2 marked vs v1, v3 marked vs v2."""
    rows = [["Metric (mean [95% CI])", *(label for label, _ in AGENTS)]]
    for column, label in SUMMARY_METRICS:
        cells = [format_estimate(estimate(r, column), decimals_for(column)) for r, _ in runs]
        for i in (1, 2):
            if is_significant(paired_estimate(runs[i][0], runs[i - 1][0], column)):
                cells[i] += f" {SIGNIFICANT}"
        rows.append([label, *cells])
    for key, label in (*LOTS, *RECORDED):
        values = [per_seed(r, rec, key) for r, rec in runs]
        cells = [
            format_estimate(bootstrap(v, r)) if v else "—"
            for v, (r, _) in zip(values, runs, strict=True)
        ]
        for i in (1, 2):
            if values[i] and values[i - 1]:
                diff = [a - b for a, b in zip(values[i], values[i - 1], strict=True)]
                if is_significant(bootstrap(diff, runs[i][0])):
                    cells[i] += f" {SIGNIFICANT}"
        rows.append([label, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds, n_steps = config.evaluation.heldout_seeds, config.n_steps
    tox = config.agent.toxicity
    scenarios = scenario_names()
    intro = (
        f"Held-out seeds {seeds[0]}..{seeds[-1]}, {n_steps} steps, every scenario in the config. "
        f"v3 frozen from the dev sweep: markout_horizon = {tox.markout_horizon}, widen_per_tick = "
        f"{tox.widen_per_tick:g}, ewma_halflife = {tox.ewma_halflife:g} lots, max_half_spread = "
        f"{tox.max_half_spread}. Training scenarios (used by the sweep): {', '.join(TRAINING)}; "
        "the rest are unseen. Money in price units, fair-value error, half-spread and T in ticks."
    )
    note = (
        f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference on identical markets has "
        "a 95% CI that excludes 0, against v1 for v2's column and against v2 for v3's column. "
        "Toxicity T is v3's own score, averaged over the steps of each episode."
    )
    detection = [["Scenario", "Mean T, v3 (ticks)", "Mean half-spread, v3 (ticks)"]]
    sections = ["# v3 toxicity: held-out evaluation", intro, note]
    tables: list[str] = []
    for scenario in scenarios:
        runs = [run_agent(name, scenario, seeds, n_steps) for _, name in AGENTS]
        v3_result, v3_record = runs[2]
        detection.append(
            [
                scenario,
                format_estimate(bootstrap(v3_record.toxicity, v3_result)),
                format_estimate(bootstrap(v3_record.half_spread, v3_result)),
            ]
        )
        kind = "training" if scenario in TRAINING else "unseen"
        tables += [f"## {scenario} ({kind})", format_markdown(scenario_table(runs))]
        print(f"done {scenario}")
    sections += [
        "## Detection: v3's toxicity score by scenario",
        format_markdown(detection),
        *tables,
    ]
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
