"""Command line for the evaluation: run, print the summary, write results/."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from mm.config import DEFAULT_CONFIG_PATH, load_config, scenario_names
from mm.eval.plots import write_plots
from mm.eval.report import (
    file_digest,
    format_console,
    header,
    summary_table,
    write_episodes_csv,
    write_report,
)
from mm.eval.runner import evaluate


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mm", description="Evaluate the v0 agent.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--seeds", choices=["dev", "heldout"], default="heldout")
    parser.add_argument(
        "--scenarios", nargs="+", help="default: every scenario in the config file"
    )
    parser.add_argument("--steps", type=int, help="default: simulation.n_steps in the config")
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument(
        "--digest", action="store_true", help="also print the SHA-256 of episodes.csv"
    )
    args = parser.parse_args(argv)

    known = scenario_names(args.config)
    if args.scenarios is None:
        args.scenarios = list(known)
    unknown = [name for name in args.scenarios if name not in known]
    if unknown:
        parser.error(f"unknown scenario {', '.join(unknown)}; known: {', '.join(known)}")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config(args.config)
    seeds = config.evaluation.dev_seeds if args.seeds == "dev" else config.evaluation.heldout_seeds
    n_steps = config.n_steps if args.steps is None else args.steps
    results = evaluate(args.scenarios, seeds, n_steps, args.config)

    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "episodes.csv"
    write_episodes_csv(results, csv_path)
    write_report(results, n_steps, args.out / "report.md")
    write_plots(results, args.out / "plots")

    print(f"v0 naive agent, {args.seeds} seeds: {header(results, n_steps)}")
    print(format_console(summary_table(results)))
    print(f"Wrote {csv_path}, {args.out / 'report.md'} and {args.out / 'plots'}/")
    if args.digest:
        print(f"episodes.csv sha256: {file_digest(csv_path)}")
