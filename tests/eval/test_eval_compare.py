import math
from dataclasses import replace

import pytest

import mm.simulation
from mm.agent import Observation, Quote
from mm.config import load_config
from mm.eval.cli import main
from mm.eval.compare import (
    COMPARE_METRICS,
    is_significant,
    paired_differences,
    paired_estimate,
    pairs,
)
from mm.eval.report import comparison_table, file_digest
from mm.eval.runner import evaluate
from mm.eval.stats import Estimate
from mm.market import generate_intents
from mm.market.takers import TakerIntent
from mm.simulation import run_episode

SEEDS = [0, 1, 2]
STEPS = 100


@pytest.fixture(scope="module")
def base_run():
    return evaluate(["base"], SEEDS, STEPS)[0]


def with_pnl(result, values):
    return replace(
        result, metrics=[replace(m, final_pnl=v) for m, v in zip(result.metrics, values)]
    )


def test_agent_compared_with_itself_has_zero_differences_and_zero_width_cis(base_run):
    for column, _ in COMPARE_METRICS:
        diffs = paired_differences(base_run, base_run, column)
        assert all(d == 0 or math.isnan(d) for d in diffs)
        est = paired_estimate(base_run, base_run, column)
        if not math.isnan(est.mean):
            assert est == Estimate(0.0, 0.0, 0.0)
            assert not is_significant(est)


def test_paired_differences_match_hand_computed_mean(base_run):
    agent = with_pnl(base_run, [5.0, 1.0, 3.0])
    baseline = with_pnl(base_run, [2.0, 2.0, 0.5])
    assert paired_differences(agent, baseline, "final_pnl") == [3.0, -1.0, 2.5]
    assert paired_estimate(agent, baseline, "final_pnl").mean == pytest.approx(4.5 / 3)


def test_constant_positive_difference_is_significant(base_run):
    agent = with_pnl(base_run, [3.0, 4.0, 5.0])
    baseline = with_pnl(base_run, [1.0, 2.0, 3.0])
    est = paired_estimate(agent, baseline, "final_pnl")
    assert est == Estimate(2.0, 2.0, 2.0)
    assert is_significant(est)
    row = {r[0]: r[2] for r in comparison_table(agent, baseline)}
    assert row["Final PnL"] == "yes"


def test_nan_estimate_is_not_significant():
    assert not is_significant(Estimate(math.nan, math.nan, math.nan))


def test_pairing_needs_the_same_seeds(base_run):
    other = replace(base_run, seeds=(5, 6, 7))
    with pytest.raises(ValueError, match="same scenario and seeds"):
        paired_differences(other, base_run, "final_pnl")


def test_pairs_use_the_first_run_as_baseline(base_run):
    first, second = [base_run], [replace(base_run, agent="other")]
    assert pairs([first, second]) == [(second[0], first[0])]
    assert pairs([first]) == []


def test_two_agent_run_is_deterministic_and_writes_comparison(tmp_path, capsys):
    args = ["--agents", "naive,naive", "--seeds", "dev", "--scenarios", "base", "--steps", "40"]
    main([*args, "--out", str(tmp_path / "a")])
    main([*args, "--out", str(tmp_path / "b")])
    out = capsys.readouterr().out
    assert file_digest(tmp_path / "a" / "episodes.csv") == file_digest(
        tmp_path / "b" / "episodes.csv"
    )
    assert "naive − naive: base" in out
    report = (tmp_path / "a" / "report.md").read_text(encoding="utf-8")
    assert "## naive − naive: base" in report and "## Summary: naive" in report
    lines = (tmp_path / "a" / "episodes.csv").read_text().splitlines()
    assert len(lines) == 1 + 2 * 30


def test_cli_rejects_unknown_agent(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["--agents", "naive,bogus", "--out", str(tmp_path)])
    assert "unknown agent bogus" in capsys.readouterr().err


def test_market_draws_are_identical_across_agents(monkeypatch):
    """The agent's quotes must not change the true-value path or the takers that arrive."""
    seen: list[list[list[TakerIntent]]] = []

    def recording(*args):
        intents = generate_intents(*args)
        seen[-1].append(intents)
        return intents

    class Silent:
        def quote(self, obs: Observation) -> Quote:
            return Quote(None, 0, None, 0, 0.0)

    monkeypatch.setattr(mm.simulation, "generate_intents", recording)
    config = replace(load_config(scenario="toxic"), n_steps=200, seed=3)
    paths = []
    for agent in (None, Silent()):
        seen.append([])
        paths.append(run_episode(config, agent=agent).path)
    assert paths[0] == paths[1]
    assert seen[0] == seen[1]
