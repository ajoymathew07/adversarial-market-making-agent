"""What the agent sees and what it returns. The agent never sees the true value or taker kinds."""

from dataclasses import dataclass
from typing import Protocol

from mm.types import Side


@dataclass(frozen=True)
class OwnFill:
    """One of the agent's fills. `side` is from the agent's perspective."""

    side: Side
    price: int
    size: int


@dataclass(frozen=True)
class Trade:
    """A public trade print: price and size only."""

    price: int
    size: int


@dataclass(frozen=True)
class Observation:
    step: int
    position: int
    cash: int
    own_fills: tuple[OwnFill, ...]  # the agent's fills in the previous step
    last_step_trades: tuple[Trade, ...]  # all public trades in the previous step
    # Price of the most recent trade; the public starting valuation until the first trade.
    last_trade_price: int


@dataclass(frozen=True)
class Quote:
    """One price level per side. A None price means no order on that side."""

    bid_price: int | None
    bid_size: int
    ask_price: int | None
    ask_size: int


class Agent(Protocol):
    def quote(self, obs: Observation) -> Quote: ...
