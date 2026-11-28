from mm.eval.heldout import (
    INTERPRETATION_HEADING,
    Column,
    baselines_note,
    per_seed,
    run_column,
    side_by_side,
    write_with_interpretation,
)
from mm.eval.recording import EpisodeRecorder
from mm.eval.report import SIGNIFICANT, SUMMARY_METRICS
from mm.eval.runner import evaluate

SEEDS = (0, 1, 2)
COLUMNS = (
    Column("v1", "skew", None),
    Column("v2-tuned", "kalman_tuned", 0),
    Column("v4", "adaptive", 1),
)
EXTRA = (("half_spread", "Mean half-spread"), ("intensity", "Mean ρ"))


def test_recorder_keeps_rho_for_the_adaptive_agent_only():
    recorder = EpisodeRecorder()
    evaluate(["base"], SEEDS, 100, agent="adaptive", agent_factory=recorder.factory)
    assert len(recorder.mean_intensity()) == len(SEEDS)
    assert all(len(e.intensity) == 100 for e in recorder.episodes)
    other = EpisodeRecorder()
    evaluate(["base"], SEEDS, 100, agent="kalman_tuned", agent_factory=other.factory)
    assert other.mean_intensity() == []


def test_side_by_side_has_plain_columns_marks_and_dashes():
    runs = [run_column(c.agent, "base", SEEDS, 300) for c in COLUMNS]
    rows = side_by_side(runs, COLUMNS, EXTRA)
    assert rows[0] == ["Metric (mean [95% CI])", "v1", "v2-tuned", "v4"]
    assert len(rows) == 1 + len(SUMMARY_METRICS) + len(EXTRA)
    spread = rows[-2]
    assert spread[1].startswith("2.00") and SIGNIFICANT not in spread[1]  # v1 is unmarked
    assert spread[2].startswith("4.00") and spread[2].endswith(SIGNIFICANT)
    rho = rows[-1]
    assert rho[1] == rho[2] == "—"
    assert rho[3] != "—" and SIGNIFICANT not in rho[3]  # its baseline has no ρ
    assert per_seed(runs[0], "final_pnl") == [m.final_pnl for m in runs[0][0].metrics]


def test_baselines_note_names_each_marked_columns_baseline():
    assert baselines_note(COLUMNS) == "v2-tuned against v1; v4 against v2-tuned"


def test_interpretation_is_kept_across_rewrites(tmp_path):
    path = tmp_path / "out" / "heldout.md"
    write_with_interpretation(path, "# First")
    assert path.read_text() == f"# First\n\n{INTERPRETATION_HEADING}\n\nTBD\n"
    path.write_text(path.read_text().replace("TBD", "Hand-written."))
    write_with_interpretation(path, "# Second\n")
    assert path.read_text() == f"# Second\n\n{INTERPRETATION_HEADING}\n\nHand-written.\n"
