"""Competing makers (decision 12): fairness, priority, post-only across makers, invariants."""

import tomllib
from dataclasses import replace

import numpy as np
import pytest

from mm import simulation
from mm.agent import Observation, Quote
from mm.config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    RiskConfig,
    SimConfig,
    build_config,
    load_config,
)
from mm.eval.cli import main
from mm.eval.report import file_digest
from mm.risk import InvariantViolation, apply_gate
from mm.simulation import EpisodeResult, run_episode
from mm.types import Side

SHORT = 300
BASE_DIGEST = "6316388b8ab23844f9e5e75416aa085231ee7dc0c5eab49533ebed64398712df"


def config(scenario: str = "base", seed: int = 0, n_steps: int = SHORT) -> SimConfig:
    return replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)


class Fixed:
    """Quotes `offset` ticks either side of the last trade price with `size` lots."""

    def __init__(self, offset: int, size: int, bid_offset: int | None = None) -> None:
        self.offset, self.size = offset, size
        self.bid_offset = offset if bid_offset is None else bid_offset

    def quote(self, obs: Observation) -> Quote:
        ltp = obs.last_trade_price
        return Quote(ltp - self.bid_offset, self.size, ltp + self.offset, self.size, float(ltp))


def competitor_of(result: EpisodeResult) -> EpisodeResult:
    assert result.competitor is not None
    return result.competitor


def roomy(cfg: SimConfig) -> SimConfig:
    """Large size and position limits, so one maker's quote never runs out within a step."""
    risk = replace(cfg.risk, position_limit=100_000, max_order_size=10_000)
    return replace(cfg, risk=risk)


def test_base_digest_is_unchanged(tmp_path, capsys):
    args = ["--agents", "skew", "--seeds", "dev", "--scenarios", "base", "--steps", "300"]
    main([*args, "--out", str(tmp_path)])
    assert file_digest(tmp_path / "episodes.csv") == BASE_DIGEST


def test_no_competitor_draws_nothing_extra_and_matches_base():
    cfg = config()
    assert cfg.market.competitor == "none"
    result = run_episode(cfg)
    assert result.competitor is None
    assert result.competitor_first == []
    # The market's draws do not depend on the competitor: the true-value path is identical.
    assert run_episode(config("vs_v1")).path == result.path


def test_strictly_better_competitor_takes_all_taker_flow():
    result = run_episode(roomy(config()), agent=Fixed(3, 5), competitor=Fixed(1, 5000))
    assert result.fills == []
    assert len(competitor_of(result).fills) > 0


def test_first_poster_fills_first_at_equal_prices():
    result = run_episode(config(), agent=Fixed(1, 1), competitor=Fixed(1, 1))
    theirs = competitor_of(result)
    filled = {
        owner: {(f.step, f.side) for f in record.fills}
        for owner, record in (("ours", result), ("theirs", theirs))
    }
    traded = filled["ours"] | filled["theirs"]
    assert traded
    for step, side in traded:
        first = "theirs" if result.competitor_first[step] else "ours"
        assert (step, side) in filled[first]


def test_posting_order_is_deterministic_per_seed_and_fair():
    first = run_episode(config("vs_v1", seed=3)).competitor_first
    assert first == run_episode(config("vs_v1", seed=3)).competitor_first
    assert first != run_episode(config("vs_v1", seed=4)).competitor_first
    assert len(first) == SHORT
    assert 0.4 < np.mean(first) < 0.6


def test_quote_crossing_the_other_maker_is_rejected_and_does_not_trade():
    # Ours: bid ltp-1, ask ltp+1. Theirs: bid ltp+1 (crosses our ask), ask ltp+3.
    cfg = roomy(config())  # no position clip, so the crossing bid is sent every step
    result = run_episode(cfg, agent=Fixed(1, 5), competitor=Fixed(3, 5, bid_offset=-1))
    theirs = competitor_of(result)
    for t, competitor_first in enumerate(result.competitor_first):
        second, side = (result, Side.SELL) if competitor_first else (theirs, Side.BUY)
        events = [e.event for e in second.gate_events if e.step == t]
        assert [(e.side, e.rule) for e in events] == [(side, "cross_book")]
    assert len(result.gate_events) + len(theirs.gate_events) == cfg.n_steps
    assert all(f.taker_kind in ("noise", "informed") for f in result.fills + theirs.fills)


