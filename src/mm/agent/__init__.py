"""Quoting strategies, the interface they implement and the registry that builds them by name."""

from mm.agent.interface import Agent, Observation, OwnFill, Quote, Trade
from mm.agent.kalman import KalmanMarketMaker
from mm.agent.naive import NaiveMarketMaker
from mm.agent.registry import AGENT_NAMES, make_agent
from mm.agent.skew import InventorySkewMarketMaker

__all__ = [
    "AGENT_NAMES",
    "Agent",
    "InventorySkewMarketMaker",
    "KalmanMarketMaker",
    "NaiveMarketMaker",
    "Observation",
    "OwnFill",
    "Quote",
    "Trade",
    "make_agent",
]
