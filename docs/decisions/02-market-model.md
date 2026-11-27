# 02: Market model

## Who provides liquidity

Decision: **(A) only our agent quotes** in v0. Every trade is a taker hitting the agent.

| Option | Pros | Cons |
|--------|------|------|
| A. Agent is the only quoter | Simple; every fill is attributable to the agent's quotes; mirrors illiquid bond markets where one dealer infers value from client flow | No competition for flow |
| B. Scripted background market-maker bot | Competition for flow | Leaks the true value if it quotes around it; its behaviour must be defended as realistic |
| C. Zero-intelligence limit-order flow | Realistic book depth | Planned as a later second scenario; A stays so version-to-version comparisons remain valid |

## True value

Gaussian random walk in ticks: `V(t+1) = V(t) + sigma * eps`, `eps ~ N(0, 1)`. This is the
Avellaneda–Stoikov price model. V is a float and is not snapped to the tick grid. The whole path
is generated from the seed at the start of an episode. Jumps and regime switching are later
scenarios.

## Takers

- **Noise takers**: random side, exponential price tolerance with rate k. A buyer sends
  `floor(V + tolerance)`, a seller `ceil(V - tolerance)`, so P(fill at distance d) = e^(-k d),
  the Avellaneda–Stoikov fill model. k is set so a quote 2 ticks from V fills 30% of the time.
- **Informed takers**: see V ten steps ahead and trade only when their edge is at least 1 tick.
  This is the Glosten–Milgrom / Kyle adverse-selection mechanism the agent must defend against.

Arrivals per step are two independent Poisson counts, shuffled into random order.

## Defaults

| Parameter | Default |
|-----------|---------|
| V0 | 10000 ticks (100.00, tick 0.01) |
| sigma | 1 tick per step |
| Noise rate / size | 1 per step / 1–5 lots |
| Noise fill at 2 ticks | 30% (k ≈ 0.602) |
| Informed share / size | 15% / 5–10 lots |
| Informed lookahead / edge | 10 steps / 1 tick |

Scenarios differ only in informed share: `no_informed` 0%, `base` 15%, `toxic` 40%.

The agent never sees V or a taker's kind; only the simulation loop and evaluation read them.
