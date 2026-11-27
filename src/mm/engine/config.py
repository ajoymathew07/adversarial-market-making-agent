"""Engine configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EngineConfig:
    # Price of one tick, quoted per 100 face value (10000 ticks -> 100.00).
    tick_size: float = 0.01
    # Fee charged per filled lot, in ticks. Zero in v0.
    fee_per_lot: int = 0
