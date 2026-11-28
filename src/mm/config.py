"""Typed schema for `config/default.toml` and its strict loader.

Every parameter value lives in the TOML file. The dataclasses here have no defaults: they give
each value a type, check its range and derive the quantities the code uses.
"""

import copy
import math
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mm.engine.units import price_to_ticks

# src/mm/config.py -> repo root (or /app in Docker) -> config/default.toml
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default.toml"

# The noise-taker fill probability is calibrated at this distance from the true value.
FILL_PROB_REFERENCE_TICKS = 2.0

# Shapes of the noise-taker price tolerance; all have mean 1/k (see mm.market.takers).
TOLERANCE_SHAPES = ("exponential", "uniform", "lognormal")
# Stress options; the first of each is the base model (see docs/decisions/08-realistic-scenarios.md).
VALUE_STEP_SHAPES = ("normal", "student_t")
NOISE_ARRIVALS = ("poisson", "regime")
NOISE_SIZE_SHAPES = ("uniform", "lognormal")
# market.competitor value for the single-maker market (decision 02, option A).
NO_COMPETITOR = "none"


class ConfigError(ValueError):
    """The config file has an unknown, missing or wrongly typed key."""


@dataclass(frozen=True)
class InstrumentConfig:
    tick_size: float  # price of one tick, quoted per 100 face value
    initial_price: float  # in price units, not ticks

    def __post_init__(self) -> None:
        if self.tick_size <= 0:
            raise ValueError("tick_size must be > 0")
        if self.initial_price <= 0:
            raise ValueError("initial_price must be > 0")

    @property
    def initial_price_ticks(self) -> int:
        return price_to_ticks(self.initial_price, self.tick_size)


@dataclass(frozen=True)
class EngineConfig:
    fee_per_lot: int  # ticks per filled lot


def _check_choice(name: str, value: str, valid: tuple[str, ...]) -> None:
    if value not in valid:
        raise ValueError(f"unknown {name} {value!r}; valid: {', '.join(valid)}")


@dataclass(frozen=True)
class TrueValueConfig:
    sigma: float  # std of each step's move, in ticks
    step_shape: str  # one of VALUE_STEP_SHAPES
    student_t_df: float  # degrees of freedom for student_t steps; > 2 for a finite variance

    def __post_init__(self) -> None:
        if self.sigma < 0:
            raise ValueError("sigma must be >= 0")
        _check_choice("value step shape", self.step_shape, VALUE_STEP_SHAPES)
        if self.student_t_df <= 2:
            raise ValueError("student_t_df must be > 2")


@dataclass(frozen=True)
class NoiseConfig:
    rate: float  # mean arrivals per step
    size_min: int
    size_max: int
    fill_prob_at_2_ticks: float
    tolerance: str  # one of TOLERANCE_SHAPES
    arrivals: str  # one of NOISE_ARRIVALS
    calm_rate_scale: float  # regime arrivals: calm rate = calm_rate_scale * rate
    calm_duration: float  # regime arrivals: mean calm spell, steps (geometric)
    busy_rate_scale: float
    busy_duration: float
    size_shape: str  # one of NOISE_SIZE_SHAPES; uniform uses size_min..size_max
    size_log_mu: float  # lognormal sizes: max(1, round(LogNormal(mu, sigma)))
    size_log_sigma: float

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError("noise rate must be >= 0")
        _check_choice("noise tolerance", self.tolerance, TOLERANCE_SHAPES)
        _check_choice("noise arrivals", self.arrivals, NOISE_ARRIVALS)
        _check_choice("noise size shape", self.size_shape, NOISE_SIZE_SHAPES)
        if not 1 <= self.size_min <= self.size_max:
            raise ValueError("noise sizes must satisfy 1 <= min <= max")
        if not 0 < self.fill_prob_at_2_ticks < 1:
            raise ValueError("fill_prob_at_2_ticks must be in (0, 1)")
        if min(self.calm_rate_scale, self.busy_rate_scale) < 0:
            raise ValueError("regime rate scales must be >= 0")
        if min(self.calm_duration, self.busy_duration) < 1:
            raise ValueError("regime durations must be >= 1 step")
        if self.size_log_sigma < 0:
            raise ValueError("size_log_sigma must be >= 0")

    @property
    def tolerance_rate(self) -> float:
        """k in P(fill at distance d) = exp(-k * d), from the calibration point."""
        return -math.log(self.fill_prob_at_2_ticks) / FILL_PROB_REFERENCE_TICKS


