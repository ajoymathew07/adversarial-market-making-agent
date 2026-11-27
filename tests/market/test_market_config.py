import math

import pytest

from mm.market import SCENARIOS, MarketConfig


def test_noise_tolerance_rate_gives_30_percent_fill_at_2_ticks():
    k = MarketConfig().noise_tolerance_rate
    assert k == pytest.approx(0.602, abs=1e-3)
    assert math.exp(-k * 2) == pytest.approx(0.30)


def test_informed_rate_makes_informed_the_configured_share_of_takers():
    config = MarketConfig(noise_rate=2.0, informed_share=0.4)
    total = config.noise_rate + config.informed_rate
    assert config.informed_rate / total == pytest.approx(0.4)


def test_zero_informed_share_gives_zero_informed_rate():
    assert MarketConfig(informed_share=0.0).informed_rate == 0.0


@pytest.mark.parametrize(
    "bad",
    [
        {"tick_size": 0.0},
        {"sigma": -0.1},
        {"noise_rate": -1.0},
        {"fill_prob_at_2_ticks": 0.0},
        {"fill_prob_at_2_ticks": 1.0},
        {"informed_share": -0.1},
        {"informed_share": 1.0},
        {"informed_lookahead": 0},
        {"informed_edge_threshold": -1.0},
        {"noise_size_min": 0},
        {"noise_size_min": 6, "noise_size_max": 5},
        {"informed_size_min": 0},
        {"informed_size_min": 11, "informed_size_max": 10},
    ],
)
def test_config_rejects_out_of_range_values(bad):
    with pytest.raises(ValueError):
        MarketConfig(**bad)


def test_scenarios_differ_only_in_informed_share():
    assert SCENARIOS["no_informed"].informed_share == 0.0
    assert SCENARIOS["base"].informed_share == 0.15
    assert SCENARIOS["toxic"].informed_share == 0.40
    for config in SCENARIOS.values():
        assert config == MarketConfig(informed_share=config.informed_share)
