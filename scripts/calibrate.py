"""Estimate `[agent.kalman]` on the base scenario's dev seeds; print a TOML snippet and a check.

Run with `make calibrate`. The estimates use only the calibration agent's own observations.
The "true" column reads [market]: that is a simulation-only check of the estimates and never
feeds the agent.
"""

from mm.calibration import CalibrationResult, calibrate
from mm.config import MarketConfig, load_config
from mm.eval.report import format_console

SCENARIO = "base"
DECIMALS = 2  # committed values are rounded to this many places


def toml_snippet(result: CalibrationResult) -> str:
    values = {
        "sigma": result.sigma,
        "noise_rate": result.noise_rate,
        "mean_size": result.mean_size,
        "mean_size_sq": result.mean_size_sq,
        "k": result.k,
    }
    return "\n".join(f"{key} = {value:.{DECIMALS}f}" for key, value in values.items())


def true_values(market: MarketConfig) -> dict[str, float]:
    """The market's noise-taker model values (simulation-only check)."""
    sizes = range(market.noise.size_min, market.noise.size_max + 1)
    return {
        "sigma": market.true_value.sigma,
        "noise_rate": market.noise.rate,
        "mean_size": sum(sizes) / len(sizes),
        "mean_size_sq": sum(s * s for s in sizes) / len(sizes),
        "k": market.noise.tolerance_rate,
    }


def check_table(result: CalibrationResult, market: MarketConfig) -> list[list[str]]:
    rows = [["Parameter", "Estimated", "True (simulation-only check)"]]
    for key, true in true_values(market).items():
        rows.append([key, f"{getattr(result, key):.3f}", f"{true:.3f}"])
    return rows


def fill_rate_table(result: CalibrationResult) -> list[list[str]]:
    rows = [["Distance (ticks)", "Quotes", "Fills", "Mean fills per quote"]]
    for p in result.fill_rates:
        rows.append([str(p.distance), str(p.quotes), str(p.fills), f"{p.mean_fills:.4f}"])
    return rows


def main() -> None:
    config = load_config(scenario=SCENARIO)
    seeds = config.evaluation.dev_seeds
    result = calibrate(config, seeds, config.n_steps)
    print(f"Calibration: {SCENARIO}, dev seeds {seeds[0]}..{seeds[-1]}, {config.n_steps} steps")
    print(f"{result.n_fills} fills observed\n")
    print("[agent.kalman] (gain_scale unchanged)")
    print(toml_snippet(result))
    print()
    print(format_console(check_table(result, config.market)))
    print()
    print(format_console(fill_rate_table(result)))


if __name__ == "__main__":
    main()
