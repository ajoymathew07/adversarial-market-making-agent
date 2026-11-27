"""Conversion between integer ticks (engine) and display prices."""


def ticks_to_price(ticks: int, tick_size: float) -> float:
    return ticks * tick_size


def price_to_ticks(price: float, tick_size: float) -> int:
    """Round to the nearest tick, so float noise like 100.00999 still maps to 10001."""
    return round(price / tick_size)