@dataclass(frozen=True)
class InformedConfig:
    share: float  # expected fraction of all takers
    lookahead: int  # steps ahead they see the true value
    edge_threshold: float  # minimum edge they need, in ticks
    size_min: int
    size_max: int

    def __post_init__(self) -> None:
        if not 0 <= self.share < 1:
            raise ValueError("informed share must be in [0, 1)")
        if self.lookahead < 1:
            raise ValueError("informed lookahead must be >= 1")
        if self.edge_threshold < 0:
            raise ValueError("informed edge_threshold must be >= 0")
        if not 1 <= self.size_min <= self.size_max:
            raise ValueError("informed sizes must satisfy 1 <= min <= max")


@dataclass(frozen=True)
class MarketConfig:
    true_value: TrueValueConfig
    noise: NoiseConfig
    informed: InformedConfig
    # A second market maker built by the agent registry, or NO_COMPETITOR (decision 12).
    # The name is checked against the registry when the episode builds it.
    competitor: str
    posting_order_stream: int  # own RNG: PCG64([episode seed, stream]) picks who posts first

    @property
    def informed_rate(self) -> float:
        """Mean informed takers per step, so that informed / all takers = informed.share."""
        return self.noise.rate * self.informed.share / (1 - self.informed.share)


@dataclass(frozen=True)
class NaiveConfig:
    half_spread: int  # ticks from the centre to each quote
    quote_size: int  # lots on each side


@dataclass(frozen=True)
class SkewConfig:
    half_spread: int  # ticks from the reservation price to each quote
    quote_size: int  # lots on each side
    skew_per_lot: float  # ticks the reservation price moves per lot of position (γσ²τ in A-S)

    def __post_init__(self) -> None:
        if self.half_spread < 1:
            raise ValueError("skew half_spread must be >= 1")
        if self.quote_size < 1:
            raise ValueError("skew quote_size must be >= 1")
        if self.skew_per_lot < 0:
            raise ValueError("skew skew_per_lot must be >= 0")


@dataclass(frozen=True)
class KalmanConfig:
    """The v2 agent's own estimates of the market, from `make calibrate` (never from [market])."""

    sigma: float  # true-value volatility, ticks per step
    noise_rate: float  # noise takers per step (lambda)
    mean_size: float  # average taker size, lots
    mean_size_sq: float  # average of size squared, lots^2
    k: float  # fill-rate decay: fills at distance d are proportional to exp(-k * d)
    gain_scale: float  # 1 = the Kalman gain; other values only for the sensitivity check

    def __post_init__(self) -> None:
        if self.sigma < 0:
            raise ValueError("kalman sigma must be >= 0")
        if self.noise_rate <= 0:
            raise ValueError("kalman noise_rate must be > 0")
        if self.mean_size <= 0:
            raise ValueError("kalman mean_size must be > 0")
        if self.mean_size_sq < self.mean_size**2:
            raise ValueError("kalman mean_size_sq must be >= mean_size^2")
        if self.k <= 0:
            raise ValueError("kalman k must be > 0")
        if self.gain_scale < 0:
            raise ValueError("kalman gain_scale must be >= 0")


@dataclass(frozen=True)
class KalmanTunedConfig:
    """The tuned-spread control: v2 with its own half-spread (see docs/decisions/09)."""

    half_spread: int  # ticks; replaces [agent.skew] half_spread for this agent only

    def __post_init__(self) -> None:
        if self.half_spread < 1:
            raise ValueError("kalman_tuned half_spread must be >= 1")


