"""Quoting strategies, the interface they implement and the registry that builds them by name."""

from mm.agent.adaptive import AdaptiveMarketMaker
from mm.agent.calibration import CalibrationMarketMaker
from mm.agent.interface import Agent, Observation, OwnFill, Quote, Trade
from mm.agent.kalman import KalmanMarketMaker
from mm.agent.naive import NaiveMarketMaker
from mm.agent.registry import AGENT_NAMES, make_agent
from mm.agent.skew import InventorySkewMarketMaker
from mm.agent.toxicity import ToxicityMarketMaker

__all__ = [
    "AGENT_NAMES",
    "AdaptiveMarketMaker",
    "Agent",
    "CalibrationMarketMaker",
    "InventorySkewMarketMaker",
    "KalmanMarketMaker",
    "NaiveMarketMaker",
    "Observation",
    "OwnFill",
    "Quote",
    "ToxicityMarketMaker",
    "Trade",
    "make_agent",
]
