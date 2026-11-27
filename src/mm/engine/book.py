"""Limit order book with price-time priority.

Each side is a dict from price to a FIFO deque of orders, plus a sorted list of the
prices that have orders. Resting orders are post-only; takers send IOC limit orders.
"""

import bisect
from collections import deque

from mm.engine.orders import Fill, Order
from mm.types import Side


class OrderBook:
    def __init__(self) -> None:
        self._levels: dict[Side, dict[int, deque[Order]]] = {Side.BUY: {}, Side.SELL: {}}
        # Ascending on both sides: best bid is the last bid price, best ask the first ask.
        self._prices: dict[Side, list[int]] = {Side.BUY: [], Side.SELL: []}
        self._orders: dict[int, Order] = {}
        self._next_id = 1

    def best_bid(self) -> int | None:
        bids = self._prices[Side.BUY]
        return bids[-1] if bids else None

    def best_ask(self) -> int | None:
        asks = self._prices[Side.SELL]
        return asks[0] if asks else None

    def is_crossed(self) -> bool:
        bid, ask = self.best_bid(), self.best_ask()
        return bid is not None and ask is not None and bid >= ask

    def open_orders(self, owner: str) -> list[Order]:
        return [order for order in self._orders.values() if order.owner == owner]

    def add_limit(self, owner: str, side: Side, price: int, size: int) -> int:
        """Rest a post-only limit order and return its id. Raises if it would cross."""
        if size < 1:
            raise ValueError(f"order size must be >= 1, got {size}")
        if self._would_cross(side, price):
            # The risk gate should make this impossible, so it signals a bug upstream.
            raise ValueError(f"{side.name} limit at {price} would cross the book")

        order = Order(id=self._next_id, owner=owner, side=side, price=price, size=size)
        self._next_id += 1
        self._orders[order.id] = order
        levels = self._levels[side]
        if price not in levels:
            levels[price] = deque()
            bisect.insort(self._prices[side], price)
        levels[price].append(order)
        return order.id

    def cancel(self, order_id: int) -> bool:
        """Remove a resting order. False if the id is unknown or already fully filled."""
        order = self._orders.pop(order_id, None)
        if order is None:
            return False
        level = self._levels[order.side][order.price]
        level.remove(order)
        if not level:
            self._remove_level(order.side, order.price)
        return True

    def cancel_all(self, owner: str) -> int:
        """Cancel every resting order of an owner and return how many were cancelled."""
        ids = [order.id for order in self.open_orders(owner)]
        for order_id in ids:
            self.cancel(order_id)
        return len(ids)

    def match_ioc(
        self, owner: str, side: Side, limit_price: int, size: int, tag: str
    ) -> list[Fill]:
        """Fill up to `size` against resting orders priced at or better than `limit_price`.

        Trades happen at the resting order's price. Any unfilled remainder is dropped.
        """
        if size < 1:
            raise ValueError(f"order size must be >= 1, got {size}")

        maker_side = side.opposite
        fills: list[Fill] = []
        remaining = size
        while remaining > 0:
            price = self.best_ask() if side is Side.BUY else self.best_bid()
            if price is None or not _within_limit(side, price, limit_price):
                break
            level = self._levels[maker_side][price]
            maker = level[0]
            traded = min(remaining, maker.remaining)
            maker.filled += traded
            remaining -= traded
            fills.append(
                Fill(
                    taker_owner=owner,
                    maker_owner=maker.owner,
                    maker_order_id=maker.id,
                    taker_side=side,
                    price=price,
                    size=traded,
                    taker_tag=tag,
                )
            )
            if maker.remaining == 0:
                level.popleft()
                del self._orders[maker.id]
                if not level:
                    self._remove_level(maker_side, price)
        return fills

    def _would_cross(self, side: Side, price: int) -> bool:
        if side is Side.BUY:
            ask = self.best_ask()
            return ask is not None and price >= ask
        bid = self.best_bid()
        return bid is not None and price <= bid

    def _remove_level(self, side: Side, price: int) -> None:
        del self._levels[side][price]
        prices = self._prices[side]
        prices.pop(bisect.bisect_left(prices, price))


def _within_limit(taker_side: Side, price: int, limit_price: int) -> bool:
    return price <= limit_price if taker_side is Side.BUY else price >= limit_price