@dataclass(frozen=True)
class ToxicityConfig:
    """The v3 agent's spread widening on its own fills' markouts (see mm.agent.toxicity)."""

    base_half_spread: int  # ticks; the half-spread when the toxicity score is 0
    markout_horizon: int  # τ: observations from a fill's reference fair value to its mark
    widen_per_tick: float  # c: half-spread ticks added per tick of toxicity score
    ewma_halflife: float  # lots of matured fills after which an old markout's weight halves
    max_half_spread: int  # ticks; the widened half-spread is clipped to this

    def __post_init__(self) -> None:
        if self.base_half_spread < 1:
            raise ValueError("toxicity base_half_spread must be >= 1")
        if self.max_half_spread < self.base_half_spread:
            raise ValueError("toxicity max_half_spread must be >= base_half_spread")
        if self.markout_horizon < 1:
            raise ValueError("toxicity markout_horizon must be >= 1")
        if self.widen_per_tick < 0:
            raise ValueError("toxicity widen_per_tick must be >= 0")
        if self.ewma_halflife <= 0:
            raise ValueError("toxicity ewma_halflife must be > 0")


@dataclass(frozen=True)
class AdaptiveConfig:
    """The v4 agent's intensity and uncertainty adaptation (see mm.agent.adaptive)."""

    base_half_spread: int  # ticks; the half-spread when the filter is certain (P = 0)
    uncertainty_weight: float  # a: half-spread ticks per tick of posterior std sqrt(P)
    intensity_halflife: float  # steps; 0 turns the online intensity off (rho = 1)
    min_scale: float  # rho is clipped to [min_scale, max_scale]
    max_scale: float
    max_half_spread: int  # ticks; the widened half-spread is clipped to this

    def __post_init__(self) -> None:
        if self.base_half_spread < 1:
            raise ValueError("adaptive base_half_spread must be >= 1")
        if self.max_half_spread < self.base_half_spread:
            raise ValueError("adaptive max_half_spread must be >= base_half_spread")
        if self.uncertainty_weight < 0:
            raise ValueError("adaptive uncertainty_weight must be >= 0")
        if self.intensity_halflife < 0:
            raise ValueError("adaptive intensity_halflife must be >= 0 (0 = off)")
        if not 0 < self.min_scale <= 1 <= self.max_scale:
            raise ValueError("adaptive scales must satisfy 0 < min_scale <= 1 <= max_scale")


@dataclass(frozen=True)
class FinalConfig:
    """Every knob of the v5 agent: v4's adaptive agent plus v3's toxicity widening.

    Range checks are those of the sections it is split into (`skew`, `adaptive`, `toxicity`).
    """

    base_half_spread: int  # ticks
    skew_per_lot: float  # ticks of reservation shift per lot of position
    quote_size: int  # lots on each side
    uncertainty_weight: float  # a: half-spread ticks per tick of sqrt(P)
    intensity_halflife: float  # steps; 0 = off
    min_scale: float  # rho clip
    max_scale: float
    max_half_spread: int  # ticks
    widen_per_tick: float  # c: half-spread ticks per tick of toxicity score T
    markout_horizon: int  # tau, observations
    ewma_halflife: float  # lots of matured fills

    def __post_init__(self) -> None:
        self.skew()
        self.adaptive()
        self.toxicity()

    def skew(self) -> SkewConfig:
        return SkewConfig(
            half_spread=self.base_half_spread,
            quote_size=self.quote_size,
            skew_per_lot=self.skew_per_lot,
        )

    def adaptive(self) -> AdaptiveConfig:
        return AdaptiveConfig(
            base_half_spread=self.base_half_spread,
            uncertainty_weight=self.uncertainty_weight,
            intensity_halflife=self.intensity_halflife,
            min_scale=self.min_scale,
            max_scale=self.max_scale,
            max_half_spread=self.max_half_spread,
        )

    def toxicity(self) -> ToxicityConfig:
        return ToxicityConfig(
            base_half_spread=self.base_half_spread,
            markout_horizon=self.markout_horizon,
            widen_per_tick=self.widen_per_tick,
            ewma_halflife=self.ewma_halflife,
            max_half_spread=self.max_half_spread,
        )


@dataclass(frozen=True)
class CalibrationAgentConfig:
    """The calibration agent's design choices (see mm.agent.calibration)."""

    min_distance: int  # ticks from the centre, drawn uniformly per side per step
    max_distance: int
    rng_stream: int  # its own RNG is PCG64([episode seed, rng_stream]), never the market's

    def __post_init__(self) -> None:
        if not 1 <= self.min_distance <= self.max_distance:
            raise ValueError("calibration distances must satisfy 1 <= min <= max")


