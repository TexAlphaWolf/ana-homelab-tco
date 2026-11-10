"""Everything the report says, as one JSON-able dictionary."""

from __future__ import annotations

import platform
from typing import Any

import numpy as np

from homelabtco import __version__, model, sensitivity
from homelabtco.config import GROUP_LABELS, GROUPS, Scenario

HISTOGRAM_BINS = 30


def average_watts(sc: Scenario) -> float:
    idle = sum(h.idle_w * h.count for h in sc.hardware)
    load = sum(h.load_w * h.count for h in sc.hardware)
    return sum((idle + (load - idle) * u) * sc.overhead_factor for u in sc.utilisation) / 24


def build_report(sc: Scenario, samples: int = 20_000, seed: int = 1, swing: float = 0.2) -> dict[str, Any]:
    costs = model.simulate(sc)
    home = costs.homelab_monthly()
    cash = float(costs.homelab_cash()[0])
    residual = float(costs.residual[0])
    net = cash - residual
    h = sc.horizon_months

    cum_home = np.cumsum(home[0])
    clouds = []
    series_cloud: dict[str, list[float]] = {}
    for c in sc.clouds:
        bill = costs.cloud[c.name]
        total = float(bill.sum())
        be = int(model.breakeven(home, bill)[0])
        clouds.append(
            {
                "name": c.name,
                "total_eur": total,
                "monthly_avg_eur": total / h,
                "advantage_eur": total - net,
                "advantage_cash_eur": total - cash,
                "breakeven_month": be,
                "breakeven_label": model.month_labels(sc)[be - 1] if be else None,
            }
        )
        series_cloud[c.name] = [round(float(x), 2) for x in np.cumsum(bill[0])]

    tornado = sensitivity.tornado(sc, swing)
    mc = sensitivity.montecarlo(sc, samples, seed)
    mc_out = []
    for c in sc.clouds:
        a = mc.advantage[c.name]
        counts, edges = np.histogram(a, bins=HISTOGRAM_BINS)
        mc_out.append(
            {
                "name": c.name,
                "p_home_cheaper": float((a > 0).mean()),
                "mean_eur": float(a.mean()),
                "p5_eur": float(np.percentile(a, 5)),
                "median_eur": float(np.median(a)),
                "p95_eur": float(np.percentile(a, 95)),
                "p_breakeven_within_horizon": float((mc.breakeven[c.name] > 0).mean()),
                "histogram": {"edges": [float(x) for x in edges], "counts": [int(x) for x in counts]},
            }
        )

    return {
        "kind": "report",
        "environment": {"homelabtco": __version__, "python": platform.python_version(), "numpy": np.__version__},
        "scenario": {
            "name": sc.name,
            "start": f"{sc.start_year}-{sc.start_month:02d}",
            "horizon_months": h,
            "capex_eur": sc.capex,
            "average_watts": average_watts(sc),
            "overhead_factor": sc.overhead_factor,
            "yearly_increase": sc.yearly_increase,
            "cloud_yearly_increase": sc.cloud_yearly_increase,
            "hardware": [
                {
                    "name": x.name,
                    "count": x.count,
                    "price_eur": x.price_eur,
                    "life_months": x.life_months,
                    "idle_w": x.idle_w,
                    "load_w": x.load_w,
                    "annual_failure_rate": x.annual_failure_rate,
                }
                for x in sc.hardware
            ],
            "uncertainty": sc.uncertainty,
        },
        "homelab": {
            "cash_eur": cash,
            "residual_eur": residual,
            "net_eur": net,
            "monthly_net_avg_eur": net / h,
            "components_eur": {
                "hardware": float(costs.hardware.sum()),
                "energy": float(costs.energy.sum()),
                "failures": float(costs.failures.sum()),
                "recurring": float(costs.recurring.sum()),
                "time": float(costs.time.sum()),
            },
        },
        "cloud": clouds,
        "series": {
            "months": model.month_labels(sc),
            "homelab_cum_eur": [round(float(x), 2) for x in cum_home],
            "cloud_cum_eur": series_cloud,
        },
        "sensitivity": {
            "swing": swing,
            "scenarios": {
                name: [
                    {"group": b.group, "label": GROUP_LABELS[b.group], "low_eur": b.low, "high_eur": b.high}
                    for b in bars
                ]
                for name, bars in tornado.items()
            },
            "groups": list(GROUPS),
        },
        "montecarlo": {"samples": samples, "seed": seed, "scenarios": mc_out},
    }
