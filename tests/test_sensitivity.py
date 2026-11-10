from __future__ import annotations

import numpy as np
import pytest

from homelabtco import config, model, sensitivity

from .conftest import SEED


def test_advantage_is_cloud_bill_minus_net_cost(example: config.Scenario) -> None:
    c = model.simulate(example)
    adv = sensitivity.advantage(example, model.Variants.base())
    for name, bill in c.cloud.items():
        assert adv[name][0] == pytest.approx(bill.sum() - (c.homelab_cash()[0] - c.residual[0]))


def test_tornado_orders_by_spread_and_has_the_right_signs(example: config.Scenario) -> None:
    t = sensitivity.tornado(example, 0.2)
    assert set(t) == {c.name for c in example.clouds}
    for bars in t.values():
        assert [b.group for b in bars].count("storage_size") == 1 and len(bars) == len(config.GROUPS)
        assert [b.spread for b in bars] == sorted((b.spread for b in bars), reverse=True)
        by = {b.group: b for b in bars}
        assert by["cloud_price"].high > by["cloud_price"].low  # a dearer cloud favours the home server
        assert by["energy_price"].high < by["energy_price"].low
        assert by["hardware_price"].high < by["hardware_price"].low
    one = {b.group: b for b in t["Flat-rate storage box + small VPS"]}
    assert one["storage_size"].spread == 0  # that alternative has no storage item


def test_tornado_swing_is_checked(example: config.Scenario) -> None:
    for bad in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError, match="swing"):
            sensitivity.tornado(example, bad)


def test_montecarlo_is_reproducible_and_chunk_independent(example: config.Scenario) -> None:
    a = sensitivity.montecarlo(example, 3000, SEED, chunk=700)
    b = sensitivity.montecarlo(example, 3000, SEED, chunk=5000)
    c = sensitivity.montecarlo(example, 3000, SEED + 1)
    for name in a.advantage:
        assert np.array_equal(a.advantage[name], b.advantage[name]) and np.array_equal(
            a.breakeven[name], b.breakeven[name]
        )
        assert not np.array_equal(a.advantage[name], c.advantage[name])
        assert len(a.advantage[name]) == 3000


def test_draw_respects_the_spread(example: config.Scenario) -> None:
    v = sensitivity.draw(example, 20_000, 3)
    for g in config.GROUPS:
        s = example.uncertainty[g]
        assert v.factors[g].min() >= 1 - s and v.factors[g].max() <= 1 + s
        assert abs(v.factors[g].mean() - 1) < 0.02  # symmetric triangle peaking at 1


def test_zero_uncertainty_gives_the_base_case(example: config.Scenario) -> None:
    from dataclasses import replace

    sc = replace(example, uncertainty={g: 0.0 for g in config.GROUPS})
    mc = sensitivity.montecarlo(sc, 50, 1)
    base = sensitivity.advantage(sc, model.Variants.base())
    for name, adv in mc.advantage.items():
        assert np.allclose(adv, base[name][0])


def test_montecarlo_needs_samples(example: config.Scenario) -> None:
    with pytest.raises(ValueError, match="samples"):
        sensitivity.montecarlo(example, 0, 1)
