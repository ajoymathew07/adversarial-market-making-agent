"""Quoting strategies and the interface they implement."""

from mm.agent.interface import Agent, Observation, OwnFill, Quote, Trade
from mm.agent.naive import NaiveMarketMaker

__all__ = ["Agent", "NaiveMarketMaker", "Observation", "OwnFill", "Quote", "Trade"]
