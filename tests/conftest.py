from __future__ import annotations

import copy
import os
from typing import Any

import pytest

from homelabtco import cli, config

SEED = int(os.environ.get("TCO_TEST_SEED", "1"))
DRAWS = int(os.environ.get("TCO_TEST_DRAWS", "25"))

SIMPLE: dict[str, Any] = {
    "name": "Simple",
    "start": "2027-01",
    "horizon_months": 24,
    "electricity": {"eur_per_kwh": 0.25},
    "load": {"utilisation": 0.5},
    "hardware": [{"name": "Box", "price_eur": 1200, "life_months": 36, "idle_w": 20, "load_w": 60}],
    "recurring": [{"name": "Domain", "eur_per_month": 3}],
    "cloud": {"scenarios": [{"name": "VM", "items": [{"type": "fixed", "name": "VM", "eur_per_month": 100}]}]},
}


def raw(**changes: Any) -> dict[str, Any]:
    d = copy.deepcopy(SIMPLE)
    d.update(changes)
    return d


def simple(**changes: Any) -> config.Scenario:
    return config.parse(raw(**changes))


@pytest.fixture(scope="session")
def example() -> config.Scenario:
    return cli.load_scenario(None)
