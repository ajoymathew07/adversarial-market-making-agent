"""Tune v4 (adaptive) on dev seeds; writes docs/results/v4-adaptive/dev-sweep.md.

Run with `make sweep-adaptive`. Held-out seeds are never touched here. Grid: base half-spread
in BASES × uncertainty weight a in WEIGHTS × intensity half-life in HALFLIVES (0 = off), 36
configs. Objective: the worst case (lowest mean Sharpe) over the training scenarios; ties go
to the first config in grid order. The control (v2 with half-spread 4, `kalman_tuned`) is the
grid point (4, 0, off), so the base spread is tuned in the same sweep. The winner goes into
[agent.adaptive] by hand.

Detection (dev, before held-out): in bursty_takers, does ρ follow the market's busy/calm regime?
The regime path is regenerated here from the episode seed exactly as `run_episode` draws it;
it is evaluation-only and the agent never sees it. Then fair-value RMSE against the control in
bursty_takers and realistic_mix. Finally a diagnostic, not a candidate: the control with its
calibrated noise rate λ multiplied by a constant, to separate "ρ corrects the level of λ" from
"ρ tracks changes in λ".
"""

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, replace
from itertools import product
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from mm.config import AgentConfig, SimConfig, load_config
from mm.eval.compare import is_significant, paired_estimate
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import SIGNIFICANT, estimate, format_estimate, format_markdown
from mm.eval.runner import ScenarioResult, evaluate
from mm.eval.stats import bootstrap_ci
from mm.market import generate_noise_rate_scale, generate_value_path

SCENARIOS = ("no_informed", "base", "toxic")
BASES = (3, 4, 5)
WEIGHTS = (0.0, 0.5, 1.0, 2.0)
HALFLIVES = (0.0, 20.0, 100.0)  # steps; 0 = off
DETECTION_SCENARIO = "bursty_takers"
RMSE_SCENARIOS = ("bursty_takers", "realistic_mix")
OUT = Path("docs/results/v4-adaptive")
LAMBDA_FACTORS = (0.6, 0.7, 0.8, 0.9, 1.0)  # diagnostic only
CHOSEN = "◀ chosen"
CONTROL = "◀ control"


@dataclass(frozen=True)
class Setting:
    base: int
    weight: float
    halflife: float

    def agent(self) -> AgentConfig:
        base = load_config().agent
        adaptive = replace(
            base.adaptive,
            base_half_spread=self.base,
            uncertainty_weight=self.weight,
            intensity_halflife=self.halflife,
        )
        return replace(base, type="adaptive", adaptive=adaptive)

    def label(self) -> str:
        halflife = "off" if self.halflife == 0 else f"{self.halflife:g}"
        return f"base = {self.base}, a = {self.weight:g}, intensity_halflife = {halflife}"


CONTROL_SETTING = Setting(4, 0.0, 0.0)


@dataclass(frozen=True)
class Row:
    setting: Setting
    sharpes: tuple[str, ...]  # formatted mean [95% CI] per training scenario
    worst: float  # lowest mean Sharpe of the training scenarios


def run(setting: Setting, scenarios: tuple[str, ...] = SCENARIOS) -> list[ScenarioResult]:
    config = load_config()
    return evaluate(
        scenarios, config.evaluation.dev_seeds, config.n_steps, agent_config=setting.agent()
    )


def score(setting: Setting) -> Row:
    sharpes = [estimate(r, "sharpe") for r in run(setting)]
    return Row(setting, tuple(format_estimate(s) for s in sharpes), min(s.mean for s in sharpes))


def score_constant_lambda(factor: float) -> Row:
    """The control with [agent.kalman] noise_rate × factor (diagnostic only)."""
    base = CONTROL_SETTING.agent()
    kalman = replace(base.kalman, noise_rate=base.kalman.noise_rate * factor)
    config = load_config()
    results = evaluate(
        SCENARIOS,
        config.evaluation.dev_seeds,
        config.n_steps,
        agent_config=replace(base, kalman=kalman),
    )
    sharpes = [estimate(r, "sharpe") for r in results]
    cells = tuple(format_estimate(s) for s in sharpes)
    return Row(CONTROL_SETTING, cells, min(s.mean for s in sharpes))


