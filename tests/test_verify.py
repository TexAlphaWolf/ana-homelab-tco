"""The model against the literal simulation, on the example and on many random scenarios."""

from __future__ import annotations

import numpy as np
import pytest

from homelabtco import config, model, reference, verify

from .conftest import DRAWS, SEED


def random_scenario(rng: np.random.Generator) -> config.Scenario:
    n_hw = int(rng.integers(1, 5))
    hw = []
    for i in range(n_hw):
        idle = float(rng.uniform(0, 50))
        hw.append(
            {
                "name": f"part{i}",
                "count": int(rng.integers(1, 5)),
                "price_eur": float(rng.uniform(10, 900)),
                "life_months": int(rng.integers(1, 90)),
                "idle_w": idle,
                "load_w": idle + float(rng.uniform(0, 100)),
                "annual_failure_rate": float(rng.uniform(0, 0.1)),
            }
        )
    items = []
    for _ in range(int(rng.integers(1, 4))):
        kind = str(rng.choice(["fixed", "storage", "egress"]))
        if kind == "fixed":
            items.append({"type": "fixed", "name": f"f{len(items)}", "eur_per_month": float(rng.uniform(1, 80))})
        elif kind == "storage":
            items.append({"type": "storage", "name": f"s{len(items)}", "tb": float(rng.uniform(0, 30)),
                          "tb_growth_per_year": float(rng.uniform(0, 5)), "eur_per_tb_month": float(rng.uniform(1, 25))})  # fmt: skip
        else:
            items.append({"type": "egress", "name": f"e{len(items)}", "tb_per_month": float(rng.uniform(0, 3)),
                          "eur_per_tb": float(rng.uniform(1, 90))})  # fmt: skip
    return config.parse(
        {
            "name": "random",
            "start": f"{int(rng.integers(2024, 2031))}-{int(rng.integers(1, 13)):02d}",
            "horizon_months": int(rng.integers(1, 130)),
            "electricity": {
                "eur_per_kwh": [float(x) for x in rng.uniform(0.1, 0.5, 24)],
                "yearly_increase": float(rng.uniform(-0.05, 0.1)),
                "overhead_factor": float(rng.uniform(1, 1.4)),
            },
            "load": {"utilisation": [float(x) for x in rng.uniform(0, 1, 24)]},
            "hardware": hw,
            "recurring": [{"name": "r", "eur_per_month": float(rng.uniform(0, 20))}],
            "admin": {"hours_per_month": float(rng.uniform(0, 5)), "hourly_value_eur": float(rng.uniform(0, 30))},
            "cloud": {
                "yearly_increase": float(rng.uniform(-0.05, 0.1)),
                "scenarios": [{"name": "c1", "items": items}, {"name": "c2", "items": items[:1]}],
            },
        }
    )


def test_example_agrees_with_the_literal_simulation(example: config.Scenario) -> None:
    checks = verify.verify(example, DRAWS, SEED)
    assert len(checks) == DRAWS + 1
    assert all(c.ok for c in checks), [c for c in checks if not c.ok]
    assert max(c.max_rel_error for c in checks) < 1e-12


@pytest.mark.parametrize("seed", range(8))
def test_random_scenarios_agree(seed: int) -> None:
    rng = np.random.default_rng(SEED * 1000 + seed)
    sc = random_scenario(rng)
    v = {g: float(rng.uniform(0.6, 1.5)) for g in config.GROUPS}
    err, _ = verify.compare(sc, v)
    assert err < 1e-12


def test_verify_notices_a_wrong_model(example: config.Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    real = model.simulate

    def wrong(sc: config.Scenario, v: model.Variants | None = None) -> model.Costs:
        c = real(sc, v)
        return model.Costs(c.hardware, c.energy * 1.001, c.failures, c.recurring, c.time, c.residual, c.cloud)

    monkeypatch.setattr(model, "simulate", wrong)
    checks = verify.verify(example, 3, 1)
    assert not any(c.ok for c in checks) and "energy" in checks[0].detail


def test_verify_notices_a_wrong_breakeven(example: config.Scenario, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model, "breakeven", lambda home, cloud: np.full(home.shape[0], 7, dtype=np.int64))
    checks = verify.verify(example, 1, 1)
    assert not checks[0].ok and "break-even" in checks[0].detail


def test_reference_breakeven_and_its_residual(example: config.Scenario) -> None:
    ref = reference.run(example)
    assert ref.residual == pytest.approx(model.simulate(example).residual[0])
    assert reference.breakeven([100.0, 1.0], [10.0, 10.0]) == 0 and reference.breakeven([1.0], [2.0]) == 1
