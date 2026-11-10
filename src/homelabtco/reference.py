"""The same costs, computed the slow and literal way, to check `model.py` against.

No arrays and no formulas for sums: it walks the calendar day by day and hour by hour, buys hardware in the month a
purchase falls due, and adds the cloud bill month by month. It shares nothing with the vectorised model but the
scenario file and the meaning of the factors.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass

from homelabtco.config import Scenario


@dataclass
class Reference:
    hardware: list[float]
    energy: list[float]
    failures: list[float]
    recurring: list[float]
    time: list[float]
    residual: float
    cloud: dict[str, list[float]]

    def homelab_monthly(self) -> list[float]:
        return [
            self.hardware[i] + self.energy[i] + self.failures[i] + self.recurring[i] + self.time[i]
            for i in range(len(self.hardware))
        ]


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def run(sc: Scenario, factors: dict[str, float] | None = None) -> Reference:
    k = {"energy_price": 1.0, "power": 1.0, "utilisation": 1.0, "hardware_price": 1.0, "hardware_life": 1.0,
         "failure_rate": 1.0, "recurring": 1.0, "cloud_price": 1.0, "storage_size": 1.0}  # fmt: skip
    k.update(factors or {})
    n = sc.horizon_months
    hardware = [0.0] * n
    energy = [0.0] * n
    failures = [0.0] * n
    recurring = [0.0] * n
    time = [0.0] * n
    residual = 0.0

    # the calendar
    cal: list[tuple[int, int]] = []
    y, m = sc.start_year, sc.start_month
    for _ in range(n):
        cal.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1

    for item in sc.hardware:
        life = max(1, round(item.life_months * k["hardware_life"]))
        price = item.price_eur * item.count * k["hardware_price"]
        bought = 0
        month = 0
        while month < n:  # a purchase whenever the previous one is worn out
            hardware[month] += price
            bought = month
            month += life
        residual += price * max(0.0, 1.0 - (n - bought) / life)
        afr = min(1.0, item.annual_failure_rate * k["failure_rate"])
        for i in range(n):
            failures[i] += price * afr / 12

    idle = sum(it.idle_w * it.count for it in sc.hardware) * k["power"]
    load = sum(it.load_w * it.count for it in sc.hardware) * k["power"]
    for i, (yy, mm) in enumerate(cal):
        rise = (1 + sc.yearly_increase) ** (i // 12)
        for _day in range(calendar.monthrange(yy, mm)[1]):
            for hour in range(24):
                u = _clamp(sc.utilisation[hour] * k["utilisation"], 0.0, 1.0)
                watts = (idle + (load - idle) * u) * sc.overhead_factor
                energy[i] += watts / 1000 * sc.tariff[hour] * rise * k["energy_price"]
        recurring[i] = sum(eur for _, eur in sc.recurring) * k["recurring"]
        time[i] = sc.admin_hours_per_month * sc.hourly_value_eur

    cloud: dict[str, list[float]] = {}
    for c in sc.clouds:
        bill = []
        for i in range(n):
            month_total = 0.0
            for it in c.items:
                if it.kind == "fixed":
                    month_total += it.eur_per_month
                elif it.kind == "storage":
                    month_total += (it.tb + it.tb_growth_per_year * i / 12) * k["storage_size"] * it.eur_per_tb_month
                else:
                    month_total += it.tb_per_month * it.eur_per_tb
            bill.append(month_total * (1 + sc.cloud_yearly_increase) ** (i // 12) * k["cloud_price"])
        cloud[c.name] = bill
    return Reference(hardware, energy, failures, recurring, time, residual, cloud)


def breakeven(homelab: list[float], cloud: list[float]) -> int:
    a = b = 0.0
    for i, (x, y) in enumerate(zip(homelab, cloud, strict=True)):
        a += x
        b += y
        if a <= b:
            return i + 1
    return 0
