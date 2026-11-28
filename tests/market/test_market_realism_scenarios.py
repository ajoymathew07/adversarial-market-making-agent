"""The realism stress scenarios (decision 08): same means as base, only the shape moves."""

from dataclasses import replace

import numpy as np
import pytest

from mm.agent import AGENT_NAMES
from mm.config import MarketConfig, load_config
from mm.eval.realism import dispersion_index, excess_kurtosis, size_stats
from mm.market import generate_intents, generate_noise_rate_scale, generate_value_path
from mm.market.arrivals import regime_path
from mm.market.takers import draw_noise_size
from mm.simulation import run_episode

BASE = load_config()
V0 = BASE.instrument.initial_price_ticks
REALISM_SCENARIOS = ("bursty_takers", "heavy_tail_sizes", "fat_tail_value", "realistic_mix")
BASE_MEAN_SIZE = (BASE.market.noise.size_min + BASE.market.noise.size_max) / 2


def market(scenario: str) -> MarketConfig:
    return load_config(scenario=scenario).market


def noise_flow(config: MarketConfig, n_steps: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-step noise-taker counts and all noise sizes, drawn the way run_episode draws them."""
    rng = np.random.default_rng(seed)
    path = generate_value_path(config, V0, n_steps, rng)
    scale = generate_noise_rate_scale(config.noise, n_steps, rng)
    counts, sizes = np.zeros(n_steps), []
    for t in range(n_steps):
        noise = [
            i for i in generate_intents(path, t, config, rng, float(scale[t])) if i.kind == "noise"
        ]
        counts[t] = len(noise)
        sizes += [i.size for i in noise]
    return counts, np.array(sizes, dtype=np.float64)


def value_steps(config: MarketConfig, n_steps: int, seed: int) -> np.ndarray:
    return np.diff(generate_value_path(config, V0, n_steps, np.random.default_rng(seed)))


# --- off by default: base draws exactly what it drew before these options existed ---


def test_base_value_path_is_the_original_gaussian_walk():
    n = 500
    expected_steps = BASE.market.true_value.sigma * np.random.default_rng(3).standard_normal(
        n + BASE.market.informed.lookahead
    )
    expected = V0 + np.concatenate(([0.0], np.cumsum(expected_steps)))
    np.testing.assert_array_equal(
        generate_value_path(BASE.market, V0, n, np.random.default_rng(3)), expected
    )


def test_poisson_arrivals_draw_no_random_numbers_and_scale_by_one():
    rng = np.random.default_rng(4)
    before = rng.bit_generator.state
    scale = generate_noise_rate_scale(BASE.market.noise, 100, rng)
    assert rng.bit_generator.state == before
    assert np.array_equal(scale, np.ones(100))


def test_uniform_size_draw_matches_the_original_integer_sequence():
    noise = BASE.market.noise
    expected = np.random.default_rng(5).integers(noise.size_min, noise.size_max + 1, 1_000)
    rng = np.random.default_rng(5)
    assert [draw_noise_size(noise, rng) for _ in range(1_000)] == expected.tolist()


def test_unit_scale_gives_the_same_intents_as_the_default():
    path = np.full(BASE.market.informed.lookahead + 2, float(V0))
    a = generate_intents(path, 0, BASE.market, np.random.default_rng(6))
    b = generate_intents(path, 0, BASE.market, np.random.default_rng(6), 1.0)
    assert a == b


# --- every scenario keeps base's means ---


@pytest.mark.parametrize("scenario", REALISM_SCENARIOS)
def test_scenario_keeps_base_mean_noise_rate_and_size(scenario):
    counts, sizes = zip(
        *(noise_flow(market(scenario), 20_000, seed) for seed in (1, 2, 3)), strict=True
    )
    assert np.concatenate(counts).mean() == pytest.approx(BASE.market.noise.rate, abs=0.06)
    assert np.concatenate(sizes).mean() == pytest.approx(BASE_MEAN_SIZE, abs=0.1)


@pytest.mark.parametrize("scenario", REALISM_SCENARIOS)
def test_scenario_keeps_base_value_step_sigma(scenario):
    steps = np.concatenate([value_steps(market(scenario), 100_000, seed) for seed in (1, 2)])
    assert steps.std() == pytest.approx(BASE.market.true_value.sigma, rel=0.02)
    assert abs(steps.mean()) < 0.02


def test_regime_rate_scale_has_mean_one():
    scale = generate_noise_rate_scale(
        market("bursty_takers").noise, 400_000, np.random.default_rng(7)
    )
    assert scale.mean() == pytest.approx(1.0, abs=0.03)
    assert set(np.unique(scale)) == {0.5, 3.0}


# --- the shape actually moved ---


def test_bursty_arrivals_are_overdispersed_and_more_so_over_longer_windows():
    counts = np.concatenate(
        [noise_flow(market("bursty_takers"), 20_000, seed)[0] for seed in (1, 2)]
    )
    one_step = dispersion_index(counts)
    ten_steps = dispersion_index(counts.reshape(-1, 10).sum(axis=1))
    assert one_step == pytest.approx(2.0, abs=0.25)  # 1 + Var(rate) / mean(rate) = 2
    assert ten_steps > one_step + 2
    base_counts = noise_flow(BASE.market, 20_000, 1)[0]
    assert dispersion_index(base_counts) == pytest.approx(1.0, abs=0.05)


def spell_lengths(busy: np.ndarray, state: bool) -> np.ndarray:
    edges = np.flatnonzero(np.diff(busy.astype(int))) + 1
    spells = np.split(busy, edges)[1:-1]  # drop the cut first and last spells
    return np.array([len(s) for s in spells if s[0] == state])


def test_regime_spells_have_the_configured_mean_durations():
    noise = market("bursty_takers").noise
    busy = regime_path(noise, 400_000, np.random.default_rng(8))
    assert spell_lengths(busy, False).mean() == pytest.approx(noise.calm_duration, rel=0.06)
    assert spell_lengths(busy, True).mean() == pytest.approx(noise.busy_duration, rel=0.06)
    assert busy.mean() == pytest.approx(0.2, abs=0.02)


def test_first_regime_follows_the_stationary_busy_share():
    noise = market("bursty_takers").noise
    first = [regime_path(noise, 1, np.random.default_rng(seed))[0] for seed in range(4_000)]
    assert np.mean(first) == pytest.approx(0.2, abs=0.02)


def test_lognormal_sizes_have_mean_three_and_a_heavy_tail():
    noise = market("heavy_tail_sizes").noise
    rng = np.random.default_rng(9)
    sizes = np.array([draw_noise_size(noise, rng) for _ in range(200_000)], dtype=np.float64)
    assert sizes.mean() == pytest.approx(3.0, abs=0.1)
    assert sizes.min() >= 1
    assert 6 <= size_stats(sizes).p99_over_median <= 14
    uniform = np.random.default_rng(9).integers(1, 6, 200_000).astype(np.float64)
    assert size_stats(uniform).p99_over_median < 3


def test_student_t_value_steps_have_fat_tails():
    fat = np.concatenate([value_steps(market("fat_tail_value"), 100_000, seed) for seed in (1, 2)])
    normal = value_steps(BASE.market, 200_000, 1)
    assert excess_kurtosis(fat) > 2  # 6 in theory; the sample estimate converges slowly
    assert abs(excess_kurtosis(normal)) < 0.1


def test_busy_rate_scale_does_not_change_the_informed_rate():
    config = market("bursty_takers")
    path = np.full(config.informed.lookahead + 1, float(V0) + 50)
    path[0] = V0  # informed takers see a move ahead, so they trade at step 0
    rng = np.random.default_rng(10)
    counts = [
        sum(i.kind == "informed" for i in generate_intents(path, 0, config, rng, 3.0))
        for _ in range(20_000)
    ]
    assert np.mean(counts) == pytest.approx(config.informed_rate, rel=0.05)


# --- full episodes pass the invariant monitor in every new scenario, for every agent ---


@pytest.mark.parametrize("agent", AGENT_NAMES)
@pytest.mark.parametrize("scenario", REALISM_SCENARIOS)
def test_full_episode_passes_the_invariant_monitor(scenario, agent):
    config = load_config(scenario=scenario)
    config = replace(config, n_steps=600, seed=11, agent=replace(config.agent, type=agent))
    assert len(run_episode(config).steps) == 600


def test_rate_scale_rejects_non_positive_step_count():
    with pytest.raises(ValueError):
        generate_noise_rate_scale(BASE.market.noise, 0, np.random.default_rng(0))
