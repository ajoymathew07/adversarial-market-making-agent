"""One simulated episode: the step loop that wires market, agent, risk gate, engine and monitor.

Each step t: read V(t); the agent quotes; the gate filters the quote; the engine replaces the
agent's resting orders; takers arrive and trade; the monitor checks invariants; the step is
recorded. Takers arrive after the agent quotes, so every quote is exposed for a full step.
"""

from dataclasses import dataclass

import numpy as np

from mm.agent import Agent, Observation, OwnFill, Quote, Trade, make_agent
from mm.config import SimConfig
from mm.engine import Account, Fill, OrderBook
from mm.market import (
    TakerKind,
    generate_intents,
    generate_noise_rate_scale,
    generate_value_path,
)
from mm.risk import GateEvent, InvariantMonitor, apply_gate
from mm.types import Side

AGENT = "agent"
TAKER = "taker"


@dataclass(frozen=True)
class FillRecord:
    """An agent fill with the hidden context evaluation needs. `side` is the agent's side."""

    step: int
    true_value: float
    taker_kind: TakerKind
    side: Side
    price: int
    size: int
    maker_order_id: int


@dataclass(frozen=True)
class StepRecord:
    step: int
    true_value: float
    position: int
    cash: int
    bid_price: int | None  # the agent's posted bid after the gate, or None
    bid_size: int  # posted bid size after the gate; 0 when there is no bid
    ask_price: int | None
    ask_size: int
    fair_value: float  # the agent's own estimate of the true value, in ticks


@dataclass(frozen=True)
class GateLogEntry:
    step: int
    event: GateEvent


@dataclass
class EpisodeResult:
    path: tuple[float, ...]  # V(0..n_steps + lookahead), in ticks
    fills: list[FillRecord]
    steps: list[StepRecord]
    gate_events: list[GateLogEntry]
    final_position: int
    final_cash: int
    final_pnl: float  # ticks x lots: cash + position x V(n_steps)


def run_episode(config: SimConfig, agent: Agent | None = None) -> EpisodeResult:
    """Run one episode. Without an agent, the one named by config.agent.type is built."""
    if agent is None:
        agent = make_agent(config)
    rng = np.random.Generator(np.random.PCG64(config.seed))
    initial_value = config.instrument.initial_price_ticks
    path = generate_value_path(config.market, initial_value, config.n_steps, rng)
    # Drawn after the value path; draws nothing for Poisson arrivals, so base runs are unchanged.
    noise_rate_scale = generate_noise_rate_scale(config.market.noise, config.n_steps, rng)

    book = OrderBook()
    account = Account(fee_per_lot=config.engine.fee_per_lot)
    monitor = InvariantMonitor(AGENT, config.risk.position_limit)
    result = EpisodeResult(
        path=tuple(float(v) for v in path),
        fills=[],
        steps=[],
        gate_events=[],
        final_position=0,
        final_cash=0,
        final_pnl=0.0,
    )
    last_trade_price = initial_value
    previous_fills: list[Fill] = []
    posted: Quote | None = None  # the gated quote that rested last step; none at step 0

    for t in range(config.n_steps):
        value = float(path[t])
        obs = _observe(t, account, previous_fills, last_trade_price, posted)
        gated = apply_gate(agent.quote(obs), account.position, last_trade_price, config.risk)
        result.gate_events += [GateLogEntry(t, event) for event in gated.events]
        _replace_quotes(book, monitor, gated.quote)

        step_fills: list[Fill] = []
        scale = float(noise_rate_scale[t])
        for intent in generate_intents(path, t, config.market, rng, scale):
            fills = book.match_ioc(TAKER, intent.side, intent.limit_price, intent.size, intent.kind)
            for fill in fills:
                account.apply_fill(fill, as_owner=AGENT)
                monitor.record_fill(fill)
                result.fills.append(_fill_record(t, value, intent.kind, fill))
                step_fills.append(fill)

        monitor.check(book, account)
        if step_fills:
            last_trade_price = step_fills[-1].price
        previous_fills = step_fills
        posted = gated.quote
        result.steps.append(
            StepRecord(
                step=t,
                true_value=value,
                position=account.position,
                cash=account.cash,
                bid_price=gated.quote.bid_price,
                bid_size=gated.quote.bid_size,
                ask_price=gated.quote.ask_price,
                ask_size=gated.quote.ask_size,
                fair_value=gated.quote.fair_value,
            )
        )

    result.final_position = account.position
    result.final_cash = account.cash
    result.final_pnl = account.mark_to(float(path[config.n_steps]))
    return result


def _observe(
    t: int,
    account: Account,
    previous_fills: list[Fill],
    last_trade_price: int,
    posted: Quote | None,
) -> Observation:
    """Build the agent's view from engine state only: no true value, no taker kind."""
    return Observation(
        step=t,
        position=account.position,
        cash=account.cash,
        own_fills=tuple(OwnFill(f.taker_side.opposite, f.price, f.size) for f in previous_fills),
        last_step_trades=tuple(Trade(f.price, f.size) for f in previous_fills),
        last_trade_price=last_trade_price,
        posted_bid=posted.bid_price if posted is not None else None,
        posted_ask=posted.ask_price if posted is not None else None,
    )


def _replace_quotes(book: OrderBook, monitor: InvariantMonitor, quote: Quote) -> None:
    book.cancel_all(AGENT)
    if quote.bid_price is not None:
        order_id = book.add_limit(AGENT, Side.BUY, quote.bid_price, quote.bid_size)
        monitor.record_order(order_id, quote.bid_size)
    if quote.ask_price is not None:
        order_id = book.add_limit(AGENT, Side.SELL, quote.ask_price, quote.ask_size)
        monitor.record_order(order_id, quote.ask_size)


def _fill_record(t: int, value: float, kind: TakerKind, fill: Fill) -> FillRecord:
    return FillRecord(
        step=t,
        true_value=value,
        taker_kind=kind,
        side=fill.taker_side.opposite,
        price=fill.price,
        size=fill.size,
        maker_order_id=fill.maker_order_id,
    )
