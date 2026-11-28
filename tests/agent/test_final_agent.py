import json
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from mm.agent import AGENT_NAMES, AdaptiveMarketMaker, KalmanMarketMaker, make_agent
from mm.config import DEFAULT_CONFIG_PATH, FinalConfig, build_config, load_config, scenario_names
from mm.simulation import run_episode

CONFIG = load_config()
DOCKERFILE = Path(__file__).resolve().parents[2] / "Dockerfile"
# The tests' own settings, so they do not depend on the tuned values in the config file.
CONTROL_KNOBS = FinalConfig(
    base_half_spread=CONFIG.agent.kalman_tuned.half_spread,
    skew_per_lot=CONFIG.agent.skew.skew_per_lot,
    quote_size=CONFIG.agent.skew.quote_size,
    uncertainty_weight=0.0,
    intensity_halflife=0.0,
    min_scale=0.25,
    max_scale=4.0,
    max_half_spread=8,
    widen_per_tick=0.0,
    markout_horizon=5,
    ewma_halflife=50.0,
)
EVERYTHING_ON = replace(
    CONTROL_KNOBS,
    base_half_spread=3,
    skew_per_lot=0.1,
    quote_size=8,
    uncertainty_weight=1.0,
    intensity_halflife=20.0,
    widen_per_tick=2.0,
)


def final_config(final: FinalConfig, scenario: str = "base", n_steps: int = 1000, seed: int = 4):
    config = replace(load_config(scenario=scenario), n_steps=n_steps, seed=seed)
    return replace(config, agent=replace(config.agent, type="final", final=final))


@pytest.mark.parametrize("scenario", ["no_informed", "base", "toxic", "realistic_mix"])
def test_final_agent_with_the_controls_knobs_equals_the_control(scenario):
    config = final_config(CONTROL_KNOBS, scenario)
    control = replace(config, agent=replace(config.agent, type="kalman_tuned"))
    assert run_episode(config) == run_episode(control)
    v2 = KalmanMarketMaker(replace(CONFIG.agent.skew, half_spread=4), CONFIG.agent.kalman)
    assert run_episode(config) == run_episode(config, v2)


def test_final_agent_uses_its_own_skew_and_size_not_skew_sections():
    config = final_config(EVERYTHING_ON, n_steps=200)
    result = run_episode(config)
    assert {s.bid_size for s in result.steps if s.bid_price is not None} <= {8}
    assert isinstance(make_agent(config), AdaptiveMarketMaker)


def test_toxicity_widening_changes_the_quotes():
    no_c = final_config(replace(EVERYTHING_ON, widen_per_tick=0.0), "toxic", n_steps=1000)
    with_c = final_config(EVERYTHING_ON, "toxic", n_steps=1000)
    spreads = [
        [s.ask_price - s.bid_price for s in run_episode(c).steps if s.ask_price and s.bid_price]
        for c in (no_c, with_c)
    ]
    assert spreads[0] != spreads[1]


@pytest.mark.parametrize("scenario", scenario_names())
def test_invariant_monitor_passes_a_full_episode_in_every_scenario(scenario):
    result = run_episode(final_config(EVERYTHING_ON, scenario, n_steps=CONFIG.n_steps))
    assert len(result.steps) == CONFIG.n_steps  # the monitor halts the run on any violation


def test_registry_builds_the_final_agent_and_it_is_the_default():
    assert "final" in AGENT_NAMES
    assert CONFIG.agent.type == "final"
    assert isinstance(make_agent(CONFIG), AdaptiveMarketMaker)


@pytest.mark.skipif(
    not DOCKERFILE.exists(), reason="the Dockerfile is not copied into the image; CI's static job runs this"
)
def test_make_run_evaluates_v1_v2_v2_tuned_and_v5_with_v1_as_baseline():
    cmd_line = next(line for line in DOCKERFILE.read_text().splitlines() if line.startswith("CMD"))
    command = json.loads(cmd_line.removeprefix("CMD").strip())
    assert command[:3] == ["python", "-m", "mm"]
    agents = command[command.index("--agents") + 1].split(",")
    assert agents == ["skew", "kalman", "kalman_tuned", "final"]
    assert set(agents) <= set(AGENT_NAMES)
    # No --seeds or --scenarios: the CLI defaults are held-out seeds and every scenario.
    assert "--seeds" not in command and "--scenarios" not in command


def raw_config() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


def test_unknown_key_in_the_final_section_is_rejected_by_name():
    raw = raw_config()
    raw["agent"]["final"]["c"] = 1
    with pytest.raises(ValueError, match="unknown config key 'agent.final.c'"):
        build_config(raw)


@pytest.mark.parametrize("key", list(raw_config()["agent"]["final"]))
def test_missing_key_in_the_final_section_is_rejected_by_name(key):
    raw = raw_config()
    del raw["agent"]["final"][key]
    with pytest.raises(ValueError, match=f"missing config key 'agent.final.{key}'"):
        build_config(raw)


@pytest.mark.parametrize(
    ("key", "value"),
    [("base_half_spread", 4.0), ("quote_size", "5"), ("markout_horizon", 5.5)],
)
def test_final_integer_keys_must_be_integers(key, value):
    raw = raw_config()
    raw["agent"]["final"][key] = value
    with pytest.raises(ValueError, match=f"'agent.final.{key}' must be an integer"):
        build_config(raw)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("base_half_spread", 0, "half_spread must be >= 1"),
        ("quote_size", 0, "quote_size must be >= 1"),
        ("skew_per_lot", -0.1, "skew_per_lot must be >= 0"),
        ("uncertainty_weight", -1.0, "uncertainty_weight must be >= 0"),
        ("intensity_halflife", -1.0, "intensity_halflife must be >= 0"),
        ("max_scale", 0.5, "0 < min_scale <= 1 <= max_scale"),
        ("max_half_spread", 1, "max_half_spread must be >= base_half_spread"),
        ("widen_per_tick", -1.0, "widen_per_tick must be >= 0"),
        ("markout_horizon", 0, "markout_horizon must be >= 1"),
        ("ewma_halflife", 0.0, "ewma_halflife must be > 0"),
    ],
)
def test_final_config_rejects_out_of_range_values(key, value, message):
    raw = raw_config()
    raw["agent"]["final"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)
