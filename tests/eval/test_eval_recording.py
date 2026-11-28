import math
from dataclasses import replace

from mm.eval.recording import EpisodeRecorder, informed_lot_share
from mm.eval.runner import evaluate

SEEDS = (0, 1)


def test_recorder_keeps_one_episode_per_seed_and_v3s_score():
    recorder = EpisodeRecorder()
    (result,) = evaluate(["toxic"], SEEDS, 200, agent="toxicity", agent_factory=recorder.factory)
    assert len(recorder.episodes) == len(SEEDS)
    assert all(len(e.half_spreads) == 200 for e in recorder.episodes)
    assert len(recorder.mean_toxicity()) == len(SEEDS)
    assert all(h >= 2 for h in recorder.mean_half_spread())
    # Recording does not change the run.
    (plain,) = evaluate(["toxic"], SEEDS, 200, agent="toxicity")
    assert [m.as_row() for m in plain.metrics] == [m.as_row() for m in result.metrics]


def test_recorder_has_no_score_for_agents_without_one():
    recorder = EpisodeRecorder()
    evaluate(["base"], SEEDS, 100, agent="kalman", agent_factory=recorder.factory)
    assert recorder.mean_toxicity() == []
    assert recorder.mean_half_spread() == [2.0, 2.0]


def test_informed_lot_share_is_informed_over_all_lots():
    (result,) = evaluate(["toxic"], SEEDS, 300, agent="kalman")
    for share, m in zip(informed_lot_share(result), result.metrics, strict=True):
        assert share == m.lots["informed"] / (m.lots["informed"] + m.lots["noise"])
    no_fills = replace(result.metrics[0], lots={"informed": 0, "noise": 0})
    assert math.isnan(informed_lot_share(replace(result, metrics=[no_fills]))[0])
