"""v2 (kalman) experiments on the development seeds; writes docs/results/v2-kalman/dev.md.

Run with `make v2-experiments`. Held-out seeds are never touched here. Three parts:
1. v1 (skew) vs v2 (kalman, calibrated), side by side, with the old oracle parameters (the
   market's true values, a leak) as a reference column only.
2. Gain sensitivity: gain_scale in {0.5, 1, 2}. A check only; the config keeps gain_scale = 1.
3. Robustness: the calibrated k and lambda each scaled by 0.5 and 1.5, one at a time.
"""

from dataclasses import replace
from pathlib import Path

from mm.agent.kalman import symmetric_steady_state
from mm.config import KalmanConfig, MarketConfig, load_config, scenario_names
from mm.eval.report import (
    SIDE_BY_SIDE_NOTE,
    estimate,
    format_estimate,
    format_markdown,
    side_by_side_table,
)
from mm.eval.runner import ScenarioResult, evaluate

SCENARIOS = scenario_names()
N_STEPS = 2000
OUT = Path("docs/results/v2-kalman")
GAIN_SCALES = (0.5, 1.0, 2.0)
FACTORS = (0.5, 1.5)
CHECK_METRICS = (
    ("fair_value_rmse", "FV RMSE"),
    ("final_pnl", "Final PnL"),
    ("sharpe", "Sharpe"),
)
V1, V2, ORACLE = "v1 (skew)", "v2 (kalman, calibrated)", "oracle (leaked, for reference only)"


def run_kalman(kalman: KalmanConfig) -> list[ScenarioResult]:
    agent = replace(load_config().agent, type="kalman", kalman=kalman)
    return evaluate(SCENARIOS, load_config().evaluation.dev_seeds, N_STEPS, agent_config=agent)


def oracle_kalman(market: MarketConfig, gain_scale: float) -> KalmanConfig:
    """The market's own noise-taker values: what [agent.kalman] used before calibration."""
    sizes = range(market.noise.size_min, market.noise.size_max + 1)
    return KalmanConfig(
        sigma=market.true_value.sigma,
        noise_rate=market.noise.rate,
        mean_size=sum(sizes) / len(sizes),
        mean_size_sq=sum(s * s for s in sizes) / len(sizes),
        k=market.noise.tolerance_rate,
        gain_scale=gain_scale,
    )


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


def misspecified(kalman: KalmanConfig) -> list[tuple[str, KalmanConfig]]:
    settings = [(f"k ×{f:g}", replace(kalman, k=kalman.k * f)) for f in FACTORS]
    settings += [(f"λ ×{f:g}", replace(kalman, noise_rate=kalman.noise_rate * f)) for f in FACTORS]
    return settings


def main() -> None:
    config = load_config()
    seeds = config.evaluation.dev_seeds
    kalman = config.agent.kalman
    v1 = evaluate(SCENARIOS, seeds, N_STEPS, agent="skew")
    v2 = run_kalman(kalman)
    oracle = run_kalman(oracle_kalman(config.market, kalman.gain_scale))

    theory = symmetric_steady_state(kalman, config.agent.skew.half_spread)
    measured = ", ".join(
        f"{r.scenario} {format_estimate(estimate(r, 'fair_value_rmse'))}" for r in v2
    )
    intro = (
        f"Dev seeds {seeds[0]}..{seeds[-1]}, {N_STEPS} steps. Money in price units, fair-value "
        "error in ticks. v2 uses the calibrated `[agent.kalman]` (docs/results/calibration.md). "
        "The oracle column uses the market's true parameters, which the agent must not know; it "
        "is shown for reference only."
    )
    theory_line = (
        f"Calibrated parameters, constant symmetric quotes (half-spread "
        f"{config.agent.skew.half_spread}, fv at the centre): gain κ = {theory.gain:.3f} ticks "
        f"per net lot, predicted fair-value error std {theory.error_std:.2f} ticks (posterior; "
        f"{theory.prior_variance**0.5:.2f} before the update). Measured v2 fair-value RMSE: "
        f"{measured}."
    )
    sections = [
        "# v2 kalman: experiments on development seeds",
        intro,
        "## Theory check",
        theory_line,
        "## v1 (skew) vs v2 (kalman, calibrated)",
        SIDE_BY_SIDE_NOTE + " The oracle column is not marked.",
    ]
    for skew_result, kalman_result, oracle_result in zip(v1, v2, oracle, strict=True):
        table = side_by_side_table(
            (V1, skew_result), (V2, kalman_result), [(ORACLE, oracle_result)]
        )
        sections += [f"### {skew_result.scenario}", format_markdown(table)]

    sensitivity = [
        (f"{g:g}", v2 if g == kalman.gain_scale else run_kalman(replace(kalman, gain_scale=g)))
        for g in GAIN_SCALES
    ]
    sections += [
        "## Gain sensitivity (check only; config keeps gain_scale = 1)",
        format_markdown(check_table(sensitivity, "gain_scale")),
    ]

    robustness = [("calibrated", v2)] + [
        (name, run_kalman(setting)) for name, setting in misspecified(kalman)
    ]
    sections += [
        "## Robustness: calibrated k and λ scaled one at a time",
        format_markdown(check_table(robustness, "Agent assumption")),
    ]

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dev.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print(f"Wrote {OUT / 'dev.md'}")


if __name__ == "__main__":
    main()
