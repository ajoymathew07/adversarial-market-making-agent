import inspect
from dataclasses import replace

import mm.agent.calibration as calibration_module
import mm.simulation
from mm.agent import CalibrationMarketMaker, NaiveMarketMaker, Observation, Quote
from mm.agent.skew import skew_ticks
from mm.config import load_config
from mm.market import generate_intents
from mm.market.takers import TakerIntent
from mm.simulation import run_episode

CONFIG = load_config()
SETTINGS = CONFIG.agent.calibration
SKEW_PER_LOT = CONFIG.agent.skew.skew_per_lot
SIZE = CONFIG.risk.max_order_size
CENTRE = 10000


def observation(step: int = 1, position: int = 0) -> Observation:
    return Observation(
        step=step,
        position=position,
        cash=0,
        own_fills=(),
        last_step_trades=(),
        last_trade_price=CENTRE,
        posted_bid=None,
        posted_ask=None,
    )


def agent(seed: int = 0) -> CalibrationMarketMaker:
    return CalibrationMarketMaker(SETTINGS, SKEW_PER_LOT, SIZE, seed)


def quotes(maker: CalibrationMarketMaker, n: int, position: int = 0) -> list[Quote]:
    return [maker.quote(observation(step=t, position=position)) for t in range(n)]


def test_each_side_is_quoted_at_every_distance_independently_at_max_order_size():
    seen = quotes(agent(), 500)
    bids = {CENTRE - q.bid_price for q in seen if q.bid_price is not None}
    asks = {q.ask_price - CENTRE for q in seen if q.ask_price is not None}
    expected = set(range(SETTINGS.min_distance, SETTINGS.max_distance + 1))
    assert bids == asks == expected
    pairs = {(CENTRE - q.bid_price, q.ask_price - CENTRE) for q in seen}  # type: ignore[operator]
    assert len(pairs) == len(expected) ** 2  # every combination occurs: the sides are independent
    assert all((q.bid_size, q.ask_size) == (SIZE, SIZE) for q in seen)


def test_quotes_never_self_cross_and_centre_on_v1_skew():
    for position in range(-50, 51, 5):
        maker = agent()
        for quote in quotes(maker, 50, position):
            assert quote.bid_price is not None and quote.ask_price is not None
            assert quote.bid_price < quote.ask_price
        assert set(maker.centres) == {CENTRE - skew_ticks(position, SKEW_PER_LOT)}


def test_same_seed_repeats_and_another_seed_differs():
    assert quotes(agent(3), 100) == quotes(agent(3), 100)
    assert quotes(agent(3), 100) != quotes(agent(4), 100)


def test_step_zero_restarts_the_random_stream_and_the_log():
    maker = agent()
    first = quotes(maker, 20)
    assert quotes(maker, 20) == first
    assert len(maker.observations) == len(maker.centres) == 20


def test_market_path_and_takers_are_the_same_as_with_the_naive_agent(monkeypatch):
    seen: list[list[list[TakerIntent]]] = []

    def recording(*args):
        intents = generate_intents(*args)
        seen[-1].append(intents)
        return intents

    monkeypatch.setattr(mm.simulation, "generate_intents", recording)
    config = replace(load_config(scenario="toxic"), n_steps=300, seed=7)
    paths = []
    for maker in (NaiveMarketMaker(config.agent.naive), agent(config.seed)):
        seen.append([])
        paths.append(run_episode(config, agent=maker).path)
    assert paths[0] == paths[1]
    assert seen[0] == seen[1]


def test_full_episode_runs_through_the_registry_and_fills():
    config = replace(CONFIG, n_steps=500, agent=replace(CONFIG.agent, type="calibration"))
    episode = run_episode(config)
    assert episode.fills
    assert run_episode(config) == episode


def test_agent_uses_only_the_observation():
    source = inspect.getsource(calibration_module)
    assert "mm.market" not in source and "mm.simulation" not in source
