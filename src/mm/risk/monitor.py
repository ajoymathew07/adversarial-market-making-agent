"""Runtime invariant monitor, checked after every simulation step."""

from collections import defaultdict

from mm.engine import Account, Fill, OrderBook


class InvariantViolation(RuntimeError):
    """A core invariant failed; the run must halt."""


class InvariantMonitor:
    def __init__(self, owner: str, position_limit: int) -> None:
        self._owner = owner
        self._position_limit = position_limit
        self._order_sizes: dict[int, int] = {}
        self._filled: defaultdict[int, int] = defaultdict(int)
        # Orders filled since the last check; an order's total only changes when it fills.
        self._unchecked: set[int] = set()

    def record_order(self, order_id: int, size: int) -> None:
        self._order_sizes[order_id] = size

    def record_fill(self, fill: Fill) -> None:
        self._filled[fill.maker_order_id] += fill.size
        self._unchecked.add(fill.maker_order_id)

    def check(self, book: OrderBook, account: Account) -> None:
        """Raise InvariantViolation on the first failing invariant."""
        if book.is_crossed():
            raise InvariantViolation(
                f"book is crossed: bid {book.best_bid()} >= ask {book.best_ask()}"
            )
        if abs(account.position) > self._position_limit:
            raise InvariantViolation(
                f"{self._owner} position {account.position} exceeds limit {self._position_limit}"
            )
        if not account.reconciles():
            raise InvariantViolation("position and cash do not reconcile with recorded fills")
        for order in book.open_orders(self._owner):
            if not 0 <= order.filled < order.size:
                raise InvariantViolation(
                    f"open order {order.id} has filled {order.filled} of size {order.size}"
                )
        for order_id in sorted(self._unchecked):
            filled = self._filled[order_id]
            size = self._order_sizes.get(order_id)
            if size is None or filled > size:
                raise InvariantViolation(
                    f"order {order_id} filled {filled} lots, more than its size {size}"
                )
        self._unchecked.clear()
