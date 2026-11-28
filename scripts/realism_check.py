"""Realism check: simulator taker flow (base scenario, dev seeds) next to one day of Binance
BTCUSDT aggTrades. Writes docs/results/realism/btcusdt-2026-11-25.md and fill_decay.png.

Run with `make realism-data && make realism`. Not a backtest and not a calibration: the agent is
not run, and nothing here feeds back into config/default.toml. The simulator column uses the raw
taker intents (no agent, no book), so the flow is not censored by any quote size.
"""

import argparse
import csv
import io
import time
import zipfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from mm.config import load_config
from mm.eval import realism as rz
from mm.market import generate_intents, generate_value_path

SOURCE_URL = (
    "https://data.binance.vision/data/spot/daily/aggTrades/BTCUSDT/BTCUSDT-aggTrades-2026-11-25.zip"
)
SOURCE_SHA256 = "59fa83f7c425d7f54da49b3858beac42017c5ea584698ebdeef860285322bb38"
REPORT_NAME = "btcusdt-2026-11-25.md"
INTERPRETATION_HEADING = "## Interpretation"
PLOT_NAME = "fill_decay.png"

STEP_SECONDS = 1.0
ROBUSTNESS_STEPS = (0.1, 1.0, 10.0)  # seconds, BTCUSDT only
MICROS = 1e6
DELTA_GRID = np.arange(0.25, 4.0 + 1e-9, 0.25)  # in units of sigma_step
REPORTED_DELTAS = (0.5, 1.0, 2.0, 4.0)
MARKOUT_HORIZONS = (1, 10, 60)  # steps
VR_HORIZONS = (10, 60)  # steps
JITTER_STREAM = 7  # own RNG stream for within-step arrival times of simulated takers
BUCKET_LABELS = ("0-50%", "50-90%", "90-99%", "99-100%")


@dataclass(frozen=True)
class Stats:
    sigma: float
    probs: rz.FloatArray
    exp_fit: rz.Fit
    pow_fit: rz.Fit
    orders_per_step: float
    dispersion: float
    cv: float
    sizes: rz.SizeStats
    markouts: rz.FloatArray  # (buckets, horizons)
    bucket_share: rz.FloatArray
    vr: tuple[float, ...]
    change_kurtosis: float


# ---------------------------------------------------------------- BTCUSDT


def load_aggtrades(path: Path) -> rz.TakerOrders:
    """Parse the zip's single CSV (no header) into raw trades; timestamps are microseconds."""
    with zipfile.ZipFile(path) as archive:
        (name,) = archive.namelist()
        with archive.open(name) as raw:
            rows = list(csv.reader(io.TextIOWrapper(raw, encoding="ascii")))
    prices = np.array([float(r[1]) for r in rows])
    sizes = np.array([float(r[2]) for r in rows])
    times = np.array([int(r[5]) for r in rows], dtype=np.float64) / MICROS
    # is_buyer_maker True means the taker sold.
    signs = np.array([-1 if r[6] == "True" else 1 for r in rows], dtype=np.int64)
    return rz.TakerOrders(times, prices, sizes, signs)


@dataclass(frozen=True)
class Binned:
    last: rz.FloatArray  # last price at the end of each step
    step: rz.IntArray  # step of each order
    n_steps: int


def bin_orders(orders: rz.TakerOrders, step: float) -> Binned:
    start = np.floor(orders.times[0] / step) * step
    n_steps = int(np.floor((orders.times[-1] - start) / step)) + 1
    last = rz.bin_last_price(orders.times, orders.prices, start, step, n_steps)
    return Binned(last, rz.bin_index(orders.times, start, step), n_steps)


def btc_stats(orders: rz.TakerOrders) -> Stats:
    b = bin_orders(orders, STEP_SECONDS)
    sigma = float(np.std(np.diff(b.last)))
    # Reference at the start of step j is the last price of step j - 1, so step 0 is dropped.
    later = b.step >= 1
    probs = rz.touch_probabilities(
        b.last[:-1],
        b.step[later] - 1,
        orders.prices[later],
        orders.signs[later],
        DELTA_GRID * sigma,
    )
    counts = np.bincount(b.step, minlength=b.n_steps).astype(np.float64)
    marks = rz.markout_values(
        orders.times,
        orders.prices,
        orders.signs,
        orders.times,
        orders.prices,
        np.array(MARKOUT_HORIZONS, dtype=np.float64) * STEP_SECONDS,
        sigma,
    )
    return _stats(sigma, probs, counts, orders.times, orders.sizes, marks, b.last)


