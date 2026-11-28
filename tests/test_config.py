import tomllib
from dataclasses import replace
from typing import Any

import pytest

from mm.config import DEFAULT_CONFIG_PATH, build_config, load_config, scenario_names


def default_raw() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


def test_default_file_loads():
    config = load_config()
    assert config.instrument.tick_size == 0.01
    assert config.engine.fee_per_lot == 0
    assert (config.n_steps, config.seed) == (2000, 0)
    assert (config.agent.naive.half_spread, config.risk.position_limit) == (2, 50)


def test_initial_price_is_converted_to_ticks():
    assert load_config().instrument.initial_price_ticks == 10000


def test_load_config_reads_the_given_path(tmp_path):
    path = tmp_path / "custom.toml"
    path.write_text(DEFAULT_CONFIG_PATH.read_text().replace("fee_per_lot = 0", "fee_per_lot = 3"))
    assert load_config(path).engine.fee_per_lot == 3


def test_unknown_key_is_rejected_by_name():
    raw = default_raw()
    raw["engine"]["fee_per_lots"] = 1
    with pytest.raises(ValueError, match="'engine.fee_per_lots'"):
        build_config(raw)


def test_unknown_section_is_rejected_by_name():
    raw = default_raw()
    raw["engin"] = {}
    with pytest.raises(ValueError, match="'engin'"):
        build_config(raw)


def test_missing_key_is_rejected_by_name():
    raw = default_raw()
    del raw["instrument"]["tick_size"]
    with pytest.raises(ValueError, match="missing config key 'instrument.tick_size'"):
        build_config(raw)


@pytest.mark.parametrize("value", ["0", 0.5, True])
def test_non_integer_value_for_integer_key_is_rejected_by_name(value):
    raw = default_raw()
    raw["engine"]["fee_per_lot"] = value
    with pytest.raises(ValueError, match="'engine.fee_per_lot' must be an integer"):
        build_config(raw)


@pytest.mark.parametrize("value", ["0.01", False])
def test_non_number_for_number_key_is_rejected_by_name(value):
    raw = default_raw()
    raw["instrument"]["tick_size"] = value
    with pytest.raises(ValueError, match="'instrument.tick_size' must be a number"):
        build_config(raw)


def test_section_that_is_not_a_table_is_rejected_by_name():
    raw = default_raw()
    raw["engine"] = 0
    with pytest.raises(ValueError, match="'engine' must be a table"):
        build_config(raw)


@pytest.mark.parametrize("name", scenario_names())
def test_every_scenario_loads(name):
    assert load_config(scenario=name).market.informed.share >= 0


def test_scenario_names_follow_file_order():
    assert scenario_names() == (
        "no_informed",
        "base",
        "toxic",
        "uniform_takers",
        "heavy_tail_takers",
        "bursty_takers",
        "heavy_tail_sizes",
        "fat_tail_value",
        "realistic_mix",
        "vs_v1",
        "vs_tuned",
        "vs_final",
    )


def test_scenario_override_replaces_only_its_key():
    raw = default_raw()
    raw["scenarios"]["calm"] = {"market.true_value.sigma": 0.5}
    config = build_config(raw, "calm")
    assert config.market.true_value.sigma == 0.5
    assert config.market.informed == load_config().market.informed


def test_scenario_override_can_set_a_string_value():
    raw = default_raw()
    raw["scenarios"]["flat"] = {"market.noise.tolerance": "uniform"}
    config = build_config(raw, "flat")
    assert config.market.noise.tolerance == "uniform"
    assert config.market.informed == load_config().market.informed


@pytest.mark.parametrize(
    ("name", "shape"), [("uniform_takers", "uniform"), ("heavy_tail_takers", "lognormal")]
)
def test_tolerance_scenarios_change_only_the_tolerance_shape(name, shape):
    base = load_config()
    noise = replace(base.market.noise, tolerance=shape)
    assert load_config(scenario=name) == replace(base, market=replace(base.market, noise=noise))


def test_unknown_tolerance_shape_is_rejected_naming_the_valid_ones():
    raw = default_raw()
    raw["market"]["noise"]["tolerance"] = "gaussian"
    with pytest.raises(ValueError, match="'gaussian'; valid: exponential, uniform, lognormal"):
        build_config(raw)