@dataclass(frozen=True)
class AgentConfig:
    type: str  # registry name of the agent that runs by default (see mm.agent.registry)
    naive: NaiveConfig
    skew: SkewConfig
    kalman: KalmanConfig
    kalman_tuned: KalmanTunedConfig
    toxicity: ToxicityConfig
    adaptive: AdaptiveConfig
    final: FinalConfig
    calibration: CalibrationAgentConfig


@dataclass(frozen=True)
class CalibrationConfig:
    """How the agent's parameters are estimated from its own observations (mm.calibration)."""

    sigma_lag: int  # steps between the trade prices used for sigma

    def __post_init__(self) -> None:
        if self.sigma_lag < 1:
            raise ValueError("calibration sigma_lag must be >= 1")


@dataclass(frozen=True)
class RiskConfig:
    position_limit: int  # max |position| in lots
    max_order_size: int  # lots per order
    max_quote_distance: int  # max ticks between a quote and the last trade price


@dataclass(frozen=True)
class EvalConfig:
    dev_seeds: tuple[int, ...]  # for tuning
    heldout_seeds: tuple[int, ...]  # only for reported numbers
    markout_horizons: tuple[int, ...]  # steps after a fill
    bootstrap_resamples: int
    bootstrap_seed: int

    def __post_init__(self) -> None:
        if not self.dev_seeds or not self.heldout_seeds:
            raise ValueError("seed ranges must not be empty")
        if set(self.dev_seeds) & set(self.heldout_seeds):
            raise ValueError("dev_seeds and heldout_seeds must not overlap")
        if not self.markout_horizons or min(self.markout_horizons) < 0:
            raise ValueError("markout_horizons must be non-empty and >= 0")
        if self.bootstrap_resamples < 1:
            raise ValueError("bootstrap_resamples must be >= 1")


@dataclass(frozen=True)
class SimConfig:
    """Everything one episode (and the evaluation around it) needs, built from the config file."""

    instrument: InstrumentConfig
    engine: EngineConfig
    market: MarketConfig
    agent: AgentConfig
    risk: RiskConfig
    n_steps: int
    seed: int
    evaluation: EvalConfig
    calibration: CalibrationConfig


def load_config(path: Path | None = None, scenario: str = "base") -> SimConfig:
    """Read the config file (default: `config/default.toml`) with one scenario applied."""
    return build_config(_read(path), scenario)


def scenario_names(path: Path | None = None) -> tuple[str, ...]:
    """The scenarios defined in the config file, in file order."""
    return tuple(_scenarios(_read(path)))


def build_config(raw: dict[str, Any], scenario: str = "base") -> SimConfig:
    """Build the typed config from parsed TOML. Raises ValueError naming any bad key."""
    root = _Table(_apply_scenario(raw, scenario), "")
    simulation = root.get_table("simulation")
    config = SimConfig(
        instrument=_instrument(root.get_table("instrument")),
        engine=_engine(root.get_table("engine")),
        market=_market(root.get_table("market")),
        agent=_agent(root.get_table("agent")),
        risk=_risk(root.get_table("risk")),
        n_steps=simulation.get_int("n_steps"),
        seed=simulation.get_int("seed"),
        evaluation=_evaluation(root.get_table("evaluation")),
        calibration=CalibrationConfig(sigma_lag=root.get_table("calibration").get_int("sigma_lag")),
    )
    root.reject_unread()
    return config


def _read(path: Path | None) -> dict[str, Any]:
    with (path or DEFAULT_CONFIG_PATH).open("rb") as handle:
        return tomllib.load(handle)


def _apply_scenario(raw: dict[str, Any], scenario: str) -> dict[str, Any]:
    """Return a copy of `raw` without [scenarios], with the scenario's overrides applied.

    Overrides use dotted keys, e.g. {"market.informed.share" = 0.40}.
    """
    raw = copy.deepcopy(raw)
    scenarios = _scenarios(raw)
    del raw["scenarios"]
    if scenario not in scenarios:
        raise ConfigError(f"unknown scenario {scenario!r}; known: {', '.join(scenarios)}")
    overrides = scenarios[scenario]
    if not isinstance(overrides, dict):
        raise ConfigError(f"'scenarios.{scenario}' must be a table")
    for dotted, value in overrides.items():
        *parents, last = dotted.split(".")
        table: Any = raw
        for part in parents:
            table = table.get(part) if isinstance(table, dict) else None
        if not isinstance(table, dict) or last not in table:
            raise ConfigError(f"scenario {scenario!r} overrides unknown key {dotted!r}")
        table[last] = value
    return raw