def mean_quotes(setting: Setting) -> list[list[str]]:
    """Mean ρ and mean half-spread per training scenario, dev seeds."""
    config = load_config()
    settings = config.evaluation
    rows = [["Scenario", "Mean ρ", "Mean half-spread (ticks)"]]
    for scenario in SCENARIOS:
        recorder = EpisodeRecorder()
        evaluate(
            [scenario],
            settings.dev_seeds,
            config.n_steps,
            agent_config=setting.agent(),
            agent_factory=recorder.factory,
        )
        cells = [
            format_estimate(
                bootstrap_ci(v, settings.bootstrap_resamples, settings.bootstrap_seed), 3
            )
            if v
            else "— (off)"
            for v in (recorder.mean_intensity(), recorder.mean_half_spread())
        ]
        rows.append([scenario, *cells])
    return rows


def best(rows: list[Row]) -> Row:
    return max(rows, key=lambda r: (r.worst, -rows.index(r)))


def busy_path(config: SimConfig) -> NDArray[np.bool_]:
    """The market's busy steps for this episode, drawn exactly as run_episode draws them."""
    rng = np.random.Generator(np.random.PCG64(config.seed))
    generate_value_path(config.market, config.instrument.initial_price_ticks, config.n_steps, rng)
    scale = generate_noise_rate_scale(config.market.noise, config.n_steps, rng)
    return np.asarray(scale > 1.0)


def detection(setting: Setting) -> list[list[str]]:
    """Mean ρ in busy vs calm steps of bursty_takers, and their correlation."""
    config = load_config(scenario=DETECTION_SCENARIO)
    settings = config.evaluation
    recorder = EpisodeRecorder()
    evaluate(
        [DETECTION_SCENARIO],
        settings.dev_seeds,
        config.n_steps,
        agent_config=setting.agent(),
        agent_factory=recorder.factory,
    )
    busy_means, calm_means, corrs = [], [], []
    all_rho: list[float] = []
    all_busy: list[bool] = []
    for seed, episode in zip(settings.dev_seeds, recorder.episodes, strict=True):
        busy = busy_path(replace(config, seed=seed))
        rho = np.asarray(episode.intensity)
        busy_means.append(float(rho[busy].mean()))
        calm_means.append(float(rho[~busy].mean()))
        corrs.append(float(np.corrcoef(rho, busy)[0, 1]))
        all_rho += list(rho)
        all_busy += list(busy)

    def ci(values: list[float]) -> str:
        est = bootstrap_ci(values, settings.bootstrap_resamples, settings.bootstrap_seed)
        return format_estimate(est, 3)

    pooled = float(np.corrcoef(all_rho, all_busy)[0, 1])
    true_ratio = config.market.noise.busy_rate_scale / config.market.noise.calm_rate_scale
    gaps = [b - c for b, c in zip(busy_means, calm_means, strict=True)]
    return [
        ["Quantity (dev seeds, per-episode mean [95% CI])", "Value"],
        ["Mean ρ in busy steps", ci(busy_means)],
        ["Mean ρ in calm steps", ci(calm_means)],
        ["Busy − calm (per episode)", ci(gaps)],
        ["corr(ρ_t, busy_t) within an episode", ci(corrs)],
        ["corr(ρ_t, busy_t) pooled over all steps", f"{pooled:.3f}"],
        ["True busy / calm noise rate (market side)", f"{true_ratio:g}"],
    ]


