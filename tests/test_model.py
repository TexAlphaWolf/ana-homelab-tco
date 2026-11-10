from __future__ import annotations

import calendar

import numpy as np
import pytest

from homelabtco import model

from .conftest import raw, simple


def test_calendar_uses_real_days() -> None:
    sc = simple(start="2027-12", horizon_months=3)
    assert model.days_in_months(sc).tolist() == [31, 31, 29]  # February 2028 is a leap month
    assert model.month_labels(sc) == ["2027-12", "2028-01", "2028-02"]
    assert model.days_in_months(simple(start="2028-02", horizon_months=1)).tolist() == [29]


def test_hardware_is_bought_up_front_and_again_when_worn_out() -> None:
    sc = simple(horizon_months=80)  # life 36 months: months 0, 36 and 72
    hw = model.simulate(sc).hardware[0]
    assert np.flatnonzero(hw).tolist() == [0, 36, 72] and hw[0] == 1200


def test_residual_value_is_what_is_left_of_the_life() -> None:
    sc = simple(horizon_months=40)  # bought at 0 and 36: 4 of 36 months used
    assert model.simulate(sc).residual[0] == pytest.approx(1200 * (1 - 4 / 36))
    sc = simple(horizon_months=36)  # exactly worn out, nothing left
    assert model.simulate(sc).residual[0] == pytest.approx(0.0)
    sc = simple(horizon_months=12)
    assert model.simulate(sc).residual[0] == pytest.approx(1200 * (1 - 12 / 36))


def test_energy_by_hand() -> None:
    sc = simple(start="2027-02", horizon_months=2)  # 28 and 31 days
    watts = 20 + (60 - 20) * 0.5
    per_day = watts * 24 / 1000 * 0.25
    e = model.simulate(sc).energy[0]
    assert e.tolist() == pytest.approx([per_day * 28, per_day * 31])


def test_overhead_and_yearly_increase() -> None:
    d = raw(horizon_months=14, start="2027-01")
    d["electricity"] = {"eur_per_kwh": 0.25, "overhead_factor": 1.2, "yearly_increase": 0.1}
    sc = simple(**{k: d[k] for k in ("horizon_months", "electricity")})
    e = model.simulate(sc).energy[0]
    assert e[12] / e[0] == pytest.approx(1.1 * 31 / 31) and e[0] == pytest.approx(40 * 1.2 * 24 / 1000 * 0.25 * 31)


def test_time_of_use_tariff_and_utilisation_profile() -> None:
    d = raw()
    d["electricity"] = {"eur_per_kwh": [0.1] * 12 + [0.3] * 12}
    d["load"] = {"utilisation": [0.0] * 12 + [1.0] * 12}
    sc = simple(electricity=d["electricity"], load=d["load"], horizon_months=1, start="2027-01")
    want = 31 * (12 * 20 * 0.1 + 12 * 60 * 0.3) / 1000
    assert model.simulate(sc).energy[0, 0] == pytest.approx(want)


def test_failures_recurring_and_time() -> None:
    d = raw()
    d["hardware"][0]["annual_failure_rate"] = 0.05
    sc = simple(hardware=d["hardware"], admin={"hours_per_month": 4, "hourly_value_eur": 25})
    c = model.simulate(sc)
    assert c.failures[0, 0] == pytest.approx(1200 * 0.05 / 12)
    assert c.recurring[0, 0] == 3 and c.time[0, 0] == 100


def test_cloud_bill_has_fixed_storage_and_egress_with_growth_and_price_rise() -> None:
    d = raw(horizon_months=13)
    d["cloud"] = {
        "yearly_increase": 0.10,
        "scenarios": [
            {
                "name": "S",
                "items": [
                    {"type": "fixed", "name": "vm", "eur_per_month": 10},
                    {"type": "storage", "name": "s", "tb": 10, "tb_growth_per_year": 12, "eur_per_tb_month": 2},
                    {"type": "egress", "name": "e", "tb_per_month": 1, "eur_per_tb": 5},
                ],
            }
        ],
    }
    bill = model.simulate(simple(cloud=d["cloud"], horizon_months=13)).cloud["S"][0]
    assert bill[0] == pytest.approx(10 + 10 * 2 + 5)
    assert bill[6] == pytest.approx(10 + (10 + 6) * 2 + 5)
    assert bill[12] == pytest.approx((10 + (10 + 12) * 2 + 5) * 1.1)


def test_factors_scale_their_group() -> None:
    sc = simple()
    base = model.simulate(sc)
    twice = model.simulate(sc, model.Variants.one(cloud_price=2.0, energy_price=2.0, hardware_price=2.0, recurring=2.0))
    assert twice.cloud["VM"][0].tolist() == pytest.approx((2 * base.cloud["VM"][0]).tolist())
    assert twice.energy[0].tolist() == pytest.approx((2 * base.energy[0]).tolist())
    assert twice.hardware[0, 0] == 2400 and twice.recurring[0, 0] == 6
    longer = model.simulate(sc, model.Variants.one(hardware_life=2.0))
    assert np.flatnonzero(longer.hardware[0]).tolist() == [0]  # life 72 months: no replacement within 24
    load = model.simulate(sc, model.Variants.one(utilisation=2.0))  # 0.5 -> 1.0, clipped there
    assert load.energy[0, 0] == pytest.approx(60 * 24 / 1000 * 0.25 * 31)
    assert model.simulate(sc, model.Variants.one(power=2.0)).energy[0, 0] == pytest.approx(2 * base.energy[0, 0])


def test_variants_are_validated_and_sliced() -> None:
    with pytest.raises(KeyError):
        model.Variants.one(colour=2.0)
    v = model.Variants.base(10)
    assert v.n == 10 and v.slice(2, 5).n == 3


def test_breakeven() -> None:
    home = np.array([[100.0, 1, 1, 1, 1, 1]])
    cloud = np.array([[10.0, 10, 10, 10, 10, 10]])
    assert model.breakeven(home, cloud).tolist() == [0]  # 105 spent against 60: never
    cloud = np.array([[30.0, 30, 30, 30, 30, 30]])
    assert model.breakeven(home, cloud).tolist() == [4]  # 103 <= 120 at the 4th month
    assert model.breakeven(np.array([[5.0, 5, 5]]), np.array([[10.0, 10, 10]])).tolist() == [1]


def test_breakeven_with_many_variants_at_once() -> None:
    home = np.array([[100.0, 1, 1, 1], [100.0, 1, 1, 1]])
    cloud = np.array([[30.0] * 4, [10.0] * 4])
    assert model.breakeven(home, cloud).tolist() == [4, 0]


def test_the_month_arrays_have_the_right_shape() -> None:
    sc = simple(horizon_months=7)
    c = model.simulate(sc, model.Variants.base(3))
    assert c.homelab_monthly().shape == (3, 7) and c.residual.shape == (3,) and c.cloud["VM"].shape == (3, 7)
    assert c.homelab_net().shape == (3,)
    assert sum(calendar.monthrange(2027, m)[1] for m in range(1, 8)) == model.days_in_months(sc).sum()
