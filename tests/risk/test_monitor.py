import pytest

from mm.engine import Account, Fill, OrderBook, Side
from mm.risk import InvariantMonitor, InvariantViolation

AGENT = "agent"


def clean_state(position_limit: int = 50):
    """A book with an agent bid and ask, one partial fill on the ask, all recorded."""
    book = OrderBook()
    account = Account()
    monitor = InvariantMonitor(AGENT, position_limit)
    bid_id = book.add_limit(AGENT, Side.BUY, 9998, 5)
    ask_id = book.add_limit(AGENT, Side.SELL, 10002, 5)
    monitor.record_order(bid_id, 5)
    monitor.record_order(ask_id, 5)
    for fill in book.match_ioc("taker", Side.BUY, 10002, 2, "noise"):
        account.apply_fill(fill, as_owner=AGENT)
        monitor.record_fill(fill)
    return book, account, monitor


def test_clean_state_passes():
    book, account, monitor = clean_state()
    monitor.check(book, account)


def test_crossed_book_is_detected():
    book, account, monitor = clean_state()
    # Tamper: force a bid above the ask into the book's internals.
    book._prices[Side.BUY].append(10005)
    with pytest.raises(InvariantViolation, match="crossed"):
        monitor.check(book, account)


def test_position_beyond_limit_is_detected():
    book, account, monitor = clean_state(position_limit=1)
    with pytest.raises(InvariantViolation, match="exceeds limit"):
        monitor.check(book, account)


def test_cash_that_does_not_reconcile_is_detected():
    book, account, monitor = clean_state()
    account.cash += 1
    with pytest.raises(InvariantViolation, match="reconcile"):
        monitor.check(book, account)


def test_open_order_filled_to_its_size_is_detected():
    book, account, monitor = clean_state()
    order = book.open_orders(AGENT)[0]
    order.filled = order.size
    with pytest.raises(InvariantViolation, match="open order"):
        monitor.check(book, account)


def test_fills_beyond_original_order_size_are_detected():
    book, account, monitor = clean_state()
    ask_fill = account.fills[0][0]
    extra = Fill("taker", AGENT, ask_fill.maker_order_id, Side.BUY, 10002, 4, "noise")
    monitor.record_fill(extra)
    with pytest.raises(InvariantViolation, match="more than its size"):
        monitor.check(book, account)


def test_fill_for_unrecorded_order_is_detected():
    book, account, monitor = clean_state()
    monitor.record_fill(Fill("taker", AGENT, 999, Side.BUY, 10002, 1, "noise"))
    with pytest.raises(InvariantViolation, match="order 999"):
        monitor.check(book, account)


def test_violation_is_a_runtime_error():
    assert issubclass(InvariantViolation, RuntimeError)