def test_gate_rejects_quotes_crossing_the_other_makers_best_prices():
    risk = RiskConfig(position_limit=50, max_order_size=10, max_quote_distance=50)
    quote = Quote(10001, 5, 9999, 5, 10000.0)  # bid at their ask, ask at their bid
    result = apply_gate(quote, 0, 10000, risk, book_bid=9999, book_ask=10001)
    assert [(e.side, e.rule) for e in result.events] == [
        (Side.BUY, "self_cross"),
        (Side.SELL, "self_cross"),
    ]
    result = apply_gate(Quote(10001, 5, 10003, 5, 0.0), 0, 10000, risk, book_ask=10001)
    assert result.quote.bid_price is None and result.quote.ask_price == 10003
    assert [(e.side, e.rule) for e in result.events] == [(Side.BUY, "cross_book")]
    result = apply_gate(Quote(9997, 5, 9999, 5, 0.0), 0, 10000, risk, book_bid=9999)
    assert result.quote.ask_price is None and result.quote.bid_price == 9997
    assert [(e.side, e.rule) for e in result.events] == [(Side.SELL, "cross_book")]


def reconciles(record: EpisodeResult) -> bool:
    position = sum(f.side.sign * f.size for f in record.fills)
    cash = sum(-f.side.sign * f.size * f.price for f in record.fills)
    return (position, cash) == (record.final_position, record.final_cash)


@pytest.mark.parametrize("scenario", ["vs_v1", "vs_tuned", "vs_final"])
@pytest.mark.parametrize("agent", ["skew", "kalman", "kalman_tuned", "final"])
def test_full_episode_passes_the_monitor_for_both_makers(scenario, agent):
    cfg = load_config(scenario=scenario)
    cfg = replace(cfg, agent=replace(cfg.agent, type=agent), seed=1000)
    result = run_episode(cfg)  # the monitor raises on any violation
    theirs = competitor_of(result)
    limit = cfg.risk.position_limit
    for record in (result, theirs):
        assert len(record.steps) == cfg.n_steps
        assert reconciles(record)
        assert max(abs(step.position) for step in record.steps) <= limit
    ours_ids = {f.maker_order_id for f in result.fills}
    assert ours_ids.isdisjoint(f.maker_order_id for f in theirs.fills)


@pytest.mark.parametrize("breaching", ["ours", "theirs"])
def test_monitor_halts_on_a_violation_by_either_maker(monkeypatch, breaching):
    # The gate is told position 0 every step, so its clip no longer bounds the position.
    def blind_gate(quote, position, last_trade_price, risk, **book):
        return apply_gate(quote, 0, last_trade_price, risk, **book)

    monkeypatch.setattr(simulation, "apply_gate", blind_gate)
    big, idle = Fixed(1, 10), Fixed(40, 1)
    agent, competitor = (big, idle) if breaching == "ours" else (idle, big)
    cfg = config()
    cfg = replace(cfg, risk=replace(cfg.risk, position_limit=5))
    owner = "agent" if breaching == "ours" else "competitor"
    with pytest.raises(InvariantViolation, match=f"^{owner} position .* exceeds limit"):
        run_episode(cfg, agent=agent, competitor=competitor)


def test_unknown_competitor_name_is_rejected():
    raw_cfg = config()
    bad = replace(raw_cfg, market=replace(raw_cfg.market, competitor="skwe"))
    with pytest.raises(ConfigError, match="unknown market.competitor 'skwe'"):
        run_episode(bad)


@pytest.mark.parametrize(
    ("name", "competitor"),
    [
        ("vs_v1", "skew"),
        ("vs_tuned", "kalman_tuned"),
        ("vs_final", "final"),
        ("vs_competitive", "competitive"),
    ],
)
def test_competition_scenarios_change_only_the_competitor(name, competitor):
    base = load_config()
    expected = replace(base, market=replace(base.market, competitor=competitor))
    assert load_config(scenario=name) == expected


def test_competitor_must_be_a_string():
    raw = tomllib.loads(DEFAULT_CONFIG_PATH.read_text())
    raw["market"]["competitor"] = 1
    with pytest.raises(ConfigError, match="'market.competitor' must be a string"):
        build_config(raw)
