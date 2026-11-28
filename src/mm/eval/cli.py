"""Command line: evaluate each agent, print summaries and comparisons, write results/."""

import argparse
from collections.abc import Sequence
from pathlib import Path

from mm.agent import AGENT_NAMES
from mm.config import DEFAULT_CONFIG_PATH, load_config, scenario_names
from mm.eval.compare import pairs
from mm.eval.plots import write_plots
from mm.eval.report import (
    PAIRED_NOTE,
    comparison_table,
    comparison_title,
    file_digest,
    format_console,
    header,
    summary_table,
    write_episodes_csv,
    write_report,
)
from mm.eval.runner import evaluate


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="mm", description="Evaluate market-making agents.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--agents",
        help="comma-separated agent names, the first is the baseline; default: [agent] type",
    )
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

    if args.agents is None:
        args.agents = [load_config(args.config).agent.type]
    else:
        args.agents = args.agents.split(",")
    unknown = [name for name in args.agents if name not in AGENT_NAMES]
    if unknown:
        parser.error(f"unknown agent {', '.join(unknown)}; known: {', '.join(AGENT_NAMES)}")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    config = load_config(args.config)
    seeds = config.evaluation.dev_seeds if args.seeds == "dev" else config.evaluation.heldout_seeds
    n_steps = config.n_steps if args.steps is None else args.steps
    runs = [evaluate(args.scenarios, seeds, n_steps, args.config, agent) for agent in args.agents]

    args.out.mkdir(parents=True, exist_ok=True)
    csv_path = args.out / "episodes.csv"
    write_episodes_csv([result for results in runs for result in results], csv_path)
    write_report(runs, n_steps, args.out / "report.md")
    write_plots(runs[0], args.out / "plots")

    for results in runs:
        print(f"Agent {results[0].agent}, {args.seeds} seeds: {header(results, n_steps)}")
        print(format_console(summary_table(results)))
        print()
    for agent, baseline in pairs(runs):
        print(f"{comparison_title(agent, baseline)}. {PAIRED_NOTE}")
        print(format_console(comparison_table(agent, baseline)))
        print()
    print(f"Wrote {csv_path}, {args.out / 'report.md'} and {args.out / 'plots'}/")
    if args.digest:
        print(f"episodes.csv sha256: {file_digest(csv_path)}")
