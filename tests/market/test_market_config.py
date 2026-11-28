import math
from dataclasses import replace

import pytest

from mm.config import load_config, scenario_names

BASE = load_config().market


def test_noise_tolerance_rate_gives_30_percent_fill_at_2_ticks():
    k = BASE.noise.tolerance_rate
    assert k == pytest.approx(0.602, abs=1e-3)
    assert math.exp(-k * 2) == pytest.approx(0.30)


def test_informed_rate_makes_informed_the_configured_share_of_takers():
    config = replace(
        BASE, noise=replace(BASE.noise, rate=2.0), informed=replace(BASE.informed, share=0.4)
    )
    total = config.noise.rate + config.informed_rate
    assert config.informed_rate / total == pytest.approx(0.4)


def test_zero_informed_share_gives_zero_informed_rate():
    assert replace(BASE, informed=replace(BASE.informed, share=0.0)).informed_rate == 0.0


@pytest.mark.parametrize(
    ("part", "bad"),
    [
        ("true_value", {"sigma": -0.1}),
        ("noise", {"rate": -1.0}),
        ("noise", {"fill_prob_at_2_ticks": 0.0}),
        ("noise", {"fill_prob_at_2_ticks": 1.0}),
        ("noise", {"size_min": 0}),
        ("noise", {"size_min": 6, "size_max": 5}),
        ("informed", {"share": -0.1}),
        ("informed", {"share": 1.0}),
        ("informed", {"lookahead": 0}),
        ("informed", {"edge_threshold": -1.0}),
        ("informed", {"size_min": 0}),
        ("informed", {"size_min": 11, "size_max": 10}),
    ],
)
def test_config_rejects_out_of_range_values(part, bad):
    with pytest.raises(ValueError):
        replace(getattr(BASE, part), **bad)


def test_informed_scenarios_differ_only_in_informed_share():
    base = load_config()
    names = [n for n in scenario_names() if load_config(scenario=n).market.noise == BASE.noise]
    shares = {name: load_config(scenario=name).market.informed.share for name in names}
    assert shares == {"no_informed": 0.0, "base": 0.15, "toxic": 0.40}
    for name, share in shares.items():
        informed = replace(base.market.informed, share=share)
        assert load_config(scenario=name) == replace(
            base, market=replace(base.market, informed=informed)
        )