def rmse_table(settings: list[tuple[str, Setting]]) -> list[list[str]]:
    """Fair-value RMSE per scenario; each non-control column marked against the control."""
    rows = [["Scenario", *(name for name, _ in settings)]]
    runs = [run(s, RMSE_SCENARIOS) for _, s in settings]
    for i, scenario in enumerate(RMSE_SCENARIOS):
        control = runs[0][i]
        cells = [format_estimate(estimate(control, "fair_value_rmse"), 3)]
        for r in runs[1:]:
            cell = format_estimate(estimate(r[i], "fair_value_rmse"), 3)
            if is_significant(paired_estimate(r[i], control, "fair_value_rmse")):
                cell += f" {SIGNIFICANT}"
            cells.append(cell)
        rows.append([scenario, *cells])
    return rows


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    grid = [Setting(b, a, h) for b, a, h in product(BASES, WEIGHTS, HALFLIVES)]
    with ProcessPoolExecutor() as pool:
        rows = list(pool.map(score, grid))
        constant_rows = list(pool.map(score_constant_lambda, LAMBDA_FACTORS))
    chosen = best(rows)
    control = next(r for r in rows if r.setting == CONTROL_SETTING)
    margin = chosen.worst - control.worst
    print(f"v4 best: {chosen.setting.label()}, worst-case Sharpe {chosen.worst:.3f}")
    print(f"control: worst-case Sharpe {control.worst:.3f}; margin {margin:+.3f}")

    sharpe_cols = [f"Sharpe {s}" for s in SCENARIOS]
    table = [["Base", "a", "Half-life", *sharpe_cols, "Worst case", ""]]
    for r in rows:
        s = r.setting
        mark = CHOSEN if r is chosen else (CONTROL if r is control else "")
        halflife = "off" if s.halflife == 0 else f"{s.halflife:g}"
        table.append(
            [str(s.base), f"{s.weight:g}", halflife, *r.sharpes, f"{r.worst:.2f}", mark]
        )
    feature_table = [["Feature setting", "Best worst-case Sharpe", "Best config"]]
    for intensity_on, weighted in product((False, True), (False, True)):
        r = best(
            [
                row
                for row in rows
                if (row.setting.halflife > 0) == intensity_on
                and (row.setting.weight > 0) == weighted
            ]
        )
        name = f"intensity {'on' if intensity_on else 'off'}, a {'>' if weighted else '='} 0"
        feature_table.append([name, f"{r.worst:.3f}", r.setting.label()])

    # Detection needs ρ, so use the chosen config if its intensity is on, else the best that is.
    on = chosen
    if chosen.setting.halflife == 0:
        on = best([r for r in rows if r.setting.halflife > 0])
    rmse_columns = [("control (v2-tuned)", CONTROL_SETTING), ("v4 chosen", chosen.setting)]
    if on is not chosen:
        rmse_columns.append(("v4 best with intensity on", on.setting))
    constant_table = [["λ factor", *sharpe_cols, "Worst case"]]
    for factor, r in zip(LAMBDA_FACTORS, constant_rows, strict=True):
        constant_table.append([f"{factor:g}", *r.sharpes, f"{r.worst:.2f}"])
    adaptive = config.agent.adaptive
    verdict = "yes" if margin > 0 else "no"
    sections = [
        "# v4 adaptive: dev sweep against the tuned control",
        (
            f"Dev seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps, training scenarios "
            f"{', '.join(SCENARIOS)}. Mean Sharpe [95% CI] over seeds. Objective: the worst case "
            "(lowest mean Sharpe) of the three; ties go to the first config in grid order. "
            f"Fixed (untuned choices): min_scale = {adaptive.min_scale:g}, max_scale = "
            f"{adaptive.max_scale:g}, max_half_spread = {adaptive.max_half_spread}; skew_per_lot "
            f"and quote_size from [agent.skew]. The control is the grid point "
            f"({CONTROL_SETTING.label()}), which quotes exactly as kalman_tuned."
        ),
        "## Verdict",
        (
            f"Does v4 beat the tuned control? **{verdict}**. Best worst-case Sharpe: "
            f"{chosen.worst:.3f} ({chosen.setting.label()}) against the control's "
            f"{control.worst:.3f}, a margin of {margin:+.3f}."
        ),
        "## Best per feature combination",
        format_markdown(feature_table),
        f"## What the chosen config quotes (dev, {', '.join(SCENARIOS)})",
        format_markdown(mean_quotes(chosen.setting)),
        "## Diagnostic: the control with a constant λ factor (not a candidate)",
        (
            "If a constant factor on the calibrated noise rate matches v4, ρ's gain comes from "
            "correcting the level of λ, not from tracking how it changes."
        ),
        format_markdown(constant_table),
        f"## Detection: does ρ track the busy/calm regime in {DETECTION_SCENARIO}?",
        (
            f"Config: {on.setting.label()}. ρ_t is the agent's intensity after its quote at step "
            "t; busy_t is the market's regime for the takers that arrive after that quote "
            "(evaluation only). corr is the Pearson correlation of ρ_t with the 0/1 busy flag."
        ),
        format_markdown(detection(on.setting)),
        "## Fair-value RMSE against the control (ticks, dev seeds)",
        (
            f"Mean [95% CI] over seeds. {SIGNIFICANT}: the per-seed difference from the control "
            "has a 95% CI that excludes 0."
        ),
        format_markdown(rmse_table(rmse_columns)),
        "## Full grid",
        format_markdown(table),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev-sweep.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev-sweep.md'}")


if __name__ == "__main__":
    main()