def btc_robustness(orders: rz.TakerOrders) -> list[tuple[float, float, float]]:
    """(dispersion, VR(10), VR(60)) at each step width."""
    out = []
    for step in ROBUSTNESS_STEPS:
        b = bin_orders(orders, step)
        counts = np.bincount(b.step, minlength=b.n_steps).astype(np.float64)
        vr10, vr60 = (rz.variance_ratio(b.last, h) for h in VR_HORIZONS)
        out.append((rz.dispersion_index(counts), vr10, vr60))
    return out


# ---------------------------------------------------------------- simulator


def sim_stats(seeds: tuple[int, ...]) -> Stats:
    """Base scenario, one value path and its intents per seed; samples pooled across seeds.

    Seeds are laid end to end in time (seed s occupies steps [s*n, (s+1)*n)): arrivals and
    random-walk increments are i.i.d. across steps, so pooling this way is exact.
    """
    config = load_config(scenario="base")
    market, n = config.market, config.n_steps
    refs, steps, limits, signs, sizes, counts, times, marks, increments = ([] for _ in range(9))
    for k, seed in enumerate(seeds):
        rng = np.random.Generator(np.random.PCG64(seed))
        jitter = np.random.Generator(np.random.PCG64([seed, JITTER_STREAM]))
        path = generate_value_path(market, config.instrument.initial_price_ticks, n, rng)
        intents = [(t, i) for t in range(n) for i in generate_intents(path, t, market, rng)]
        step = np.array([t for t, _ in intents], dtype=np.int64)
        sign = np.array([i.side.sign for _, i in intents], dtype=np.int64)
        refs.append(path[:n])
        steps.append(step + k * n)
        limits.append(np.array([i.limit_price for _, i in intents], dtype=np.float64))
        signs.append(sign)
        sizes.append(np.array([i.size for _, i in intents], dtype=np.float64))
        counts.append(np.bincount(step, minlength=n).astype(np.float64))
        # Poisson counts per step with uniform times inside the step is a Poisson process.
        times.append(np.sort(step + jitter.random(len(step))) + k * n)
        marks.append((path, step, sign))
        increments.append(np.diff(path))
    sigma = float(np.std(np.concatenate(increments)))
    probs = rz.touch_probabilities(
        np.concatenate(refs),
        np.concatenate(steps),
        np.concatenate(limits),
        np.concatenate(signs),
        DELTA_GRID * sigma,
    )
    horizons = np.array(MARKOUT_HORIZONS, dtype=np.float64)
    # Markouts against the true value at the arrival step (there is no trade price without a book).
    mark_values = np.concatenate(
        [
            rz.markout_values(
                s.astype(np.float64),
                path[s],
                g,
                np.arange(len(path), dtype=np.float64),
                path,
                horizons,
                sigma,
            )
            for path, s, g in marks
        ]
    )
    value = np.concatenate(([0.0], np.cumsum(np.concatenate(increments))))
    return _stats(
        sigma,
        probs,
        np.concatenate(counts),
        np.concatenate(times),
        np.concatenate(sizes),
        mark_values,
        value,
    )


# ---------------------------------------------------------------- shared


def _stats(
    sigma: float,
    probs: rz.FloatArray,
    counts: rz.FloatArray,
    times: rz.FloatArray,
    sizes: rz.FloatArray,
    marks: rz.FloatArray,
    prices: rz.FloatArray,
) -> Stats:
    buckets = rz.size_buckets(sizes)
    share = np.bincount(buckets, minlength=len(BUCKET_LABELS)) / len(buckets)
    return Stats(
        sigma=sigma,
        probs=probs,
        exp_fit=rz.fit_exponential(DELTA_GRID, probs),
        pow_fit=rz.fit_power_law(DELTA_GRID, probs),
        orders_per_step=float(counts.mean()),
        dispersion=rz.dispersion_index(counts),
        cv=rz.interarrival_cv(times),
        sizes=rz.size_stats(sizes),
        markouts=rz.bucket_means(marks, buckets),
        bucket_share=share.astype(np.float64),
        vr=tuple(rz.variance_ratio(prices, h) for h in VR_HORIZONS),
        change_kurtosis=rz.excess_kurtosis(np.diff(prices)),
    )


