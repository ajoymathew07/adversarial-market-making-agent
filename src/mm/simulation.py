"""One simulated episode: the step loop that wires market, agent, risk gate, engine and monitor.

Each step t: read V(t); the agent quotes; the gate filters the quote; the engine replaces the
agent's resting orders; takers arrive and trade; the monitor checks invariants; the step is
recorded. Takers arrive after the agent quotes, so every quote is exposed for a full step.

With a competitor (decision 12) both makers cancel, then post in an order drawn from their own
stream; each has its own account, gate call and monitor, and takers fill best price first, then
FIFO, across both.
"""

from dataclasses import dataclass, field, replace

import numpy as np

from mm.agent import AGENT_NAMES, Agent, Observation, OwnFill, Quote, Trade, make_agent
from mm.config import NO_COMPETITOR, ConfigError, SimConfig
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
COMPETITOR = "competitor"
TAKER = "taker"
COMPETITOR_FIRST_PROB = 0.5  # each step, the chance the competitor posts first (decision 12)


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
    # The competing maker's own record, same format and same path; None without one.
    competitor: "EpisodeResult | None" = None
    # Per step: True when the competitor posted first (time priority at equal prices).
    competitor_first: list[bool] = field(default_factory=list)


class _Maker:
    """One market maker's state: its agent, account, monitor and what it posted."""

    def __init__(self, owner: str, agent: Agent, config: SimConfig, path: tuple[float, ...]):
        self.owner = owner
        self.agent = agent
        self.account = Account(fee_per_lot=config.engine.fee_per_lot)
        self.monitor = InvariantMonitor(owner, config.risk.position_limit)
        self.previous_fills: list[Fill] = []
        self.step_fills: list[Fill] = []
        self.posted: Quote | None = None  # the gated quote that rested last step; none at step 0
        self.result = EpisodeResult(
            path=path,
            fills=[],
            steps=[],
            gate_events=[],
            final_position=0,
            final_cash=0,
            final_pnl=0.0,
        )


def run_episode(
    config: SimConfig, agent: Agent | None = None, competitor: Agent | None = None
) -> EpisodeResult:
    """Run one episode. Without an agent, the one named by config.agent.type is built.

    With market.competitor set (or a `competitor` agent given), a second maker quotes in the
    same book; its record is `result.competitor`.
    """
    if agent is None:
        agent = make_agent(config)
    if competitor is None and config.market.competitor != NO_COMPETITOR:
        competitor = _make_competitor(config)
    rng = np.random.Generator(np.random.PCG64(config.seed))
    initial_value = config.instrument.initial_price_ticks
    path = generate_value_path(config.market, initial_value, config.n_steps, rng)
    # Drawn after the value path; draws nothing for Poisson arrivals, so base runs are unchanged.
    noise_rate_scale = generate_noise_rate_scale(config.market.noise, config.n_steps, rng)
    path_ticks = tuple(float(v) for v in path)

    book = OrderBook()
    ours = _Maker(AGENT, agent, config, path_ticks)
    makers = [ours]
    order_rng: np.random.Generator | None = None
    if competitor is not None:
        makers.append(_Maker(COMPETITOR, competitor, config, path_ticks))
        # A separate stream, so the market's draws are the same with or without a competitor.
        stream = config.market.posting_order_stream
        order_rng = np.random.Generator(np.random.PCG64([config.seed, stream]))
    by_owner = {maker.owner: maker for maker in makers}
    last_trade_price = initial_value
    public_trades: tuple[Trade, ...] = ()

    for t in range(config.n_steps):
        value = float(path[t])
        posting = makers
        if order_rng is not None:
            competitor_first = bool(order_rng.random() < COMPETITOR_FIRST_PROB)
            ours.result.competitor_first.append(competitor_first)
            posting = makers[::-1] if competitor_first else makers
        # Every maker cancels first, so each one's gate sees only the others' new orders.
        for maker in makers:
            book.cancel_all(maker.owner)
        for maker in posting:
            obs = _observe(t, maker, public_trades, last_trade_price)
            gated = apply_gate(
                maker.agent.quote(obs),
                maker.account.position,
                last_trade_price,
                config.risk,
                book_bid=book.best_bid(),
                book_ask=book.best_ask(),
            )
            maker.result.gate_events += [GateLogEntry(t, event) for event in gated.events]
            _post_quotes(book, maker, gated.quote)
            maker.posted = gated.quote

        step_fills: list[Fill] = []
        scale = float(noise_rate_scale[t])
        for intent in generate_intents(path, t, config.market, rng, scale):
            fills = book.match_ioc(TAKER, intent.side, intent.limit_price, intent.size, intent.kind)
            for fill in fills:
                maker = by_owner[fill.maker_owner]
                maker.account.apply_fill(fill, as_owner=maker.owner)
                maker.monitor.record_fill(fill)
                maker.result.fills.append(_fill_record(t, value, intent.kind, fill))
                maker.step_fills.append(fill)
                step_fills.append(fill)

        for maker in makers:
            maker.monitor.check(book, maker.account)
            maker.previous_fills, maker.step_fills = maker.step_fills, []
            maker.result.steps.append(_step_record(t, value, maker))
        if step_fills:
            last_trade_price = step_fills[-1].price
        public_trades = tuple(Trade(f.price, f.size) for f in step_fills)

    final_value = float(path[config.n_steps])
    for maker in makers:
        maker.result.final_position = maker.account.position
        maker.result.final_cash = maker.account.cash
        maker.result.final_pnl = maker.account.mark_to(final_value)
    if len(makers) > 1:
        ours.result.competitor = makers[1].result
    return ours.result


