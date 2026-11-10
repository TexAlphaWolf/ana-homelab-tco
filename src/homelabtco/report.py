"""Markdown and figures built from a report or a benchmark (both are plain JSON)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#e69f00"]


def eur(v: float) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}€{abs(v):,.0f}"


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def closest(rep: dict[str, Any]) -> dict[str, Any]:
    """The cloud scenario with the smallest advantage in absolute terms, relative to its cost: the closest call."""
    return min(rep["cloud"], key=lambda c: abs(c["advantage_eur"]) / max(c["total_eur"], 1.0))


def render_report(rep: dict[str, Any]) -> str:
    s, h = rep["scenario"], rep["homelab"]
    n = s["horizon_months"]
    out = [
        f"# Total cost of ownership: {s['name']}",
        "",
        f"{n} months from {s['start']}. Hardware bought up front is {eur(s['capex_eur'])}; the parts draw {s['average_watts']:.0f} W on "
        f"average over a day (power-supply overhead x{s['overhead_factor']:g} included). Electricity rises {pct(s['yearly_increase'])} a "
        f"year, cloud prices {pct(s['cloud_yearly_increase'])} a year. Cash view: hardware is paid when bought and again when its "
        "life ends; what is left of its straight-line life at the end is shown as a residual value.",
        "",
        "## 1. The home server",
        "",
        "| Part | Count | Price each | Life (months) | Idle W | Load W | Failures a year |",
        "|---|---|---|---|---|---|---|",
    ]
    for x in s["hardware"]:
        out.append(
            f"| {x['name']} | {x['count']} | {eur(x['price_eur'])} | {x['life_months']} | {x['idle_w']:g} | {x['load_w']:g} | {pct(x['annual_failure_rate'])} |"
        )
    c = h["components_eur"]
    out += [
        "",
        f"## 2. What it costs over {n} months",
        "",
        "| Item | EUR |",
        "|---|---|",
        f"| Hardware purchases (including replacements) | {eur(c['hardware'])} |",
        f"| Electricity | {eur(c['energy'])} |",
        f"| Expected failures (spares) | {eur(c['failures'])} |",
        f"| Recurring (domain, off-site backup, ...) | {eur(c['recurring'])} |",
        f"| Your time, valued | {eur(c['time'])} |",
        f"| **Cash spent** | **{eur(h['cash_eur'])}** |",
        f"| Residual value of the hardware at the end | -{eur(h['residual_eur'])} |",
        f"| **Net cost** | **{eur(h['net_eur'])}** ({eur(h['monthly_net_avg_eur'])} a month) |",
        "",
        "## 3. Against the cloud",
        "",
        "*Home server saves* is the cloud bill minus the home server's net cost; the break-even is the first month in which the cash "
        "spent on the home server (all of it, bought up front) is no more than the cloud bill so far.",
        "",
        "| Cloud alternative | Cloud bill | A month | Home server saves | Break-even |",
        "|---|---|---|---|---|",
    ]
    for cl in rep["cloud"]:
        be = (
            f"month {cl['breakeven_month']} ({cl['breakeven_label']})"
            if cl["breakeven_month"]
            else f"not within {n} months"
        )
        out.append(
            f"| {cl['name']} | {eur(cl['total_eur'])} | {eur(cl['monthly_avg_eur'])} | {eur(cl['advantage_eur'])} | {be} |"
        )
    sw = rep["sensitivity"]["swing"]
    out += [
        "",
        "## 4. What moves the answer",
        "",
        f"Each group of numbers in turn {pct(sw)} lower and {pct(sw)} higher, the rest as written; the cell is what the home server "
        "saves over that cloud alternative (negative: it costs more). Largest effect first.",
    ]
    for name, bars in rep["sensitivity"]["scenarios"].items():
        out += ["", f"**{name}**", "", f"| Group | At -{sw * 100:.0f}% | At +{sw * 100:.0f}% |", "|---|---|---|"]
        for b in bars:
            out.append(f"| {b['label']} | {eur(b['low_eur'])} | {eur(b['high_eur'])} |")
    mc = rep["montecarlo"]
    out += [
        "",
        "## 5. Monte Carlo",
        "",
        f"{mc['samples']:,} variants (seed {mc['seed']}), every group of numbers drawn independently from a triangular distribution that "
        "peaks at the value as written and reaches the spread set in `uncertainty`.",
        "",
        "| Cloud alternative | Home server cheaper | 5th percentile | Median | 95th percentile | Break-even within horizon |",
        "|---|---|---|---|---|---|",
    ]
    for m in mc["scenarios"]:
        out.append(
            f"| {m['name']} | {pct(m['p_home_cheaper'])} | {eur(m['p5_eur'])} | {eur(m['median_eur'])} | {eur(m['p95_eur'])} | {pct(m['p_breakeven_within_horizon'])} |"
        )
    return "\n".join(out) + "\n"


def report_figure(rep: dict[str, Any], path: Path) -> None:
    ser = rep["series"]
    x = np.arange(1, len(ser["months"]) + 1)
    fig, (a, b, c) = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    a.plot(x, ser["homelab_cum_eur"], color="black", lw=2.2, label="home server (cash)")
    for i, (name, vals) in enumerate(ser["cloud_cum_eur"].items()):
        a.plot(x, vals, color=COLORS[i % len(COLORS)], label=name)
    a.set_xlabel("months")
    a.set_ylabel("cumulative cash, EUR")
    a.set_title("Cash spent so far")
    a.legend(fontsize=7)
    a.grid(alpha=0.25)

    pick = closest(rep)
    bars = rep["sensitivity"]["scenarios"][pick["name"]]
    base = pick["advantage_eur"]
    ys = np.arange(len(bars))[::-1]
    for y, bar in zip(ys, bars, strict=True):
        lo, hi = bar["low_eur"], bar["high_eur"]
        b.barh(y, lo - base, left=base, color="#56b4e9", height=0.6)
        b.barh(y, hi - base, left=base, color="#e69f00", height=0.6)
    b.axvline(base, color="black", lw=1)
    b.axvline(0, color="grey", lw=0.8, ls="--")
    b.set_yticks(ys, [bar["label"] for bar in bars], fontsize=8)
    sw = rep["sensitivity"]["swing"]
    b.set_xlabel(f"what the home server saves, EUR (blue: -{sw * 100:.0f}%, orange: +{sw * 100:.0f}%)")
    b.set_title(f"What moves the answer\n{pick['name']}", fontsize=10)

    m = next(m for m in rep["montecarlo"]["scenarios"] if m["name"] == pick["name"])
    edges, counts = np.array(m["histogram"]["edges"]), np.array(m["histogram"]["counts"])
    c.bar(edges[:-1], counts, width=np.diff(edges), align="edge", color="#009e73")
    c.axvline(0, color="black", lw=1)
    c.set_xlabel("what the home server saves, EUR")
    c.set_ylabel("variants")
    c.set_title(
        f"Monte Carlo: cheaper in {pct(m['p_home_cheaper'])} of {rep['montecarlo']['samples']:,}\n{pick['name']}",
        fontsize=10,
    )
    fig.suptitle(
        f"homelabtco {rep['environment']['homelabtco']}: {rep['scenario']['name']}, {rep['scenario']['horizon_months']} months",
        fontsize=10,
    )
    fig.savefig(path, dpi=130)
    plt.close(fig)


def secs(v: float) -> str:
    if v < 0.001:
        return f"{v * 1e6:,.0f} µs"
    if v < 1:
        return f"{v * 1e3:,.1f} ms"
    return f"{v:,.2f} s"


def render_bench(bench: dict[str, Any]) -> str:
    env = bench["environment"]
    out = [
        "# Benchmark",
        "",
        f"Run on {env['system']}, {env['cpus']} CPUs, Python {env['python']}, NumPy {env['numpy']}; scenario `{env['scenario']}` "
        f"({env['horizon_months']} months, {env['cloud_scenarios']} cloud alternatives); seed {env['seed']}; each time is the median of "
        f"{env['repeat']} runs; command `{env['command']}`.",
        "",
        "## 1. Monte Carlo by number of variants",
        "",
        "Every variant is the whole scenario evaluated again (hardware purchases, 24 hours of energy for each month, every cloud bill "
        "and the break-even months). *Literal simulation* is the time of the day-by-day reference for one variant multiplied by the "
        "number of variants: an extrapolation, not a measurement.",
        "",
        "| Variants | Time | Variants per second | Literal simulation (extrapolated) | Speed-up |",
        "|---|---|---|---|---|",
    ]
    ref = bench["reference_s"]
    for r in bench["montecarlo"]:
        est = ref * r["samples"]
        out.append(
            f"| {r['samples']:,} | {secs(r['seconds'])} | {r['samples'] / r['seconds']:,.0f} | {secs(est)} | {est / r['seconds']:,.0f}x |"
        )
    out += [
        "",
        f"One variant by the literal simulation takes {secs(ref)} (median); by the vectorised model on its own, one evaluation "
        f"takes {secs(bench['single_s'])}.",
        "",
        "## 2. Time by horizon (10,000 variants)",
        "",
        "| Horizon (months) | Time | Variants per second |",
        "|---|---|---|",
    ]
    for r in bench["horizon"]:
        out.append(f"| {r['months']} | {secs(r['seconds'])} | {r['samples'] / r['seconds']:,.0f} |")
    v = bench["verification"]
    out += [
        "",
        "## 3. Agreement with the literal simulation",
        "",
        f"{v['checks']} comparisons (the scenario as written and {v['checks'] - 1} random variants): every monthly cost, the residual "
        f"value and every break-even month. Largest relative difference {v['max_rel_error']:.2e} (tolerance {v['tolerance']:.0e}); "
        f"{'all match' if v['ok'] else 'MISMATCH'}.",
    ]
    return "\n".join(out) + "\n"


def bench_figure(bench: dict[str, Any], path: Path) -> None:
    mc = bench["montecarlo"]
    n = [r["samples"] for r in mc]
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.6), constrained_layout=True)
    ref = bench["reference_s"]
    a.plot(n, [r["seconds"] for r in mc], marker="o", color="#0072b2", label="vectorised model")
    a.plot(n, [ref * k for k in n], marker="s", ls="--", color="#d55e00", label="literal simulation (extrapolated)")
    a.set_xscale("log")
    a.set_yscale("log")
    a.set_xlabel("variants")
    a.set_ylabel("seconds")
    a.set_title("Monte Carlo: time against variants")
    a.legend(fontsize=8)
    a.grid(alpha=0.25, which="both")
    hz = bench["horizon"]
    b.plot([r["months"] for r in hz], [r["samples"] / r["seconds"] for r in hz], marker="o", color="#009e73")
    b.set_xlabel("horizon, months")
    b.set_ylabel("variants per second")
    b.set_ylim(0, None)
    b.set_title("Throughput against horizon (10,000 variants)")
    b.grid(alpha=0.25)
    fig.suptitle(f"homelabtco {bench['environment']['homelabtco']}", fontsize=10)
    fig.savefig(path, dpi=130)
    plt.close(fig)
