from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from homelabtco import config

from .conftest import SIMPLE, raw, simple


def test_example_loads(example: config.Scenario) -> None:
    assert example.name.startswith("Home server") and example.horizon_months == 60
    assert len(example.hardware) == 5 and len(example.clouds) == 3
    assert example.capex == 900 + 4 * 250 + 120 + 150 + 60
    assert len(example.tariff) == 24 and len(example.utilisation) == 24
    assert example.uncertainty["energy_price"] == 0.30 and example.uncertainty["power"] == 0.15  # default kept


def test_scalars_become_24_hours() -> None:
    sc = simple()
    assert sc.tariff == (0.25,) * 24 and sc.utilisation == (0.5,) * 24 and sc.hardware[0].count == 1


def bad(path: list[Any], value: Any) -> dict[str, Any]:
    d = copy.deepcopy(SIMPLE)
    node = d
    for key in path[:-1]:
        node = node[key]
    if value is KeyError:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return d


@pytest.mark.parametrize(
    ("data", "needle"),
    [
        (bad(["horizon_months"], 0), "horizon_months"),
        (bad(["horizon_months"], 12.5), "whole number"),
        (bad(["horizon_months"], "x"), "must be a number"),
        (bad(["horizon_months"], True), "must be a number"),
        (bad(["horizon_months"], KeyError), "missing"),
        (bad(["start"], "2027/01"), "start"),
        (bad(["start"], "2027-13"), "start"),
        (bad(["electricity", "eur_per_kwh"], [0.2] * 5), "24 numbers"),
        (bad(["electricity", "eur_per_kwh"], -1), "at least"),
        (bad(["electricity", "overhead_factor"], 0.5), "overhead_factor"),
        (bad(["electricity", "color"], 1), "unknown key"),
        (bad(["load", "utilisation"], 1.5), "at most"),
        (bad(["hardware"], []), "at least one"),
        (bad(["hardware", 0, "load_w"], 5), "below idle_w"),
        (bad(["hardware", 0, "count"], 0), "count"),
        (bad(["hardware", 0, "price_eur"], -5), "price_eur"),
        (bad(["hardware", 0, "annual_failure_rate"], 2), "annual_failure_rate"),
        (bad(["hardware", 0, "name"], " "), "non-empty"),
        (bad(["hardware", 0], "box"), "mapping"),
        (bad(["recurring", 0, "eur_per_month"], -1), "eur_per_month"),
        (bad(["recurring"], "x"), "must be a list"),
        (bad(["cloud", "scenarios"], []), "at least one"),
        (bad(["cloud", "scenarios", 0, "items"], []), "at least one"),
        (bad(["cloud", "scenarios", 0, "items", 0, "type"], "gpu"), "needs type"),
        (bad(["cloud", "scenarios", 0, "items", 0, "eur_per_month"], KeyError), "missing"),
        (bad(["uncertainty"], {"nothing": 0.1}), "unknown key"),
        (bad(["uncertainty"], {"power": 1.5}), "at most"),
        ([1, 2], "mapping"),
    ],
)
def test_invalid_scenarios_say_where(data: Any, needle: str) -> None:
    with pytest.raises(config.ConfigError, match=needle):
        config.parse(data)


def test_duplicate_names_are_refused() -> None:
    d = raw()
    d["hardware"] = d["hardware"] * 2
    with pytest.raises(config.ConfigError, match="unique"):
        config.parse(d)
    d = raw()
    d["cloud"]["scenarios"] = d["cloud"]["scenarios"] * 2
    with pytest.raises(config.ConfigError, match="unique"):
        config.parse(d)


def test_the_three_kinds_of_cloud_item() -> None:
    d = raw()
    d["cloud"]["scenarios"][0]["items"] = [
        {"type": "fixed", "name": "a", "eur_per_month": 1},
        {"type": "storage", "name": "b", "tb": 2, "eur_per_tb_month": 5, "tb_growth_per_year": 1},
        {"type": "egress", "name": "c", "tb_per_month": 1, "eur_per_tb": 9},
    ]
    kinds = [i.kind for i in config.parse(d).clouds[0].items]
    assert kinds == ["fixed", "storage", "egress"]


def test_load_from_files(tmp_path: Path) -> None:
    with pytest.raises(config.ConfigError, match="cannot read"):
        config.load(tmp_path / "none.yaml")
    f = tmp_path / "x.yaml"
    f.write_text("name: [unclosed", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="not valid YAML"):
        config.load(f)
    f.write_text("name: only a name\n", encoding="utf-8")
    with pytest.raises(config.ConfigError, match="missing"):
        config.load(f)
