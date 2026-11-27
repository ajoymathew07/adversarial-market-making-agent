# 0001: Integer tick prices in the engine

**Status:** Accepted (2026-11-27)

## Context
The matching engine compares prices constantly: is a bid at or above the best ask, which orders
share a price level. Floats make these comparisons unreliable (`0.1 + 0.2 != 0.3`), and such a
bug would show up as a missed or wrong fill.

## Decision
Inside the engine every price is an integer number of ticks. Conversion to and from real prices
happens only at the edges: config input, the true-value process, and reports.

## Alternatives considered
- Floats with a tolerance: every comparison needs care, and one missed case breaks matching.
- `Decimal`: exact, but slower and easy to mix with floats by accident.

## Consequences
Matching and price-level keys are exact and fast. Every boundary needs an explicit, tested
conversion, and the tick size becomes a config value.