def test_tolerance_shape_must_be_a_string():
    raw = default_raw()
    raw["market"]["noise"]["tolerance"] = 1.0
    with pytest.raises(ValueError, match="'market.noise.tolerance' must be a string"):
        build_config(raw)


def test_realism_scenarios_change_only_their_switches():
    base = load_config()
    regime = replace(base.market.noise, arrivals="regime")
    lognormal = replace(base.market.noise, size_shape="lognormal")
    student_t = replace(base.market.true_value, step_shape="student_t")
    mix_noise = replace(base.market.noise, arrivals="regime", size_shape="lognormal")
    expected = {
        "bursty_takers": replace(base.market, noise=regime),
        "heavy_tail_sizes": replace(base.market, noise=lognormal),
        "fat_tail_value": replace(base.market, true_value=student_t),
        "realistic_mix": replace(base.market, noise=mix_noise, true_value=student_t),
    }
    for name, market in expected.items():
        assert load_config(scenario=name) == replace(base, market=market)


def test_realism_options_are_off_in_base():
    market = load_config().market
    assert market.noise.arrivals == "poisson"
    assert market.noise.size_shape == "uniform"
    assert market.true_value.step_shape == "normal"


@pytest.mark.parametrize(
    ("table", "key", "valid"),
    [
        ("noise", "arrivals", "poisson, regime"),
        ("noise", "size_shape", "uniform, lognormal"),
        ("true_value", "step_shape", "normal, student_t"),
    ],
)
def test_unknown_realism_switch_is_rejected_naming_the_valid_ones(table, key, valid):
    raw = default_raw()
    raw["market"][table][key] = "hawkes"
    with pytest.raises(ValueError, match=f"'hawkes'; valid: {valid}"):
        build_config(raw)


@pytest.mark.parametrize(
    ("table", "key"),
    [
        ("noise", "arrivals"),
        ("noise", "calm_rate_scale"),
        ("noise", "calm_duration"),
        ("noise", "busy_rate_scale"),
        ("noise", "busy_duration"),
        ("noise", "size_shape"),
        ("noise", "size_log_mu"),
        ("noise", "size_log_sigma"),
        ("true_value", "step_shape"),
        ("true_value", "student_t_df"),
    ],
)
def test_missing_realism_key_is_rejected_by_name(table, key):
    raw = default_raw()
    del raw["market"][table][key]
    with pytest.raises(ValueError, match=f"missing config key 'market.{table}.{key}'"):
        build_config(raw)


def test_unknown_scenario_is_rejected_by_name():
    with pytest.raises(ValueError, match="unknown scenario 'toxik'"):
        load_config(scenario="toxik")


@pytest.mark.parametrize("dotted", ["market.informed.shar", "markets.informed.share", "x"])
def test_scenario_override_of_unknown_key_is_rejected_by_name(dotted):
    raw = default_raw()
    raw["scenarios"]["typo"] = {dotted: 0.4}
    with pytest.raises(ValueError, match=f"unknown key '{dotted}'"):
        build_config(raw, "typo")


def test_scenario_override_with_wrong_type_is_rejected_by_name():
    raw = default_raw()
    raw["scenarios"]["typo"] = {"market.informed.share": "0.4"}
    with pytest.raises(ValueError, match="'market.informed.share' must be a number"):
        build_config(raw, "typo")


def test_scenario_that_is_not_a_table_is_rejected_by_name():
    raw = default_raw()
    raw["scenarios"]["bad"] = 0.4
    with pytest.raises(ValueError, match="'scenarios.bad' must be a table"):
        build_config(raw, "bad")


def test_missing_scenarios_table_is_rejected():
    raw = default_raw()
    del raw["scenarios"]
    with pytest.raises(ValueError, match="'scenarios'"):
        build_config(raw)


@pytest.mark.parametrize("value", [[1], [1, 2, 3], [1, 2.5], 3])
def test_size_range_must_be_two_integers(value):
    raw = default_raw()
    raw["market"]["noise"]["size"] = value
    with pytest.raises(ValueError, match=r"'market.noise.size' must be \[min, max\]"):
        build_config(raw)