def _make_competitor(config: SimConfig) -> Agent:
    """Build market.competitor from the registry, with the same [agent.*] sections."""
    name = config.market.competitor
    if name not in AGENT_NAMES:
        raise ConfigError(
            f"unknown market.competitor {name!r}; known: {NO_COMPETITOR}, {', '.join(AGENT_NAMES)}"
        )
    return make_agent(replace(config, agent=replace(config.agent, type=name)))


def _observe(
    t: int, maker: _Maker, public_trades: tuple[Trade, ...], last_trade_price: int
) -> Observation:
    """Build one maker's view from engine state only: no true value, no taker kind, and no
    other maker's quotes. Public trades include every maker's fills."""
    posted = maker.posted
    return Observation(
        step=t,
        position=maker.account.position,
        cash=maker.account.cash,
        own_fills=tuple(
            OwnFill(f.taker_side.opposite, f.price, f.size) for f in maker.previous_fills
        ),
        last_step_trades=public_trades,
        last_trade_price=last_trade_price,
        posted_bid=posted.bid_price if posted is not None else None,
        posted_ask=posted.ask_price if posted is not None else None,
    )


def _post_quotes(book: OrderBook, maker: _Maker, quote: Quote) -> None:
    if quote.bid_price is not None:
        order_id = book.add_limit(maker.owner, Side.BUY, quote.bid_price, quote.bid_size)
        maker.monitor.record_order(order_id, quote.bid_size)
    if quote.ask_price is not None:
        order_id = book.add_limit(maker.owner, Side.SELL, quote.ask_price, quote.ask_size)
        maker.monitor.record_order(order_id, quote.ask_size)


def _step_record(t: int, value: float, maker: _Maker) -> StepRecord:
    quote = maker.posted
    assert quote is not None  # every maker posts (possibly nothing) before takers arrive
    return StepRecord(
        step=t,
        true_value=value,
        position=maker.account.position,
        cash=maker.account.cash,
        bid_price=quote.bid_price,
        bid_size=quote.bid_size,
        ask_price=quote.ask_price,
        ask_size=quote.ask_size,
        fair_value=quote.fair_value,
    )


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
