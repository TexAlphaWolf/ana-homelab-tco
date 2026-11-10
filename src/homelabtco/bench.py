"""How fast the cost model is, and that it still agrees with the literal simulation."""

from __future__ import annotations

import os
import platform
import statistics
import time
from collections.abc import Callable
from dataclasses import replace
from functools import partial
from typing import Any

import numpy as np

from homelabtco import __version__, model, reference, sensitivity, verify
from homelabtco.config import Scenario


def timed(fn: Callable[[], object], repeat: int) -> float:
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        fn()
        runs.append(time.perf_counter() - t0)
    return statistics.median(runs)


def run_bench(
    sc: Scenario,
    scenario_name: str,
    sizes: list[int],
    repeat: int,
    seed: int,
    draws: int,
    command: str,
    progress: Callable[[str], None] = lambda _m: None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    progress("literal simulation: one variant")
    ref_s = timed(lambda: reference.run(sc), repeat)
    progress("vectorised model: one evaluation")
    single_s = timed(lambda: model.simulate(sc), repeat)
    mc = []
    for n in sizes:
        progress(f"Monte Carlo with {n:,} variants")
        mc.append({"samples": n, "seconds": timed(partial(sensitivity.montecarlo, sc, n, seed), repeat)})
    horizon = []
    for months in (60, 120, 240, 480):
        progress(f"horizon of {months} months")
        long = replace(sc, horizon_months=months)
        horizon.append(
            {
                "months": months,
                "samples": 10_000,
                "seconds": timed(partial(sensitivity.montecarlo, long, 10_000, seed), repeat),
            }
        )
    progress(f"agreement with the literal simulation on {draws} random variants")
    checks = verify.verify(sc, draws, seed)
    worst = max(c.max_rel_error for c in checks)
    return {
        "kind": "bench",
        "environment": {
            "homelabtco": __version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "system": f"{platform.system()} {platform.machine()}",
            "cpus": os.cpu_count(),
            "scenario": scenario_name,
            "horizon_months": sc.horizon_months,
            "cloud_scenarios": len(sc.clouds),
            "seed": seed,
            "repeat": repeat,
            "command": command,
            "seconds": round(time.perf_counter() - t0, 1),
        },
        "reference_s": ref_s,
        "single_s": single_s,
        "montecarlo": mc,
        "horizon": horizon,
        "verification": {
            "checks": len(checks),
            "ok": all(c.ok for c in checks),
            "max_rel_error": worst,
            "tolerance": verify.RTOL,
        },
    }