def _scenarios(raw: dict[str, Any]) -> dict[str, Any]:
    scenarios = raw.get("scenarios")
    if not isinstance(scenarios, dict):
        raise ConfigError("missing config table 'scenarios'")
    return scenarios


def _instrument(table: "_Table") -> InstrumentConfig:
    return InstrumentConfig(
        tick_size=table.get_float("tick_size"),
        initial_price=table.get_float("initial_price"),
    )


def _engine(table: "_Table") -> EngineConfig:
    return EngineConfig(fee_per_lot=table.get_int("fee_per_lot"))


def _market(table: "_Table") -> MarketConfig:
    noise = table.get_table("noise")
    noise_min, noise_max = noise.get_int_pair("size")
    informed = table.get_table("informed")
    informed_min, informed_max = informed.get_int_pair("size")
    true_value = table.get_table("true_value")
    return MarketConfig(
        true_value=TrueValueConfig(
            sigma=true_value.get_float("sigma"),
            step_shape=true_value.get_str("step_shape"),
            student_t_df=true_value.get_float("student_t_df"),
        ),
        noise=NoiseConfig(
            rate=noise.get_float("rate"),
            size_min=noise_min,
            size_max=noise_max,
            fill_prob_at_2_ticks=noise.get_float("fill_prob_at_2_ticks"),
            tolerance=noise.get_str("tolerance"),
            arrivals=noise.get_str("arrivals"),
            calm_rate_scale=noise.get_float("calm_rate_scale"),
            calm_duration=noise.get_float("calm_duration"),
            busy_rate_scale=noise.get_float("busy_rate_scale"),
            busy_duration=noise.get_float("busy_duration"),
            size_shape=noise.get_str("size_shape"),
            size_log_mu=noise.get_float("size_log_mu"),
            size_log_sigma=noise.get_float("size_log_sigma"),
        ),
        informed=InformedConfig(
            share=informed.get_float("share"),
            lookahead=informed.get_int("lookahead"),
            edge_threshold=informed.get_float("edge_threshold"),
            size_min=informed_min,
            size_max=informed_max,
        ),
        competitor=table.get_str("competitor"),
        posting_order_stream=table.get_int("posting_order_stream"),
    )


def _agent(table: "_Table") -> AgentConfig:
    naive = table.get_table("naive")
    skew = table.get_table("skew")
    kalman = table.get_table("kalman")
    kalman_tuned = table.get_table("kalman_tuned")
    toxicity = table.get_table("toxicity")
    adaptive = table.get_table("adaptive")
    final = table.get_table("final")
    calibration = table.get_table("calibration")
    min_distance, max_distance = calibration.get_int_pair("distances")
    return AgentConfig(
        type=table.get_str("type"),
        naive=NaiveConfig(
            half_spread=naive.get_int("half_spread"),
            quote_size=naive.get_int("quote_size"),
        ),
        skew=SkewConfig(
            half_spread=skew.get_int("half_spread"),
            quote_size=skew.get_int("quote_size"),
            skew_per_lot=skew.get_float("skew_per_lot"),
        ),
        kalman=KalmanConfig(
            sigma=kalman.get_float("sigma"),
            noise_rate=kalman.get_float("noise_rate"),
            mean_size=kalman.get_float("mean_size"),
            mean_size_sq=kalman.get_float("mean_size_sq"),
            k=kalman.get_float("k"),
            gain_scale=kalman.get_float("gain_scale"),
        ),
        kalman_tuned=KalmanTunedConfig(half_spread=kalman_tuned.get_int("half_spread")),
        toxicity=ToxicityConfig(
            base_half_spread=toxicity.get_int("base_half_spread"),
            markout_horizon=toxicity.get_int("markout_horizon"),
            widen_per_tick=toxicity.get_float("widen_per_tick"),
            ewma_halflife=toxicity.get_float("ewma_halflife"),
            max_half_spread=toxicity.get_int("max_half_spread"),
        ),
        adaptive=AdaptiveConfig(
            base_half_spread=adaptive.get_int("base_half_spread"),
            uncertainty_weight=adaptive.get_float("uncertainty_weight"),
            intensity_halflife=adaptive.get_float("intensity_halflife"),
            min_scale=adaptive.get_float("min_scale"),
            max_scale=adaptive.get_float("max_scale"),
            max_half_spread=adaptive.get_int("max_half_spread"),
        ),
        final=FinalConfig(
            base_half_spread=final.get_int("base_half_spread"),
            skew_per_lot=final.get_float("skew_per_lot"),
            quote_size=final.get_int("quote_size"),
            uncertainty_weight=final.get_float("uncertainty_weight"),
            intensity_halflife=final.get_float("intensity_halflife"),
            min_scale=final.get_float("min_scale"),
            max_scale=final.get_float("max_scale"),
            max_half_spread=final.get_int("max_half_spread"),
            widen_per_tick=final.get_float("widen_per_tick"),
            markout_horizon=final.get_int("markout_horizon"),
            ewma_halflife=final.get_float("ewma_halflife"),
        ),
        calibration=CalibrationAgentConfig(
            min_distance=min_distance,
            max_distance=max_distance,
            rng_stream=calibration.get_int("rng_stream"),
        ),
    )


