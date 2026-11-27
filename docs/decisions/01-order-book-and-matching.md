# 01: Order book and matching

## Decision

- **Discrete steps.** The simulation advances in fixed steps; within a step, orders are processed in sequence.
- **Minimal limit order book.** Bids and asks, each a dict from price to a FIFO queue, plus a sorted price list.
- **Price-time priority.** Best price first; at the same price, earliest order first.
- **Maker-price execution.** A trade happens at the resting order's price.
- **Partial fills.** A resting order's remainder stays in the book.
- **Takers send IOC limit orders.** They match at or better than their limit; the unfilled remainder is cancelled.
- **Resting orders are post-only.** A resting order that would cross the book raises an error. The risk gate prevents this upstream, so an error means a bug. The book is never crossed.
- **No fees in v0.** `fee_per_lot` (ticks per filled lot) exists in config and accounting, set to 0.

## Why

This is the smallest model with a real book: it lets us state and test the core invariants (no double fills, uncrossed book, PnL reconciles) directly. Price-time priority and maker-price execution are how most exchanges work and are easy to explain. IOC takers keep the book holding only the agent's quotes, so every fill is attributable. Keeping fees as a zero-valued parameter means turning them on later is a config change.

## Rejected

- **Event-driven continuous time:** more complex (event queue, latencies) and not needed to study adverse selection.
- **Quote-driven model without a real book:** simpler at first, but it would need replacing for the tournament and could not express the no-double-fill and uncrossed-book invariants.
