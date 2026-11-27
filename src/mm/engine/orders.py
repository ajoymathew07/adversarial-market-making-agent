"""Order and fill records."""

from dataclasses import dataclass

from mm.types import Side


@dataclass
class Order:
    """A resting limit order. Price in ticks, size in lots."""

    id: int
    owner: str
    side: Side
    price: int
    size: int
    filled: int = 0

    @property
    def remaining(self) -> int:
        return self.size - self.filled


@dataclass(frozen=True)
class Fill:
    """One match between a taker IOC order and a resting maker order, at the maker's price."""

    taker_owner: str
    maker_owner: str
    maker_order_id: int
    taker_side: Side
    price: int
    size: int
    # Free-form label from the taker (e.g. "noise", "informed"); for evaluation only.
    taker_tag: str
