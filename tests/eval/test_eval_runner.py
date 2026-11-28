import pytest

from mm.config import DEFAULT_CONFIG_PATH
from mm.eval.cli import main
from mm.eval.plots import write_plots
from mm.eval.report import file_digest, write_episodes_csv, write_report
from mm.eval.runner import evaluate

SCENARIOS = ["no_informed", "base"]
SEEDS = [0, 1]
STEPS = 100


def run():
    return evaluate(SCENARIOS, SEEDS, STEPS)


def test_same_inputs_give_identical_csv_digest(tmp_path):
    first, second = tmp_path / "a.csv", tmp_path / "b.csv"
    write_episodes_csv(run(), first)
    write_episodes_csv(run(), second)
    assert file_digest(first) == file_digest(second)


def test_csv_has_one_row_per_scenario_and_seed(tmp_path):
    path = tmp_path / "episodes.csv"
    write_episodes_csv(run(), path)
    lines = path.read_text().splitlines()
    assert lines[0].startswith("scenario,seed,final_pnl")
    assert len(lines) == 1 + len(SCENARIOS) * len(SEEDS)


def test_report_and_plots_are_written(tmp_path):
    results = run()
    write_report(results, STEPS, tmp_path / "report.md")
    write_plots(results, tmp_path / "plots")
    report = (tmp_path / "report.md").read_text()
    assert "## Summary" in report and "## Markouts" in report
    assert "Mean \\|q\\|" in report  # pipes escaped so the markdown table stays intact
    for name in ("pnl_paths.png", "inventory_paths.png", "markouts.png"):
        assert (tmp_path / "plots" / name).stat().st_size > 0


def test_evaluate_needs_at_least_one_seed():
    with pytest.raises(ValueError):
        evaluate(SCENARIOS, [], STEPS)


def test_cli_prints_digest_of_written_csv(tmp_path, capsys):
    args = ["--seeds", "dev", "--scenarios", "base", "--steps", "50", "--out", str(tmp_path)]
    main([*args, "--digest"])
    out = capsys.readouterr().out
    assert f"episodes.csv sha256: {file_digest(tmp_path / 'episodes.csv')}" in out


def test_cli_defaults_to_every_scenario_in_the_config(tmp_path, capsys):
    main(["--seeds", "dev", "--steps", "30", "--out", str(tmp_path)])
    header = capsys.readouterr().out.splitlines()[1]
    assert header.split()[-3:] == ["no_informed", "base", "toxic"]


def test_cli_reads_the_given_config_file(tmp_path, capsys):
    path = tmp_path / "custom.toml"
    path.write_text(DEFAULT_CONFIG_PATH.read_text().replace("n_steps = 2000", "n_steps = 40"))
    main(["--config", str(path), "--seeds", "dev", "--scenarios", "base", "--out", str(tmp_path)])
    assert "40 steps per episode" in capsys.readouterr().out


def test_cli_rejects_unknown_scenario(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main(["--scenarios", "toxik", "--out", str(tmp_path)])
    assert "unknown scenario toxik" in capsys.readouterr().err
