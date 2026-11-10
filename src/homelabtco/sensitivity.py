"""One-at-a-time sensitivity and Monte Carlo on the factors of `model.Variants`."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from homelabtco import model
from homelabtco.config import GROUP_LABELS, GROUPS, Scenario

F = NDArray[np.float64]


def advantage(sc: Scenario, v: model.Variants) -> dict[str, F]:
    """What the home server saves over each cloud scenario at the end of the horizon, in EUR, per variant: the cloud
    bill minus the home server's cash cost net of the value of the hardware left. Positive means the home server wins."""
    costs = model.simulate(sc, v)
    net = costs.homelab_net()
    return {name: bill.sum(axis=1) - net for name, bill in costs.cloud.items()}


@dataclass(frozen=True)
class Bar:
    group: str
    label: str
    low: float  # advantage with the group at (1 - swing)
    high: float  # advantage with the group at (1 + swing)

    @property
    def spread(self) -> float:
        return abs(self.high - self.low)


def tornado(sc: Scenario, swing: float = 0.2) -> dict[str, list[Bar]]:
    """Each group of parameters in turn at (1 - swing) and (1 + swing), the others as written; largest effect first."""
    if not 0 < swing < 1:
        raise ValueError("swing must be between 0 and 1")
    n = len(GROUPS)
    factors = {g: np.ones(2 * n) for g in GROUPS}
    for i, g in enumerate(GROUPS):
        factors[g][2 * i] = 1 - swing
        factors[g][2 * i + 1] = 1 + swing
    adv = advantage(sc, model.Variants(factors))
    out: dict[str, list[Bar]] = {}
    for name, vals in adv.items():
        bars = [Bar(g, GROUP_LABELS[g], float(vals[2 * i]), float(vals[2 * i + 1])) for i, g in enumerate(GROUPS)]
        out[name] = sorted(bars, key=lambda b: -b.spread)
    return out


@dataclass(frozen=True)
class MonteCarlo:
    samples: int
    seed: int
    advantage: dict[str, F]
    breakeven: dict[str, NDArray[np.int64]]


def draw(sc: Scenario, samples: int, seed: int) -> model.Variants:
    """Independent triangular factors (peak at 1, spread from `sc.uncertainty`) for every group."""
    if samples < 1:
        raise ValueError("samples must be at least 1")
    rng = np.random.default_rng(seed)
    factors: dict[str, F] = {}
    for g in GROUPS:
        s = sc.uncertainty[g]
        factors[g] = rng.triangular(1 - s, 1.0, 1 + s, samples) if s > 0 else np.ones(samples)
    return model.Variants(factors)


def montecarlo(sc: Scenario, samples: int, seed: int, chunk: int = 20_000) -> MonteCarlo:
    v = draw(sc, samples, seed)
    adv: dict[str, list[F]] = {c.name: [] for c in sc.clouds}
    be: dict[str, list[NDArray[np.int64]]] = {c.name: [] for c in sc.clouds}
    for a in range(0, samples, chunk):
        part = v.slice(a, min(samples, a + chunk))
        costs = model.simulate(sc, part)
        net = costs.homelab_net()
        home = costs.homelab_monthly()
        for name, bill in costs.cloud.items():
            adv[name].append(bill.sum(axis=1) - net)
            be[name].append(model.breakeven(home, bill))
    return MonteCarlo(
        samples, seed, {k: np.concatenate(x) for k, x in adv.items()}, {k: np.concatenate(x) for k, x in be.items()}
    )
