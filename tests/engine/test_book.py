"""Unit and edge-case tests for the order book and matching."""

import pytest

from mm.engine import OrderBook, Side


def test_empty_book_has_no_best_prices_and_is_not_crossed():
    book = OrderBook()
    assert book.best_bid() is None
    assert book.best_ask() is None
    assert not book.is_crossed()


def test_add_limit_returns_sequential_ids_and_sets_best_prices():
    book = OrderBook()
    assert book.add_limit("mm", Side.BUY, 9990, 5) == 1
    assert book.add_limit("mm", Side.SELL, 10010, 5) == 2
    assert book.add_limit("mm", Side.BUY, 9995, 5) == 3
    assert book.best_bid() == 9995
    assert book.best_ask() == 10010


@pytest.mark.parametrize("size", [0, -1])
def test_add_limit_rejects_non_positive_size(size):
    with pytest.raises(ValueError):
        OrderBook().add_limit("mm", Side.BUY, 10000, size)


@pytest.mark.parametrize(
    ("side", "price"), [(Side.BUY, 10010), (Side.BUY, 10020), (Side.SELL, 9990), (Side.SELL, 9980)]
)
def test_add_limit_that_would_cross_raises(side, price):
    book = OrderBook()
    book.add_limit("mm", Side.BUY, 9990, 1)
    book.add_limit("mm", Side.SELL, 10010, 1)
    with pytest.raises(ValueError):
        book.add_limit("mm", side, price, 1)
    assert not book.is_crossed()


def test_ioc_on_empty_book_returns_no_fills():
    assert OrderBook().match_ioc("taker", Side.BUY, 10100, 5, "noise") == []


def test_ioc_rejects_non_positive_size():
    with pytest.raises(ValueError):
        OrderBook().match_ioc("taker", Side.BUY, 10100, 0, "noise")


def test_ioc_with_no_liquidity_within_limit_returns_no_fills():
    book = OrderBook()
    book.add_limit("mm", Side.SELL, 10010, 5)
    assert book.match_ioc("taker", Side.BUY, 10005, 5, "noise") == []
    assert book.open_orders("mm")[0].filled == 0


def test_ioc_never_fills_beyond_limit_price():
    book = OrderBook()
    book.add_limit("mm", Side.SELL, 10010, 2)
    book.add_limit("mm", Side.SELL, 10020, 2)
    fills = book.match_ioc("taker", Side.BUY, 10010, 10, "noise")
    assert [(f.price, f.size) for f in fills] == [(10010, 2)]
    assert book.best_ask() == 10020


def test_ioc_sweeps_multiple_levels_at_maker_prices_best_first():
    book = OrderBook()
    book.add_limit("mm", Side.BUY, 9990, 2)
    book.add_limit("mm", Side.BUY, 9980, 3)
    book.add_limit("mm", Side.BUY, 9970, 4)
    fills = book.match_ioc("taker", Side.SELL, 9970, 6, "informed")
    assert [(f.price, f.size) for f in fills] == [(9990, 2), (9980, 3), (9970, 1)]
    assert book.best_bid() == 9970
    assert book.open_orders("mm")[0].remaining == 3


def test_ioc_remainder_is_dropped_after_sweeping_the_book():
    book = OrderBook()
    book.add_limit("mm", Side.SELL, 10010, 2)
    fills = book.match_ioc("taker", Side.BUY, 10100, 10, "noise")
    assert sum(f.size for f in fills) == 2
    assert book.best_ask() is None
    assert book.best_bid() is None
    assert book.open_orders("taker") == []


def test_ioc_partially_fills_resting_order_and_leaves_remainder():
    book = OrderBook()
    order_id = book.add_limit("mm", Side.SELL, 10010, 5)
    fills = book.match_ioc("taker", Side.BUY, 10010, 3, "noise")
    assert len(fills) == 1
    assert fills[0].maker_order_id == order_id
    (order,) = book.open_orders("mm")
    assert (order.filled, order.remaining) == (3, 2)
    assert book.best_ask() == 10010


def test_exact_size_fill_removes_order_and_level():
    book = OrderBook()
    order_id = book.add_limit("mm", Side.SELL, 10010, 5)
    book.match_ioc("taker", Side.BUY, 10010, 5, "noise")
    assert book.open_orders("mm") == []
    assert book.best_ask() is None
    assert not book.cancel(order_id)


def test_orders_at_same_price_fill_in_fifo_order():
    book = OrderBook()
    first = book.add_limit("mm", Side.BUY, 9990, 2)
    second = book.add_limit("mm", Side.BUY, 9990, 2)
    fills = book.match_ioc("taker", Side.SELL, 9990, 3, "noise")
    assert [(f.maker_order_id, f.size) for f in fills] == [(first, 2), (second, 1)]


def test_fill_records_both_parties_side_and_tag():
    book = OrderBook()
    order_id = book.add_limit("mm", Side.SELL, 10010, 1)
    (fill,) = book.match_ioc("bot", Side.BUY, 10050, 1, "informed")
    assert fill.taker_owner == "bot"
    assert fill.maker_owner == "mm"
    assert fill.maker_order_id == order_id
    assert fill.taker_side is Side.BUY
    assert fill.price == 10010
    assert fill.taker_tag == "informed"


def test_cancel_removes_order_and_empty_level():
    book = OrderBook()
    order_id = book.add_limit("mm", Side.BUY, 9990, 1)
    assert book.cancel(order_id)
    assert book.best_bid() is None
    assert book.open_orders("mm") == []


def test_cancel_keeps_other_orders_at_the_same_level():
    book = OrderBook()
    first = book.add_limit("mm", Side.BUY, 9990, 1)
    second = book.add_limit("mm", Side.BUY, 9990, 1)
    assert book.cancel(first)
    assert book.best_bid() == 9990
    assert [o.id for o in book.open_orders("mm")] == [second]


def test_cancel_unknown_or_already_cancelled_id_returns_false():
    book = OrderBook()
    order_id = book.add_limit("mm", Side.BUY, 9990, 1)
    assert not book.cancel(999)
    assert book.cancel(order_id)
    assert not book.cancel(order_id)


def test_cancel_all_removes_only_that_owners_orders():
    book = OrderBook()
    book.add_limit("mm", Side.BUY, 9990, 1)
    book.add_limit("mm", Side.SELL, 10010, 1)
    other = book.add_limit("other", Side.BUY, 9980, 1)
    assert book.cancel_all("mm") == 2
    assert book.open_orders("mm") == []
    assert [o.id for o in book.open_orders("other")] == [other]
    assert book.cancel_all("mm") == 0
