"""Property-based invariant tests: random sequences of adds, cancels and IOCs."""

from hypothesis import given
from hypothesis import strategies as st

from mm.engine import Account, Fill, OrderBook, Side

MAKER = "mm"
TAKERS = ["noise", "informed"]

sides = st.sampled_from([Side.BUY, Side.SELL])
prices = st.integers(min_value=9950, max_value=10050)
sizes = st.integers(min_value=1, max_value=10)

add_op = st.tuples(st.just("add"), sides, prices, sizes)
cancel_op = st.tuples(st.just("cancel"), st.integers(min_value=1, max_value=60))
ioc_op = st.tuples(st.just("ioc"), st.sampled_from(TAKERS), sides, prices, sizes)
operations = st.lists(st.one_of(add_op, cancel_op, ioc_op), max_size=60)


def would_cross(book: OrderBook, side: Side, price: int) -> bool:
    if side is Side.BUY:
        ask = book.best_ask()
        return ask is not None and price >= ask
    bid = book.best_bid()
    return bid is not None and price <= bid


@given(operations)
def test_random_order_flow_preserves_book_and_accounting_invariants(ops):
    book = OrderBook()
    maker = Account(fee_per_lot=1)
    takers = {name: Account(fee_per_lot=1) for name in TAKERS}
    sizes_by_id: dict[int, int] = {}
    filled_by_id: dict[int, int] = {}
    all_fills: list[Fill] = []

    for op in ops:
        if op[0] == "add":
            _, side, price, size = op
            if would_cross(book, side, price):
                continue  # resting orders never cross; the gate upstream ensures this
            sizes_by_id[book.add_limit(MAKER, side, price, size)] = size
        elif op[0] == "cancel":
            book.cancel(op[1])
        else:
            _, taker, side, limit, size = op
            fills = book.match_ioc(taker, side, limit, size, taker)
            assert sum(f.size for f in fills) <= size
            for fill in fills:
                if side is Side.BUY:
                    assert fill.price <= limit
                else:
                    assert fill.price >= limit
                maker.apply_fill(fill, as_owner=MAKER)
                takers[taker].apply_fill(fill, as_owner=taker)
                filled_by_id[fill.maker_order_id] = (
                    filled_by_id.get(fill.maker_order_id, 0) + fill.size
                )
            all_fills.extend(fills)

        assert not book.is_crossed()
        for order in book.open_orders(MAKER):
            assert 0 <= order.filled < order.size

    # No order is ever filled more than its size (no double fills).
    for order_id, filled in filled_by_id.items():
        assert filled <= sizes_by_id[order_id]

    # Every lot the maker traded was traded by some taker, and vice versa.
    maker_lots = sum(f.size for f, _ in maker.fills)
    assert maker_lots == sum(f.size for t in takers.values() for f, _ in t.fills)
    assert maker.position == -sum(t.position for t in takers.values())

    signed = sum(f.size if f.taker_side is Side.SELL else -f.size for f in all_fills)
    assert maker.position == signed
    assert maker.reconciles()
    assert all(t.reconciles() for t in takers.values())