def _f(x: float, digits: int = 3) -> str:
    return "n/a" if np.isnan(x) else f"{x:.{digits}g}"


def _table(rows: Sequence[tuple[str, ...]], header: tuple[str, ...]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(lines)


def report(sim: Stats, btc: Stats, robust: list[tuple[float, float, float]], meta: str) -> str:
    head = ("Statistic", "Simulator (base)", "BTCUSDT")

    def row(label: str, a: float, b: float, digits: int = 3) -> tuple[str, str, str]:
        return (label, _f(a, digits), _f(b, digits))

    fill = [
        row(f"P(touch) at δ = {d:g} σ", sim.probs[_grid(d)], btc.probs[_grid(d)])
        for d in REPORTED_DELTAS
    ]
    fill += [
        row("Exponential fit: k·σ", sim.exp_fit.slope, btc.exp_fit.slope),
        row("Exponential fit: R²", sim.exp_fit.r2, btc.exp_fit.r2),
        row("Power-law fit: exponent", sim.pow_fit.slope, btc.pow_fit.slope),
        row("Power-law fit: R²", sim.pow_fit.r2, btc.pow_fit.r2),
    ]
    arrivals = [
        row("Taker orders per step", sim.orders_per_step, btc.orders_per_step),
        row("Dispersion index (var/mean of counts)", sim.dispersion, btc.dispersion),
        row("Inter-arrival CV", sim.cv, btc.cv),
    ]
    s, b = sim.sizes, btc.sizes
    size = [
        row("p90 / median", s.p90_over_median, b.p90_over_median),
        row("p99 / median", s.p99_over_median, b.p99_over_median),
        row("max / median", s.max_over_median, b.max_over_median),
        row("Excess kurtosis", s.excess_kurtosis, b.excess_kurtosis),
    ]
    marks = [
        row(f"Share of orders, size {lab}", sim.bucket_share[i], btc.bucket_share[i])
        for i, lab in enumerate(BUCKET_LABELS)
    ]
    marks += [
        row(f"h = {h}, size {lab}", sim.markouts[i, j], btc.markouts[i, j])
        for j, h in enumerate(MARKOUT_HORIZONS)
        for i, lab in enumerate(BUCKET_LABELS)
    ]
    price = [row("σ_step (sim: ticks, BTC: USDT)", sim.sigma, btc.sigma)]
    price += [
        row(f"Variance ratio, h = {h}", sim.vr[i], btc.vr[i]) for i, h in enumerate(VR_HORIZONS)
    ]
    price.append(row("Excess kurtosis of 1-step changes", sim.change_kurtosis, btc.change_kurtosis))
    robust_rows = [
        (name, *(_f(r[i]) for r in robust))
        for i, name in enumerate(
            ("Dispersion index", "Variance ratio, h = 10", "Variance ratio, h = 60")
        )
    ]
    robust_head = ("BTCUSDT", *(f"step {s:g} s" for s in ROBUSTNESS_STEPS))
    return (
        "\n\n".join(
            [
                "# Realism check: simulator vs BTCUSDT (2026-11-25)",
                meta,
                "## Fill decay (P that a quote δ away is traded through within one step)",
                _table(fill, head),
                f"![fill decay]({PLOT_NAME})",
                "## Taker arrivals",
                _table(arrivals, head),
                "## Taker order sizes",
                _table(size, head),
                "## Taker markouts (σ_step; positive = price moved the taker's way)",
                _table(marks, head),
                "## Price process",
                _table(price, head),
                "## Robustness to the step width (BTCUSDT)",
                _table(robust_rows, robust_head),
            ]
        )
        + "\n"
    )


def _grid(delta: float) -> int:
    return int(np.argmin(np.abs(DELTA_GRID - delta)))


def plot(sim: Stats, btc: Stats, out: Path) -> None:
    fig = Figure(figsize=(6, 4))
    FigureCanvasAgg(fig)
    ax = fig.add_subplot()
    for name, st, colour in (("Simulator (base)", sim, "tab:blue"), ("BTCUSDT", btc, "tab:orange")):
        keep = st.probs > 0
        ax.semilogy(DELTA_GRID[keep], st.probs[keep], "o", color=colour, label=name)
        logp = np.log(st.probs[keep])
        intercept = float(np.mean(logp + st.exp_fit.slope * DELTA_GRID[keep]))
        fit = np.exp(intercept - st.exp_fit.slope * DELTA_GRID)
        ax.semilogy(
            DELTA_GRID,
            fit,
            "-",
            color=colour,
            alpha=0.6,
            label=f"{name} exp fit, k·σ = {st.exp_fit.slope:.2f}",
        )
    ax.set_xlabel("δ / σ_step")
    ax.set_ylabel("P(touch within one step)")
    ax.set_title("Fill decay")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def parse_seeds(text: str) -> tuple[int, ...]:
    if text == "dev":
        return load_config().evaluation.dev_seeds
    first, last = (int(x) for x in text.split("-"))
    return tuple(range(first, last + 1))


def _kept_interpretation(path: Path) -> str:
    """The hand-written section from INTERPRETATION_HEADING on, kept across reruns."""
    if not path.exists():
        return f"\n{INTERPRETATION_HEADING}\n\nTBD\n"
    text = path.read_text(encoding="utf-8")
    at = text.find(INTERPRETATION_HEADING)
    return "\n" + text[at:] if at >= 0 else f"\n{INTERPRETATION_HEADING}\n\nTBD\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", type=Path, required=True, help="BTCUSDT aggTrades zip")
    parser.add_argument("--out", type=Path, default=Path("docs/results/realism"))
    parser.add_argument(
        "--seeds", default="dev", help="simulator seeds: 'dev' or an inclusive range 'first-last'"
    )
    args = parser.parse_args()
    started = time.perf_counter()

    raw = load_aggtrades(args.data)
    orders = rz.merge_taker_orders(raw.times, raw.prices, raw.sizes, raw.signs)
    btc = btc_stats(orders)
    robust = btc_robustness(orders)
    seeds = parse_seeds(args.seeds)
    sim = sim_stats(seeds)

    config = load_config(scenario="base")
    meta = "\n".join(
        [
            (
                f"Data: Binance spot BTCUSDT aggTrades, 2026-11-25 ([zip]({SOURCE_URL}), sha256 "
                f"`{SOURCE_SHA256}`). {len(raw.times):,} aggTrades merged into {len(orders.times):,} "
                f"taker orders. Simulator: base scenario, dev seeds {seeds[0]}–{seeds[-1]}, "
                f"{config.n_steps} steps each, raw taker intents (no agent, no book)."
            ),
            "",
            (
                f"- Step = {STEP_SECONDS:g} s for BTCUSDT, one simulator step for the simulator. "
                "Distances and markouts are in σ_step (std of 1-step changes of the reference price), "
                "since BTC's tick is far finer than ours."
            ),
            (
                "- Taker order: consecutive aggTrades with the same timestamp and side merged (summed "
                "size, last = worst price). Simulator: each intent, priced at its limit for fill decay "
                "and at the true value for markouts; within-step arrival times drawn uniformly for the "
                "inter-arrival CV."
            ),
            (
                "- Reference price: BTCUSDT has no quote data here, so it is the last trade price "
                "(forward-filled per step); for the simulator it is the true value."
            ),
            (
                "- A bid at ref − δ counts as touched if a selling taker trades at or below it within "
                "the step (ask symmetric). Trade-through is not a fill: real quotes have a queue ahead "
                "of them."
            ),
            (
                "- Our quote would itself change taker behaviour; this only compares the flow we "
                "assume with the flow observed. Not a backtest, not a calibration."
            ),
        ]
    )
    args.out.mkdir(parents=True, exist_ok=True)
    path = args.out / REPORT_NAME
    path.write_text(report(sim, btc, robust, meta) + _kept_interpretation(path), encoding="utf-8")
    plot(sim, btc, args.out / PLOT_NAME)
    print(
        f"Wrote {args.out / REPORT_NAME} and {PLOT_NAME} in {time.perf_counter() - started:.1f} s"
    )


if __name__ == "__main__":
    main()
