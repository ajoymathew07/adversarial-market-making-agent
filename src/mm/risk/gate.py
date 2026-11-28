"""The single order gate: every agent quote passes through `apply_gate` before the engine."""

from dataclasses import dataclass

from mm.agent import Quote
from mm.config import RiskConfig
from mm.types import Side


@dataclass(frozen=True)
class GateEvent:
    """A side that the gate rejected or clipped."""

    side: Side
    rule: str  # "size", "price_band", "self_cross" or "position_clip"
    detail: str


@dataclass(frozen=True)
class GateResult:
    quote: Quote
    events: list[GateEvent]


def apply_gate(
    quote: Quote, position: int, last_trade_price: int, config: RiskConfig
) -> GateResult:
    """Return the accepted quote and an event for every rejected or clipped side.

    Rules, in order (a side with a None price is absent and skips every rule):
    1. size: a side with size < 1 or size > max_order_size is rejected.
    2. price_band: a side with |price - last_trade_price| > max_quote_distance is rejected.
    3. self_cross: if both sides remain and bid >= ask, both are rejected.
    4. position_clip: bid size is clipped to position_limit - position and ask size to
       position_limit + position, so even a complete fill keeps |position| <= limit.
       A side clipped to 0 is dropped.
    A rejected side is returned with price None and size 0.
    """
    events: list[GateEvent] = []
    bid = _check_side(Side.BUY, quote.bid_price, quote.bid_size, last_trade_price, config, events)
    ask = _check_side(Side.SELL, quote.ask_price, quote.ask_size, last_trade_price, config, events)

    if bid is not None and ask is not None and bid[0] >= ask[0]:
        detail = f"bid {bid[0]} >= ask {ask[0]}"
        events.append(GateEvent(Side.BUY, "self_cross", detail))
        events.append(GateEvent(Side.SELL, "self_cross", detail))
        bid = ask = None

    bid = _clip(Side.BUY, bid, config.position_limit - position, events)
    ask = _clip(Side.SELL, ask, config.position_limit + position, events)

    accepted = Quote(
        bid_price=bid[0] if bid else None,
        bid_size=bid[1] if bid else 0,
        ask_price=ask[0] if ask else None,
        ask_size=ask[1] if ask else 0,
    )
    return GateResult(accepted, events)


def _check_side(
    side: Side,
    price: int | None,
    size: int,
    last_trade_price: int,
    config: RiskConfig,
    events: list[GateEvent],
) -> tuple[int, int] | None:
    """Apply the size and price-band rules; return (price, size) or None if rejected."""
    if price is None:
        return None
    if not 1 <= size <= config.max_order_size:
        events.append(GateEvent(side, "size", f"size {size} outside 1..{config.max_order_size}"))
        return None
    distance = abs(price - last_trade_price)
    if distance > config.max_quote_distance:
        events.append(
            GateEvent(
                side,
                "price_band",
                f"price {price} is {distance} ticks from last trade {last_trade_price}",
            )
        )
        return None
    return price, size


def _clip(
    side: Side, level: tuple[int, int] | None, capacity: int, events: list[GateEvent]
) -> tuple[int, int] | None:
    """Clip the size to the remaining position capacity on this side; drop it at 0."""
    if level is None or level[1] <= capacity:
        return level
    price, size = level
    allowed = max(capacity, 0)
    events.append(GateEvent(side, "position_clip", f"size {size} clipped to {allowed}"))
    return (price, allowed) if allowed > 0 else None