def _risk(table: "_Table") -> RiskConfig:
    return RiskConfig(
        position_limit=table.get_int("position_limit"),
        max_order_size=table.get_int("max_order_size"),
        max_quote_distance=table.get_int("max_quote_distance"),
    )


def _evaluation(table: "_Table") -> EvalConfig:
    dev_first, dev_last = table.get_int_pair("dev_seeds")
    heldout_first, heldout_last = table.get_int_pair("heldout_seeds")
    return EvalConfig(
        dev_seeds=tuple(range(dev_first, dev_last + 1)),
        heldout_seeds=tuple(range(heldout_first, heldout_last + 1)),
        markout_horizons=table.get_int_list("markout_horizons"),
        bootstrap_resamples=table.get_int("bootstrap_resamples"),
        bootstrap_seed=table.get_int("bootstrap_seed"),
    )


class _Table:
    """One TOML table, read strictly: each key must exist with the expected type.

    Keys that are never read are reported by `reject_unread`, so a typo cannot be ignored.
    """

    def __init__(self, values: dict[str, Any], name: str) -> None:
        self._values = values
        self._name = name
        self._unread = set(values)
        self._children: list[_Table] = []

    def get_table(self, key: str) -> "_Table":
        value = self._get(key)
        if not isinstance(value, dict):
            raise ConfigError(f"{self._full(key)!r} must be a table")
        child = _Table(value, self._full(key))
        self._children.append(child)
        return child

    def get_int(self, key: str) -> int:
        value = self._get(key)
        if not _is_int(value):
            raise ConfigError(f"{self._full(key)!r} must be an integer, got {value!r}")
        return int(value)

    def get_str(self, key: str) -> str:
        value = self._get(key)
        if not isinstance(value, str):
            raise ConfigError(f"{self._full(key)!r} must be a string, got {value!r}")
        return value

    def get_float(self, key: str) -> float:
        value = self._get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ConfigError(f"{self._full(key)!r} must be a number, got {value!r}")
        return float(value)

    def get_int_pair(self, key: str) -> tuple[int, int]:
        value = self._get(key)
        if not (isinstance(value, list) and len(value) == 2 and all(map(_is_int, value))):
            raise ConfigError(f"{self._full(key)!r} must be [min, max] integers, got {value!r}")
        return int(value[0]), int(value[1])

    def get_int_list(self, key: str) -> tuple[int, ...]:
        value = self._get(key)
        if not (isinstance(value, list) and all(map(_is_int, value))):
            raise ConfigError(f"{self._full(key)!r} must be a list of integers, got {value!r}")
        return tuple(int(v) for v in value)

    def reject_unread(self) -> None:
        if self._unread:
            raise ConfigError(f"unknown config key {self._full(min(self._unread))!r}")
        for child in self._children:
            child.reject_unread()

    def _get(self, key: str) -> Any:
        if key not in self._values:
            raise ConfigError(f"missing config key {self._full(key)!r}")
        self._unread.discard(key)
        return self._values[key]

    def _full(self, key: str) -> str:
        return f"{self._name}.{key}" if self._name else key


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
