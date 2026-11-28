"""v2 (kalman) experiments on the development seeds; writes docs/results/v2-kalman/dev.md.

Run with `make v2-experiments`. Held-out seeds are never touched here. Three parts:
1. v1 (skew) vs v2 (kalman), with the theory-predicted fair-value error next to the measured one.
2. Gain sensitivity: gain_scale in {0.5, 1, 2}. A check only; the config keeps gain_scale = 1.
3. Robustness: the agent's k and lambda each set to 0.5x and 1.5x the market's, one at a time.
"""

from dataclasses import replace
from pathlib import Path

from mm.agent.kalman import symmetric_steady_state
from mm.config import KalmanConfig, load_config
from mm.eval.report import (
    PAIRED_NOTE,
    comparison_table,
    estimate,
    format_estimate,
    format_markdown,
    summary_table,
)
from mm.eval.runner import ScenarioResult, evaluate

SCENARIOS = ("base", "toxic")
N_STEPS = 2000
OUT = Path("docs/results/v2-kalman")
GAIN_SCALES = (0.5, 1.0, 2.0)
FACTORS = (0.5, 1.5)
CHECK_METRICS = (
    ("fair_value_rmse", "FV RMSE"),
    ("final_pnl", "Final PnL"),
    ("sharpe", "Sharpe"),
)


def run_kalman(kalman: KalmanConfig) -> list[ScenarioResult]:
    agent = replace(load_config().agent, type="kalman", kalman=kalman)
    return evaluate(SCENARIOS, load_config().evaluation.dev_seeds, N_STEPS, agent_config=agent)


def check_table(rows: list[tuple[str, list[ScenarioResult]]], first: str) -> list[list[str]]:
    """One row per setting; FV RMSE, final PnL and Sharpe for each scenario."""
    header = [first]
    for scenario in SCENARIOS:
        header += [f"{label} ({scenario})" for _, label in CHECK_METRICS]
    table = [header]
    for name, results in rows:
        cells = [
            format_estimate(estimate(result, column))
            for result in results
            for column, _ in CHECK_METRICS
        ]
        table.append([name, *cells])
    return table


def misspecified(
    kalman: KalmanConfig, market_fill_prob: float, market_rate: float
) -> list[tuple[str, KalmanConfig]]:
    # k = -ln(p) / 2, so scaling k by f means raising the calibration probability to the power f.
    settings = []
    for factor in FACTORS:
        settings.append(
            (f"k ×{factor:g}", replace(kalman, fill_prob_at_2_ticks=market_fill_prob**factor))
        )
    for factor in FACTORS:
        settings.append((f"λ ×{factor:g}", replace(kalman, noise_rate=market_rate * factor)))
    return settings


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    kalman = config.agent.kalman
    v1 = evaluate(SCENARIOS, seeds, N_STEPS, agent="skew")
    v2 = run_kalman(kalman)

    theory = symmetric_steady_state(kalman, config.agent.skew.half_spread)
    measured = ", ".join(
        f"{r.scenario} {format_estimate(estimate(r, 'fair_value_rmse'))}" for r in v2
    )
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {N_STEPS} steps. Mean [95% CI] over seeds; money in "
        "price units, fair-value error in ticks."
    )
    theory_line = (
        f"Constant symmetric quotes (half-spread {config.agent.skew.half_spread}, fv at the "
        f"centre): gain κ = {theory.gain:.3f} ticks per net lot, predicted fair-value error std "
        f"{theory.error_std:.2f} ticks (posterior; {theory.prior_variance**0.5:.2f} before the "
        f"update). Measured v2 fair-value RMSE: {measured}."
    )
    sections = [
        "# v2 kalman: experiments on development seeds",
        intro,
        "## Theory check",
        theory_line,
        "## v1 (skew) vs v2 (kalman)",
        "### Summary: skew",
        format_markdown(summary_table(v1)),
        "### Summary: kalman",
        format_markdown(summary_table(v2)),
    ]
    for agent_result, baseline in zip(v2, v1, strict=True):
        sections += [
            f"### kalman − skew: {agent_result.scenario}",
            PAIRED_NOTE,
            format_markdown(comparison_table(agent_result, baseline)),
        ]

    sensitivity = [
        (f"{g:g}", v2 if g == kalman.gain_scale else run_kalman(replace(kalman, gain_scale=g)))
        for g in GAIN_SCALES
    ]
    sections += [
        "## Gain sensitivity (check only; config keeps gain_scale = 1)",
        format_markdown(check_table(sensitivity, "gain_scale")),
    ]

    noise = config.market.noise
    robustness = [("correct", v2)] + [
        (name, run_kalman(setting))
        for name, setting in misspecified(kalman, noise.fill_prob_at_2_ticks, noise.rate)
    ]
    sections += [
        "## Robustness: misspecified agent assumptions (one at a time, vs the market's k and λ)",
        format_markdown(check_table(robustness, "Agent assumption")),
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev.md'}")


if __name__ == "__main__":
    main()
