"""Position and cash accounting from fills."""

from dataclasses import dataclass, field

from mm.engine.orders import Fill, Side


@dataclass
class Account:
    """Position in lots and cash in ticks x lots, both exact integers."""

    fee_per_lot: int = 0
    position: int = 0
    cash: int = 0
    # Each applied fill with the owner whose perspective it was applied from.
    fills: list[tuple[Fill, str]] = field(default_factory=list)

    def apply_fill(self, fill: Fill, as_owner: str) -> None:
        signed_size = _signed_size(fill, as_owner)
        self.position += signed_size
        self.cash += self._cash_change(fill, signed_size)
        self.fills.append((fill, as_owner))

    def mark_to(self, value_ticks: float) -> float:
        return self.cash + self.position * value_ticks

    def reconciles(self) -> bool:
        """Recompute position and cash from the recorded fills and compare."""
        position = 0
        cash = 0
        for fill, as_owner in self.fills:
            signed_size = _signed_size(fill, as_owner)
            position += signed_size
            cash += self._cash_change(fill, signed_size)
        return position == self.position and cash == self.cash

    def _cash_change(self, fill: Fill, signed_size: int) -> int:
        return -signed_size * fill.price - self.fee_per_lot * fill.size


def _signed_size(fill: Fill, as_owner: str) -> int:
    """Lots bought (+) or sold (-) by `as_owner` in this fill."""
    if as_owner == fill.taker_owner:
        side = fill.taker_side
    elif as_owner == fill.maker_owner:
        side = Side.SELL if fill.taker_side is Side.BUY else Side.BUY
    else:
        raise ValueError(f"{as_owner!r} is not a party to this fill")
    return fill.size if side is Side.BUY else -fill.size
