from dataclasses import replace

from mm.agent import NaiveMarketMaker, Observation, Quote
from mm.config import load_config

DEFAULT = load_config().agent


def observation(last_trade_price: int, position: int = 0) -> Observation:
    return Observation(
        step=0,
        position=position,
        cash=0,
        own_fills=(),
        last_step_trades=(),
        last_trade_price=last_trade_price,
    )


def test_quotes_centre_plus_minus_half_spread_with_quote_size():
    agent = NaiveMarketMaker(replace(DEFAULT, half_spread=3, quote_size=7))
    assert agent.quote(observation(10000)) == Quote(9997, 7, 10003, 7)


def test_default_config_quotes_two_ticks_and_five_lots():
    assert NaiveMarketMaker(DEFAULT).quote(observation(10000)) == Quote(9998, 5, 10002, 5)


def test_quote_follows_last_trade_price():
    agent = NaiveMarketMaker(DEFAULT)
    assert agent.quote(observation(10010)) == Quote(10008, 5, 10012, 5)


def test_quote_ignores_inventory():
    agent = NaiveMarketMaker(DEFAULT)
    assert agent.quote(observation(10000, position=40)) == agent.quote(observation(10000))
