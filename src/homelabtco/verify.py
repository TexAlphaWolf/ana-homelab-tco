"""Check the vectorised model against the literal simulation, on the scenario as written and on random variants."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from homelabtco import model, reference, sensitivity
from homelabtco.config import GROUPS, Scenario

RTOL = 1e-9


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    max_rel_error: float
    detail: str


def _rel(a: np.ndarray, b: np.ndarray) -> float:
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.max(np.abs(a - b) / np.maximum(1.0, np.abs(b)))) if a.size else 0.0


def compare(sc: Scenario, factors: dict[str, float]) -> tuple[float, str]:
    """Largest relative difference over everything that is compared, and what was compared."""
    fast = model.simulate(sc, model.Variants.one(**factors))
    slow = reference.run(sc, factors)
    errs: dict[str, float] = {
        "hardware": _rel(fast.hardware[0], np.array(slow.hardware)),
        "energy": _rel(fast.energy[0], np.array(slow.energy)),
        "failures": _rel(fast.failures[0], np.array(slow.failures)),
        "recurring": _rel(fast.recurring[0], np.array(slow.recurring)),
        "time": _rel(fast.time[0], np.array(slow.time)),
        "residual": _rel(fast.residual, np.array([slow.residual])),
    }
    for name, bill in fast.cloud.items():
        errs[f"cloud: {name}"] = _rel(bill[0], np.array(slow.cloud[name]))
        be_fast = int(model.breakeven(fast.homelab_monthly(), bill)[0])
        be_slow = reference.breakeven(slow.homelab_monthly(), slow.cloud[name])
        errs[f"break-even: {name}"] = 0.0 if be_fast == be_slow else 1.0
    worst = max(errs, key=lambda k: errs[k])
    return errs[worst], f"worst: {worst}"


def verify(sc: Scenario, draws: int = 25, seed: int = 1) -> list[Check]:
    """The scenario as written, then `draws` random variants within the scenario's uncertainty."""
    out = []
    err, detail = compare(sc, {})
    out.append(Check("scenario as written", err <= RTOL, err, detail))
    v = sensitivity.draw(sc, max(draws, 1), seed)
    for i in range(draws):
        factors = {g: float(v.factors[g][i]) for g in GROUPS}
        err, detail = compare(sc, factors)
        out.append(Check(f"random variant {i + 1}", err <= RTOL, err, detail))
    return out