def test_size_range_is_read_into_min_and_max():
    noise = load_config().market.noise
    assert (noise.size_min, noise.size_max) == (1, 5)


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [("instrument", "tick_size", 0.0), ("instrument", "initial_price", -1.0)],
)
def test_range_validation_still_fires(section, key, value):
    raw = default_raw()
    raw[section][key] = value
    with pytest.raises(ValueError, match=f"{key} must be"):
        build_config(raw)


def test_evaluation_seed_ranges_are_inclusive():
    evaluation = load_config().evaluation
    assert evaluation.dev_seeds == tuple(range(30))
    assert evaluation.heldout_seeds == tuple(range(1000, 1030))
    assert evaluation.markout_horizons == (0, 1, 5, 10, 20)
    assert (evaluation.bootstrap_resamples, evaluation.bootstrap_seed) == (10000, 12345)


@pytest.mark.parametrize("value", [[0, 1.5], "0, 1", 3])
def test_markout_horizons_must_be_a_list_of_integers(value):
    raw = default_raw()
    raw["evaluation"]["markout_horizons"] = value
    with pytest.raises(ValueError, match="'evaluation.markout_horizons' must be a list"):
        build_config(raw)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("dev_seeds", [5, 4], "must not be empty"),
        ("heldout_seeds", [20, 40], "must not overlap"),
        ("markout_horizons", [], "markout_horizons"),
        ("markout_horizons", [-1, 0], "markout_horizons"),
        ("bootstrap_resamples", 0, "bootstrap_resamples"),
    ],
)
def test_evaluation_validation_fires(key, value, message):
    raw = default_raw()
    raw["evaluation"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_agent_section_reads_type_and_naive_settings():
    agent = load_config().agent
    assert agent.type == "final"
    assert (agent.naive.half_spread, agent.naive.quote_size) == (2, 5)


def test_unknown_key_in_agent_section_is_rejected_by_name():
    raw = default_raw()
    raw["agent"]["naive"]["half_spred"] = 3
    with pytest.raises(ValueError, match="'agent.naive.half_spred'"):
        build_config(raw)


def test_missing_agent_type_is_rejected_by_name():
    raw = default_raw()
    del raw["agent"]["type"]
    with pytest.raises(ValueError, match="missing config key 'agent.type'"):
        build_config(raw)


def test_agent_type_must_be_a_string():
    raw = default_raw()
    raw["agent"]["type"] = 1
    with pytest.raises(ValueError, match="'agent.type' must be a string"):
        build_config(raw)


def test_skew_section_loads_one_tuned_skew_per_lot():
    skew = load_config().agent.skew
    assert (skew.half_spread, skew.quote_size, skew.skew_per_lot) == (2, 5, 0.05)


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("half_spread", 0, "half_spread must be >= 1"),
        ("quote_size", 0, "quote_size must be >= 1"),
        ("skew_per_lot", -0.01, "skew_per_lot must be >= 0"),
    ],
)
def test_skew_validation_fires(key, value, message):
    raw = default_raw()
    raw["agent"]["skew"][key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_missing_skew_key_is_rejected_by_name():
    raw = default_raw()
    del raw["agent"]["skew"]["skew_per_lot"]
    with pytest.raises(ValueError, match="missing config key 'agent.skew.skew_per_lot'"):
        build_config(raw)


@pytest.mark.parametrize(
    ("table", "key", "value", "message"),
    [
        (("agent", "calibration"), "distances", [0, 5], "distances must satisfy 1 <= min <= max"),
        (("agent", "calibration"), "distances", [4, 2], "distances must satisfy 1 <= min <= max"),
        (("calibration",), "sigma_lag", 0, "sigma_lag must be >= 1"),
    ],
)
def test_calibration_validation_fires(table, key, value, message):
    raw = default_raw()
    section = raw
    for part in table:
        section = section[part]
    section[key] = value
    with pytest.raises(ValueError, match=message):
        build_config(raw)


def test_calibration_sections_load():
    config = load_config()
    agent = config.agent.calibration
    assert (agent.min_distance, agent.max_distance, agent.rng_stream) == (1, 5, 1)
    assert config.calibration.sigma_lag == 50
