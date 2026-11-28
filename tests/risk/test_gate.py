import pytest

from mm.agent import Quote
from mm.config import RiskConfig
from mm.risk import apply_gate
from mm.types import Side

CONFIG = RiskConfig(position_limit=50, max_order_size=10, max_quote_distance=50)
LAST = 10000


def gate(quote: Quote, position: int = 0):
    return apply_gate(quote, position, LAST, CONFIG)


def rules(result) -> list[tuple[Side, str]]:
    return [(event.side, event.rule) for event in result.events]


def test_valid_quote_passes_unchanged_without_events():
    quote = Quote(9998, 5, 10002, 5)
    result = gate(quote)
    assert result.quote == quote
    assert result.events == []


def test_absent_sides_are_ignored():
    result = gate(Quote(None, 0, None, 0))
    assert result.quote == Quote(None, 0, None, 0)
    assert result.events == []


@pytest.mark.parametrize("size", [0, 11])
def test_bid_with_invalid_size_is_rejected(size):
    result = gate(Quote(9998, size, 10002, 5))
    assert result.quote == Quote(None, 0, 10002, 5)
    assert rules(result) == [(Side.BUY, "size")]


@pytest.mark.parametrize("size", [0, 11])
def test_ask_with_invalid_size_is_rejected(size):
    result = gate(Quote(9998, 5, 10002, size))
    assert result.quote == Quote(9998, 5, None, 0)
    assert rules(result) == [(Side.SELL, "size")]


def test_size_at_max_order_size_is_accepted():
    result = gate(Quote(9998, 10, 10002, 10))
    assert result.quote == Quote(9998, 10, 10002, 10)
    assert result.events == []


def test_quote_exactly_at_price_band_is_accepted():
    result = gate(Quote(LAST - 50, 5, LAST + 50, 5))
    assert result.quote == Quote(LAST - 50, 5, LAST + 50, 5)
    assert result.events == []


def test_quote_one_tick_beyond_price_band_is_rejected():
    result = gate(Quote(LAST - 51, 5, LAST + 51, 5))
    assert result.quote == Quote(None, 0, None, 0)
    assert rules(result) == [(Side.BUY, "price_band"), (Side.SELL, "price_band")]


@pytest.mark.parametrize("bid, ask", [(10000, 10000), (10001, 10000)])
def test_locked_or_crossed_quote_rejects_both_sides(bid, ask):
    result = gate(Quote(bid, 5, ask, 5))
    assert result.quote == Quote(None, 0, None, 0)
    assert rules(result) == [(Side.BUY, "self_cross"), (Side.SELL, "self_cross")]


def test_long_position_clips_bid_to_remaining_capacity():
    result = gate(Quote(9998, 10, 10002, 10), position=45)
    assert result.quote == Quote(9998, 5, 10002, 10)
    assert rules(result) == [(Side.BUY, "position_clip")]


def test_bid_within_capacity_is_not_clipped():
    result = gate(Quote(9998, 5, 10002, 10), position=45)
    assert result.quote == Quote(9998, 5, 10002, 10)
    assert result.events == []


def test_bid_is_dropped_at_long_position_limit():
    result = gate(Quote(9998, 5, 10002, 10), position=50)
    assert result.quote == Quote(None, 0, 10002, 10)
    assert rules(result) == [(Side.BUY, "position_clip")]


def test_short_position_clips_ask_to_remaining_capacity():
    result = gate(Quote(9998, 10, 10002, 10), position=-45)
    assert result.quote == Quote(9998, 10, 10002, 5)
    assert rules(result) == [(Side.SELL, "position_clip")]


def test_ask_is_dropped_at_short_position_limit():
    result = gate(Quote(9998, 10, 10002, 5), position=-50)
    assert result.quote == Quote(9998, 10, None, 0)
    assert rules(result) == [(Side.SELL, "position_clip")]


def test_events_carry_a_readable_detail():
    result = gate(Quote(9998, 10, 10002, 10), position=45)
    assert result.events[0].detail == "size 10 clipped to 5"
