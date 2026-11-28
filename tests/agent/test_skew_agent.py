from dataclasses import replace

import pytest

from mm.agent import InventorySkewMarketMaker, NaiveMarketMaker, Observation, Quote
from mm.agent.skew import skew_ticks
from mm.config import load_config
from mm.simulation import run_episode

CONFIG = load_config()
DEFAULT = CONFIG.agent.skew
CENTRE = 10000


def observation(position: int, last_trade_price: int = CENTRE) -> Observation:
    return Observation(
        step=0,
        position=position,
        cash=0,
        own_fills=(),
        last_step_trades=(),
        last_trade_price=last_trade_price,
    )


def with_skew_per_lot(skew_per_lot: float) -> InventorySkewMarketMaker:
    # sigma = 1 and horizon = 1, so gamma is the skew per lot.
    return InventorySkewMarketMaker(replace(DEFAULT, gamma=skew_per_lot, sigma=1.0, horizon=1))


def test_flat_position_quotes_like_the_naive_agent():
    naive = NaiveMarketMaker(CONFIG.agent.naive)
    assert InventorySkewMarketMaker(DEFAULT).quote(observation(0)) == naive.quote(observation(0))


def test_long_moves_both_quotes_down_and_short_moves_them_up():
    agent = with_skew_per_lot(0.1)  # 30 lots long -> shift 3 ticks
    assert agent.quote(observation(30)) == Quote(9995, 5, 9999, 5)
    assert agent.quote(observation(-30)) == Quote(10001, 5, 10005, 5)


@pytest.mark.parametrize(
    ("position", "skew_per_lot", "expected_shift"),
    [
        (10, 0.1, 1),
        (14, 0.1, 1),  # 1.4 rounds down
        (16, 0.1, 2),  # 1.6 rounds up
        (-16, 0.1, -2),
        (1, 0.5, 1),  # exact half: away from zero
        (-1, 0.5, -1),
        (3, 0.5, 2),  # 1.5 -> 2
        (5, 0.5, 3),  # 2.5 -> 3, not Python round()'s even 2
        (-5, 0.5, -3),
        (1, 0.25, 0),
        (50, 0.02, 1),
        (0, 0.5, 0),
    ],
)
def test_shift_is_position_times_skew_rounded_halves_away_from_zero(
    position, skew_per_lot, expected_shift
):
    assert skew_ticks(position, skew_per_lot) == expected_shift
    quote = with_skew_per_lot(skew_per_lot).quote(observation(position))
    assert quote.bid_price == CENTRE - expected_shift - DEFAULT.half_spread
    assert quote.ask_price == CENTRE - expected_shift + DEFAULT.half_spread


@pytest.mark.parametrize("half_spread", [1, 2, 5])
@pytest.mark.parametrize("skew_per_lot", [0.0, 0.1, 0.37, 0.5, 2.0])
def test_quotes_never_self_cross(half_spread, skew_per_lot):
    config = replace(DEFAULT, half_spread=half_spread, gamma=skew_per_lot, sigma=1.0, horizon=1)
    agent = InventorySkewMarketMaker(config)
    for position in range(-50, 51):
        quote = agent.quote(observation(position))
        assert quote.bid_price is not None and quote.ask_price is not None
        assert quote.bid_price < quote.ask_price


def test_sizes_are_not_skewed():
    quote = InventorySkewMarketMaker(DEFAULT).quote(observation(40))
    assert (quote.bid_size, quote.ask_size) == (DEFAULT.quote_size, DEFAULT.quote_size)


def test_zero_gamma_episode_is_identical_to_the_naive_episode():
    config = replace(load_config(scenario="toxic"), n_steps=500)
    naive = run_episode(config, NaiveMarketMaker(config.agent.naive))
    skew = run_episode(config, InventorySkewMarketMaker(replace(config.agent.skew, gamma=0.0)))
    assert skew.fills == naive.fills
    assert skew.steps == naive.steps
    assert skew.final_pnl == naive.final_pnl


def test_default_skew_stays_inside_the_gate_price_band():
    config = load_config(scenario="toxic")
    assert DEFAULT.skew_per_lot * config.risk.position_limit + DEFAULT.half_spread < (
        config.risk.max_quote_distance
    )
    episode = run_episode(config, InventorySkewMarketMaker(config.agent.skew))
    assert not [e for e in episode.gate_events if e.event.rule == "price_band"]
