import math
from dataclasses import replace

import numpy as np
import pytest

from mm.config import load_config, scenario_names
from mm.eval.metrics import GATE_RULES, episode_metrics, markout, max_drawdown, sharpe
from mm.risk import GateEvent
from mm.simulation import EpisodeResult, FillRecord, GateLogEntry, StepRecord, run_episode
from mm.types import Side

HORIZONS = load_config().evaluation.markout_horizons

# Hand-built episode of 3 steps: V = 100, 101, 103, then 102 (= V(T)) and 100 beyond it.
PATH = (100.0, 101.0, 103.0, 102.0, 100.0)
FILLS = [
    FillRecord(0, 100.0, "noise", Side.BUY, price=99, size=2, maker_order_id=1),
    FillRecord(1, 101.0, "informed", Side.SELL, price=102, size=1, maker_order_id=2),
    FillRecord(2, 103.0, "noise", Side.SELL, price=105, size=3, maker_order_id=3),
]
STATES = [(2, -198), (1, -96), (-2, 219)]  # (position, cash) after each step's fills


def hand_built() -> EpisodeResult:
    steps = [
        StepRecord(t, PATH[t], q, c, bid_price=90, bid_size=5, ask_price=110, ask_size=5)
        for t, (q, c) in enumerate(STATES)
    ]
    gate = [
        GateLogEntry(0, GateEvent(Side.BUY, "position_clip", "")),
        GateLogEntry(2, GateEvent(Side.SELL, "position_clip", "")),
        GateLogEntry(2, GateEvent(Side.BUY, "size", "")),
    ]
    return EpisodeResult(
        path=PATH,
        fills=FILLS,
        steps=steps,
        gate_events=gate,
        final_position=-2,
        final_cash=219,
        final_pnl=219 - 2 * 102,
    )


def test_hand_built_decomposition_matches_known_numbers():
    m = episode_metrics(hand_built(), 1.0, fee_per_lot=0, position_limit=2, horizons=HORIZONS)
    assert m.final_pnl == 15
    assert m.spread_capture == 9  # 1*2 + 1*1 + 2*3
    assert m.inventory_pnl == 6  # 2*1 + 1*2 + (-2)*(-1)
    assert m.fees == 0


def test_money_is_reported_in_price_units():
    m = episode_metrics(hand_built(), 0.01, fee_per_lot=1, position_limit=2, horizons=HORIZONS)
    assert m.final_pnl == pytest.approx(0.15)
    assert m.fees == pytest.approx(0.06)
    assert m.markouts[("noise", 0)] == pytest.approx(0.016)


def test_markout_is_size_weighted_per_lot():
    # Noise fill edges at h=0 are 1 and 2 per lot on 2 and 3 lots: (2 + 6) / 5, not 1.5.
    assert markout(FILLS, PATH, "noise", 0) == pytest.approx(1.6)
    assert markout(FILLS, PATH, "noise", 1) == pytest.approx((4 + 9) / 5)


def test_markout_splits_by_counterparty_kind():
    assert markout(FILLS, PATH, "informed", 1) == pytest.approx(-1.0)
    assert markout(FILLS, PATH, "informed", 3) == pytest.approx(2.0)


def test_markout_skips_fills_whose_horizon_is_beyond_the_path():
    # h=4: the noise fill at step 2 would need V(6); only the step-0 fill counts.
    assert markout(FILLS, PATH, "noise", 4) == pytest.approx(1.0)
    assert math.isnan(markout(FILLS, PATH, "informed", 4))


def test_markout_is_nan_without_fills_of_that_kind():
    assert math.isnan(markout(FILLS[:1], PATH, "informed", 0))


def test_inventory_fill_and_gate_counts_on_hand_built_episode():
    m = episode_metrics(hand_built(), 1.0, fee_per_lot=0, position_limit=2, horizons=HORIZONS)
    assert m.mean_abs_position == pytest.approx(5 / 3)
    assert m.max_abs_position == 2
    assert m.pct_time_at_limit == pytest.approx(200 / 3)
    assert m.fills == {"noise": 2, "informed": 1}
    assert m.lots == {"noise": 5, "informed": 1}
    assert m.fill_rate == pytest.approx(6 / 30)
    assert m.gate_events == {"size": 1, "price_band": 0, "self_cross": 0, "position_clip": 2}


def test_hand_built_drawdown_and_sharpe_use_mark_to_market_path():
    m = episode_metrics(hand_built(), 1.0, fee_per_lot=0, position_limit=2, horizons=HORIZONS)
    changes = np.diff([0.0, 2, 5, 13])  # m_t = cash_t + q_t * V(t), starting from 0
    assert m.max_drawdown == 0
    assert m.sharpe == pytest.approx(changes.mean() / changes.std() * math.sqrt(3))


def test_as_row_has_every_scalar_column():
    row = episode_metrics(hand_built(), 1.0, 0, 2, HORIZONS).as_row()
    assert row["final_pnl"] == 15
    assert row["lots_informed"] == 1
    assert row["markout_noise_0"] == pytest.approx(1.6)
    assert all(f"gate_{rule}" in row for rule in GATE_RULES)


def test_max_drawdown_is_largest_peak_to_trough_drop():
    assert max_drawdown(np.array([0.0, 5, 2, 7, 1, 4])) == 6
    assert max_drawdown(np.array([0.0, 1, 2, 3])) == 0


def test_sharpe_on_known_series():
    # changes 1 and 2: mean 1.5, population std 0.5, two changes
    assert sharpe(np.array([0.0, 1, 3])) == pytest.approx(3 * math.sqrt(2))


def test_sharpe_of_flat_series_is_zero():
    assert sharpe(np.array([3.0, 3, 3, 3])) == 0.0


@pytest.mark.parametrize("scenario", scenario_names())
@pytest.mark.parametrize("seed", [0, 1, 2])
@pytest.mark.parametrize("fee_per_lot", [0, 1])
def test_pnl_decomposition_is_exact_on_real_episodes(scenario, seed, fee_per_lot):
    base = load_config(scenario=scenario)
    config = replace(
        base, engine=replace(base.engine, fee_per_lot=fee_per_lot), n_steps=300, seed=seed
    )
    position_limit = config.risk.position_limit
    m = episode_metrics(run_episode(config), 0.01, fee_per_lot, position_limit, HORIZONS)
    assert m.final_pnl == pytest.approx(m.spread_capture + m.inventory_pnl - m.fees, abs=1e-9)
    if fee_per_lot:
        assert m.fees > 0
