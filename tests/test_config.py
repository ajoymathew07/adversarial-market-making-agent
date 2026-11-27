import tomllib
from typing import Any

import pytest

from mm.config import DEFAULT_CONFIG_PATH, build_config, load_config


def default_raw() -> dict[str, Any]:
    return tomllib.loads(DEFAULT_CONFIG_PATH.read_text())


def test_default_file_loads():
    config = load_config()
    assert config.instrument.tick_size == 0.01
    assert config.engine.fee_per_lot == 0


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


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [("instrument", "tick_size", 0.0), ("instrument", "initial_price", -1.0)],
)
def test_range_validation_still_fires(section, key, value):
    raw = default_raw()
    raw[section][key] = value
    with pytest.raises(ValueError, match=f"{key} must be"):
        build_config(raw)
