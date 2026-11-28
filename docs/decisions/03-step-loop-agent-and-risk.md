# 03: Step loop, v0 agent and risk

## Step loop

The true-value path is generated once per episode from the seed, then each step t runs:

1. Read V(t).
2. The agent gets an observation and returns a quote.
3. The order gate accepts, clips or rejects each side and logs why.
4. The engine cancels the agent's resting orders and posts the accepted bid and ask.
5. Takers arrive and trade against the book; every fill is applied to the agent's account.
6. The invariant monitor checks the state; a violation halts the run.
7. The step is recorded.

Final PnL is cash plus inventory marked at V(n_steps). One seeded generator draws the path first,
then the takers, so a seed reproduces an episode exactly.

The agent quotes before takers arrive, so each quote is exposed for a full step: a one-step
latency. The reverse order would let the agent react to flow before it is filled and would
understate adverse selection.

## Agent interface

The agent returns a `Quote`: one price and size per side, or no order on a side. Full order
management (place, amend, cancel) was rejected for v0: it adds failure modes, and with one market
maker queue position does not matter. The agent sees its position, cash, its own last-step fills,
last-step public trades and the last trade price. It never sees V or a taker's kind.

## v0 agent

Centre on the last trade price, quote 2 ticks either side, 5 lots per side, no inventory
awareness. It is a deliberately simple baseline; its losses to informed flow and its inventory
drift motivate v1+.

## Order gate

Values (`[risk]` in `config/default.toml`): position limit 50, max order size 10, max quote distance 50 ticks from the last trade.
Per side: reject size outside 1..10, reject prices outside the band, reject both sides if
bid >= ask, then clip the bid to `limit - position` and the ask to `limit + position`. Since the
clip assumes the whole order fills, a breach of the position limit is impossible by construction.

## Invariant monitor

After every step: book not crossed, |position| <= limit, position and cash reconcile with the
recorded fills, and no order is ever filled beyond its original size.
