"""The cost model, vectorised: many variants of one scenario are evaluated at once.

A *variant* is the scenario with each group of parameters multiplied by a factor (see `config.GROUPS`): 1.0 is the
scenario as written. Arrays have one row per variant and one column per month, so a sensitivity study and a Monte Carlo
run of a million variants use the same code as a single evaluation.

Cash view: hardware is bought in month 0 and again every `life_months` (a purchase in the last months still counts in
full); a residual value (what is left of the straight-line life at the end) is reported separately. Energy is charged
hour by hour on the real days of each calendar month.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from homelabtco.config import GROUPS, HOURS, CloudScenario, Scenario

F = NDArray[np.float64]


def days_in_months(sc: Scenario) -> F:
    out = np.empty(sc.horizon_months)
    y, m = sc.start_year, sc.start_month
    for i in range(sc.horizon_months):
        out[i] = calendar.monthrange(y, m)[1]
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def month_labels(sc: Scenario) -> list[str]:
    out = []
    y, m = sc.start_year, sc.start_month
    for _ in range(sc.horizon_months):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


@dataclass(frozen=True)
class Variants:
    """A factor for each group, one value per variant."""

    factors: dict[str, F]

    @property
    def n(self) -> int:
        return len(next(iter(self.factors.values())))

    @staticmethod
    def base(n: int = 1) -> Variants:
        return Variants({g: np.ones(n) for g in GROUPS})

    @staticmethod
    def one(**factors: float) -> Variants:
        unknown = set(factors) - set(GROUPS)
        if unknown:
            raise KeyError(f"unknown group(s) {sorted(unknown)}")
        return Variants({g: np.full(1, float(factors.get(g, 1.0))) for g in GROUPS})

    def slice(self, a: int, b: int) -> Variants:
        return Variants({g: v[a:b] for g, v in self.factors.items()})


@dataclass(frozen=True)
class Costs:
    """Monthly cash costs, shape (variants, months), plus the end-of-horizon residual value, shape (variants,)."""

    hardware: F
    energy: F
    failures: F
    recurring: F
    time: F
    residual: F
    cloud: dict[str, F]

    def homelab_monthly(self) -> F:
        return self.hardware + self.energy + self.failures + self.recurring + self.time

    def homelab_cash(self) -> F:
        return np.asarray(self.homelab_monthly().sum(axis=1))

    def homelab_net(self) -> F:
        return self.homelab_cash() - self.residual


def _life(sc: Scenario, v: Variants, base_life: int) -> NDArray[np.int64]:
    return np.maximum(1, np.rint(base_life * v.factors["hardware_life"])).astype(np.int64)


def cloud_monthly(sc: Scenario, cloud: CloudScenario, v: Variants) -> F:
    months = np.arange(sc.horizon_months, dtype=np.float64)
    growth = (1 + sc.cloud_yearly_increase) ** (months // 12)
    storage_factor = v.factors["storage_size"][:, None]
    total = np.zeros((v.n, sc.horizon_months))
    for it in cloud.items:
        if it.kind == "fixed":
            total += it.eur_per_month
        elif it.kind == "storage":
            tb = (it.tb + it.tb_growth_per_year * months / 12)[None, :] * storage_factor
            total += tb * it.eur_per_tb_month
        else:
            total += it.tb_per_month * it.eur_per_tb
    return total * growth[None, :] * v.factors["cloud_price"][:, None]


def simulate(sc: Scenario, v: Variants | None = None) -> Costs:
    v = v or Variants.base()
    n, h = v.n, sc.horizon_months
    months = np.arange(h)
    f = v.factors

    hardware = np.zeros((n, h))
    failures = np.zeros((n, h))
    residual = np.zeros(n)
    for item in sc.hardware:
        life = _life(sc, v, item.life_months)
        price = item.price_eur * item.count * f["hardware_price"]
        hardware += (months[None, :] % life[:, None] == 0) * price[:, None]
        last_buy = life * ((h - 1) // life)
        left = np.maximum(0.0, 1.0 - (h - last_buy) / life)
        residual += price * left
        afr = np.minimum(1.0, item.annual_failure_rate * f["failure_rate"])
        failures += (price * afr / 12)[:, None]

    idle = sum(it.idle_w * it.count for it in sc.hardware) * f["power"]
    load = sum(it.load_w * it.count for it in sc.hardware) * f["power"]
    u = np.clip(np.array(sc.utilisation)[None, :] * f["utilisation"][:, None], 0.0, 1.0)
    watts = (idle[:, None] + (load - idle)[:, None] * u) * sc.overhead_factor  # (variants, 24)
    per_day = (watts * np.array(sc.tariff)[None, :]).sum(axis=1) / 1000  # EUR for one day, at the base price
    rise = (1 + sc.yearly_increase) ** (months // 12)
    energy = per_day[:, None] * days_in_months(sc)[None, :] * rise[None, :] * f["energy_price"][:, None]

    recurring = np.broadcast_to((sum(eur for _, eur in sc.recurring) * f["recurring"])[:, None], (n, h)).copy()
    time = np.full((n, h), sc.admin_hours_per_month * sc.hourly_value_eur)
    cloud = {c.name: cloud_monthly(sc, c, v) for c in sc.clouds}
    return Costs(hardware, energy, failures, recurring, time, residual, cloud)


def breakeven(homelab_monthly: F, cloud_monthly_: F) -> NDArray[np.int64]:
    """First month number (1 is the first month) at which the cumulative cash spent on the home server is no more than
    on the cloud; 0 if that never happens within the horizon."""
    gap = np.cumsum(homelab_monthly, axis=1) - np.cumsum(cloud_monthly_, axis=1)
    below = gap <= 0
    first = below.argmax(axis=1) + 1
    return np.where(below.any(axis=1), first, 0).astype(np.int64)


assert HOURS == 24
