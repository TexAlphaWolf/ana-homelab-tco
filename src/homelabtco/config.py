"""The scenario file: what the server is made of, what it draws, what it costs, and what the cloud would charge.

The file is YAML. Everything is checked when it is read, so that a typo is an error with the path of the field
(`hardware[2].life_months`) and not a strange number in a report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

HOURS = 24
GROUPS = (
    "energy_price",
    "power",
    "utilisation",
    "hardware_price",
    "hardware_life",
    "failure_rate",
    "recurring",
    "cloud_price",
    "storage_size",
)
GROUP_LABELS = {
    "energy_price": "Electricity price",
    "power": "Power draw of the hardware",
    "utilisation": "Time spent at load",
    "hardware_price": "Hardware prices",
    "hardware_life": "Hardware life",
    "failure_rate": "Failure rate",
    "recurring": "Recurring costs",
    "cloud_price": "Cloud prices",
    "storage_size": "Storage needed",
}
DEFAULT_UNCERTAINTY = {
    "energy_price": 0.30,
    "power": 0.15,
    "utilisation": 0.40,
    "hardware_price": 0.15,
    "hardware_life": 0.25,
    "failure_rate": 0.50,
    "recurring": 0.20,
    "cloud_price": 0.25,
    "storage_size": 0.30,
}


class ConfigError(ValueError):
    """The scenario file is not valid."""


@dataclass(frozen=True)
class Hardware:
    name: str
    count: int
    price_eur: float
    life_months: int
    idle_w: float
    load_w: float
    annual_failure_rate: float = 0.0


@dataclass(frozen=True)
class CloudItem:
    kind: str  # fixed, storage, egress
    name: str
    eur_per_month: float = 0.0
    tb: float = 0.0
    tb_growth_per_year: float = 0.0
    eur_per_tb_month: float = 0.0
    tb_per_month: float = 0.0
    eur_per_tb: float = 0.0


@dataclass(frozen=True)
class CloudScenario:
    name: str
    items: tuple[CloudItem, ...]


@dataclass(frozen=True)
class Scenario:
    name: str
    start_year: int
    start_month: int
    horizon_months: int
    tariff: tuple[float, ...]  # EUR per kWh, by hour of day
    yearly_increase: float
    overhead_factor: float
    utilisation: tuple[float, ...]  # share of the hour at load power, by hour of day
    hardware: tuple[Hardware, ...]
    recurring: tuple[tuple[str, float], ...]
    admin_hours_per_month: float
    hourly_value_eur: float
    cloud_yearly_increase: float
    clouds: tuple[CloudScenario, ...]
    uncertainty: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_UNCERTAINTY))

    @property
    def capex(self) -> float:
        return sum(h.price_eur * h.count for h in self.hardware)


def _fail(path: str, message: str) -> ConfigError:
    return ConfigError(f"{path}: {message}")


def _mapping(value: Any, path: str, allowed: set[str], required: set[str] = frozenset()) -> dict[str, Any]:  # type: ignore[assignment]
    if not isinstance(value, dict):
        raise _fail(path, "must be a mapping")
    unknown = set(value) - allowed
    if unknown:
        raise _fail(path, f"unknown key(s) {sorted(unknown)}; allowed: {sorted(allowed)}")
    missing = set(required) - set(value)
    if missing:
        raise _fail(path, f"missing {sorted(missing)}")
    return value


def _number(value: Any, path: str, low: float | None = None, high: float | None = None, integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _fail(path, f"must be a number, got {value!r}")
    if integer and float(value) != int(value):
        raise _fail(path, f"must be a whole number, got {value!r}")
    v = float(value)
    if v != v or v in (float("inf"), float("-inf")):
        raise _fail(path, "must be finite")
    if low is not None and v < low:
        raise _fail(path, f"must be at least {low}, got {value}")
    if high is not None and v > high:
        raise _fail(path, f"must be at most {high}, got {value}")
    return v


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _fail(path, "must be a non-empty text")
    return value.strip()


def _hourly(value: Any, path: str, low: float, high: float | None) -> tuple[float, ...]:
    """One number for every hour, or 24 numbers (hour 0 to 23)."""
    if isinstance(value, list):
        if len(value) != HOURS:
            raise _fail(path, f"must be one number or {HOURS} numbers (one per hour), got {len(value)}")
        return tuple(_number(v, f"{path}[{i}]", low, high) for i, v in enumerate(value))
    return (_number(value, path, low, high),) * HOURS


def _hardware(raw: Any, path: str) -> Hardware:
    keys = {"name", "count", "price_eur", "life_months", "idle_w", "load_w", "annual_failure_rate"}
    d = _mapping(raw, path, keys, {"name", "price_eur", "life_months", "idle_w", "load_w"})
    idle = _number(d["idle_w"], f"{path}.idle_w", 0)
    load = _number(d["load_w"], f"{path}.load_w", 0)
    if load < idle:
        raise _fail(path, f"load_w ({load}) is below idle_w ({idle})")
    return Hardware(
        name=_text(d["name"], f"{path}.name"),
        count=int(_number(d.get("count", 1), f"{path}.count", 1, integer=True)),
        price_eur=_number(d["price_eur"], f"{path}.price_eur", 0),
        life_months=int(_number(d["life_months"], f"{path}.life_months", 1, 1200, integer=True)),
        idle_w=idle,
        load_w=load,
        annual_failure_rate=_number(d.get("annual_failure_rate", 0), f"{path}.annual_failure_rate", 0, 1),
    )


def _cloud_item(raw: Any, path: str) -> CloudItem:
    if not isinstance(raw, dict) or raw.get("type") not in ("fixed", "storage", "egress"):
        raise _fail(path, "needs type: fixed, storage or egress")
    kind = raw["type"]
    fields = {
        "fixed": ({"type", "name", "eur_per_month"}, {"name", "eur_per_month"}),
        "storage": (
            {"type", "name", "tb", "tb_growth_per_year", "eur_per_tb_month"},
            {"name", "tb", "eur_per_tb_month"},
        ),
        "egress": ({"type", "name", "tb_per_month", "eur_per_tb"}, {"name", "tb_per_month", "eur_per_tb"}),
    }[kind]
    d = _mapping(raw, path, fields[0], fields[1])
    name = _text(d["name"], f"{path}.name")
    if kind == "fixed":
        return CloudItem(kind, name, eur_per_month=_number(d["eur_per_month"], f"{path}.eur_per_month", 0))
    if kind == "storage":
        return CloudItem(
            kind,
            name,
            tb=_number(d["tb"], f"{path}.tb", 0),
            tb_growth_per_year=_number(d.get("tb_growth_per_year", 0), f"{path}.tb_growth_per_year", 0),
            eur_per_tb_month=_number(d["eur_per_tb_month"], f"{path}.eur_per_tb_month", 0),
        )
    return CloudItem(
        kind,
        name,
        tb_per_month=_number(d["tb_per_month"], f"{path}.tb_per_month", 0),
        eur_per_tb=_number(d["eur_per_tb"], f"{path}.eur_per_tb", 0),
    )


def parse(raw: Any) -> Scenario:
    top = {
        "name",
        "start",
        "horizon_months",
        "electricity",
        "load",
        "hardware",
        "recurring",
        "admin",
        "cloud",
        "uncertainty",
    }
    d = _mapping(raw, "scenario", top, {"name", "horizon_months", "electricity", "hardware", "cloud"})
    start = str(d.get("start", "2026-01"))
    try:
        year_s, month_s = start.split("-")
        year, month = int(year_s), int(month_s)
    except ValueError as exc:
        raise _fail("start", f"must look like 2026-01, got {start!r}") from exc
    if not (1900 <= year <= 2200 and 1 <= month <= 12):
        raise _fail("start", f"not a valid month: {start!r}")

    el = _mapping(
        d["electricity"], "electricity", {"eur_per_kwh", "yearly_increase", "overhead_factor"}, {"eur_per_kwh"}
    )
    load = _mapping(d.get("load", {}), "load", {"utilisation"})
    hw_raw = d["hardware"]
    if not isinstance(hw_raw, list) or not hw_raw:
        raise _fail("hardware", "must be a list with at least one item")
    hardware = tuple(_hardware(h, f"hardware[{i}]") for i, h in enumerate(hw_raw))
    names = [h.name for h in hardware]
    if len(set(names)) != len(names):
        raise _fail("hardware", "names must be unique")

    rec_raw = d.get("recurring", [])
    if not isinstance(rec_raw, list):
        raise _fail("recurring", "must be a list")
    recurring = []
    for i, r in enumerate(rec_raw):
        rd = _mapping(r, f"recurring[{i}]", {"name", "eur_per_month"}, {"name", "eur_per_month"})
        recurring.append(
            (
                _text(rd["name"], f"recurring[{i}].name"),
                _number(rd["eur_per_month"], f"recurring[{i}].eur_per_month", 0),
            )
        )

    admin = _mapping(d.get("admin", {}), "admin", {"hours_per_month", "hourly_value_eur"})
    cl = _mapping(d["cloud"], "cloud", {"yearly_increase", "scenarios"}, {"scenarios"})
    sc_raw = cl["scenarios"]
    if not isinstance(sc_raw, list) or not sc_raw:
        raise _fail("cloud.scenarios", "must be a list with at least one scenario")
    clouds = []
    for i, s in enumerate(sc_raw):
        p = f"cloud.scenarios[{i}]"
        sd = _mapping(s, p, {"name", "items"}, {"name", "items"})
        if not isinstance(sd["items"], list) or not sd["items"]:
            raise _fail(f"{p}.items", "must be a list with at least one item")
        clouds.append(
            CloudScenario(
                _text(sd["name"], f"{p}.name"),
                tuple(_cloud_item(it, f"{p}.items[{j}]") for j, it in enumerate(sd["items"])),
            )
        )
    if len({c.name for c in clouds}) != len(clouds):
        raise _fail("cloud.scenarios", "names must be unique")

    unc = dict(DEFAULT_UNCERTAINTY)
    for k, v in _mapping(d.get("uncertainty", {}), "uncertainty", set(GROUPS)).items():
        unc[k] = _number(v, f"uncertainty.{k}", 0, 0.95)

    return Scenario(
        name=_text(d["name"], "name"),
        start_year=year,
        start_month=month,
        horizon_months=int(_number(d["horizon_months"], "horizon_months", 1, 600, integer=True)),
        tariff=_hourly(el["eur_per_kwh"], "electricity.eur_per_kwh", 0, None),
        yearly_increase=_number(el.get("yearly_increase", 0), "electricity.yearly_increase", -0.5, 1),
        overhead_factor=_number(el.get("overhead_factor", 1.0), "electricity.overhead_factor", 1, 3),
        utilisation=_hourly(load.get("utilisation", 0.2), "load.utilisation", 0, 1),
        hardware=hardware,
        recurring=tuple(recurring),
        admin_hours_per_month=_number(admin.get("hours_per_month", 0), "admin.hours_per_month", 0),
        hourly_value_eur=_number(admin.get("hourly_value_eur", 0), "admin.hourly_value_eur", 0),
        cloud_yearly_increase=_number(cl.get("yearly_increase", 0), "cloud.yearly_increase", -0.5, 1),
        clouds=tuple(clouds),
        uncertainty=unc,
    )


def load(path: Path) -> Scenario:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror or exc}") from exc
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path} is not valid YAML: {exc}") from exc
    return parse(raw)
