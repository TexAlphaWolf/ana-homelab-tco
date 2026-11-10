"""The documentation must say what the measurements say."""

from __future__ import annotations

import json
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from homelabtco import analysis, cli, model, report
from homelabtco.report import eur, pct

ROOT = Path(__file__).resolve().parent.parent
REPORT = json.loads((ROOT / "docs" / "report.json").read_text(encoding="utf-8"))
BENCH = json.loads((ROOT / "docs" / "bench.json").read_text(encoding="utf-8"))
README = (ROOT / "README.md").read_text(encoding="utf-8")
ANALYSIS = (ROOT / "docs" / "analysis.md").read_text(encoding="utf-8")
S, H = REPORT["scenario"], REPORT["homelab"]
CLOUD = {c["name"]: c for c in REPORT["cloud"]}
MC = {m["name"]: m for m in REPORT["montecarlo"]["scenarios"]}
N1, N2, N3 = CLOUD
TOR = {n: {b["group"]: b for b in bars} for n, bars in REPORT["sensitivity"]["scenarios"].items()}
MCB = {r["samples"]: r["seconds"] for r in BENCH["montecarlo"]}
HZ = {r["months"]: r["seconds"] for r in BENCH["horizon"]}


def spread(n: str, g: str) -> float:
    return abs(TOR[n][g]["high_eur"] - TOR[n][g]["low_eur"])


def assert_close(a: Any, b: Any) -> None:
    """Equal structure; numbers equal to 12 digits (the file keeps full precision)."""
    if isinstance(b, dict):
        assert a.keys() == b.keys()
        for k in b:
            assert_close(a[k], b[k])
    elif isinstance(b, list):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            assert_close(x, y)
    elif isinstance(b, float):
        assert a == pytest.approx(b, rel=1e-12)
    else:
        assert a == b


def test_the_benchmark_is_what_the_text_says_it_is() -> None:
    env = BENCH["environment"]
    assert env["homelabtco"] == "1.0.0" and env["seed"] == 1 and env["repeat"] == 5 and env["cpus"] == 12
    assert env["python"] == "3.14.10" and env["numpy"] == "2.5.4" and env["horizon_months"] == 60
    assert sorted(MCB) == [1_000, 10_000, 100_000, 1_000_000] and sorted(HZ) == [60, 120, 240, 480]
    assert BENCH["verification"]["ok"] is True and BENCH["verification"]["checks"] == 51


def test_markdown_is_the_render_of_the_json(tmp_path: Path) -> None:
    for name in ("report", "bench"):
        out = tmp_path / f"{name}.md"
        assert cli.main(["render", str(ROOT / "docs" / f"{name}.json"), "-o", str(out)]) == 0
        assert out.read_text(encoding="utf-8") == (ROOT / "docs" / f"{name}.md").read_text(encoding="utf-8")


def test_figures_exist() -> None:
    for name in ("report.png", "bench.png"):
        assert (ROOT / "docs" / name).stat().st_size > 10_000


@pytest.mark.parametrize("text", [README, ANALYSIS], ids=["README", "analysis"])
def test_no_scaffold_left(text: str) -> None:
    assert not re.search(r"work in progress|TODO|TBD|lorem|measurements pending|provisional|scaffold", text, re.I)


@pytest.mark.parametrize("name", ["README.md", "docs/analysis.md"])
def test_local_links_resolve(name: str) -> None:
    path = ROOT / name
    for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://")):
            continue
        assert (path.parent / target).exists(), f"{name}: broken link {target}"


def test_report_is_what_the_example_gives_now(example: Any) -> None:
    """The committed report is the example's: the deterministic numbers exactly, Monte Carlo within sampling noise."""
    fresh = analysis.build_report(
        example, REPORT["montecarlo"]["samples"], REPORT["montecarlo"]["seed"], REPORT["sensitivity"]["swing"]
    )
    for key in ("homelab", "cloud", "sensitivity"):
        assert_close(fresh[key], REPORT[key])
    for a, b in zip(fresh["montecarlo"]["scenarios"], REPORT["montecarlo"]["scenarios"], strict=True):
        assert a["p_home_cheaper"] == pytest.approx(b["p_home_cheaper"], abs=0.01)
        assert a["median_eur"] == pytest.approx(b["median_eur"], rel=0.02)


def test_readme_headline_numbers() -> None:
    c = H["components_eur"]
    assert f"costs {eur(H['cash_eur'])} in cash over 60 months" in README
    assert f"{eur(c['hardware'])} of hardware, {eur(c['energy'])} of" in README
    assert f"{eur(c['failures'])} of expected spares and {eur(c['recurring'])} of recurring" in README
    assert (
        f"it is {eur(H['net_eur'])}, {eur(H['monthly_net_avg_eur'])} a month, at an average draw of {S['average_watts']:.0f} W"
        in README
    )
    assert f"it saves {eur(CLOUD[N1]['advantage_eur'])}** and breaks even" in README
    assert f"in month {CLOUD[N1]['breakeven_month']} ({CLOUD[N1]['breakeven_label']})" in README
    assert f"cheaper in {pct(MC[N1]['p_home_cheaper'])} of" in README
    assert f"{eur(MC[N1]['p5_eur'])} to {eur(MC[N1]['p95_eur'])}" in README
    assert f"the home server costs {eur(-CLOUD[N2]['advantage_eur'])} more" in README
    assert f"wins in {round(MC[N2]['p_home_cheaper'] * 20_000)} of 20,000 variants" in README
    assert (
        f"it saves {eur(CLOUD[N3]['advantage_eur'])}**, with break-even in month {CLOUD[N3]['breakeven_month']}"
        in README
    )
    assert CLOUD[N2]["breakeven_month"] == 0
    for g, label in (
        ("cloud_price", "cloud prices"),
        ("storage_size", "storage needed"),
        ("hardware_price", "hardware prices"),
        ("energy_price", "electricity price"),
    ):
        assert eur(spread(N1, g)) in README, label
    big = MCB[1_000_000]
    assert f"take {big:.2f} s ({1_000_000 / big:,.0f} variants a second)" in README
    assert f"{BENCH['reference_s'] * 1_000_000 / big:,.0f} times faster" in README
    assert f"{BENCH['verification']['max_rel_error']:.2e} on 51 comparisons" in README


def test_the_cost_of_your_time_claim_is_true(example: Any) -> None:
    """Valued below the stated break-even the home server still wins against the cheap storage; above it, it does not."""
    per_hour = CLOUD[N1]["advantage_eur"] / (example.admin_hours_per_month * example.horizon_months)
    assert f"worth more than\n   {eur(per_hour)} an hour" in README or f"{eur(per_hour)} an hour" in README
    for value, wins in ((per_hour - 1, True), (per_hour + 1, False)):
        sc = replace(example, hourly_value_eur=value)
        adv = model.simulate(sc)
        assert bool(adv.cloud[N1].sum() - adv.homelab_net()[0] > 0) is wins


def test_analysis_tables_match_the_json() -> None:
    c = H["components_eur"]
    for item in ("hardware", "energy", "failures", "recurring"):
        assert eur(c[item]) in ANALYSIS
    assert (
        f"| **Cash spent** | **{eur(H['cash_eur'])}** |" in ANALYSIS
        and f"| **Net cost** | **{eur(H['net_eur'])}** |" in ANALYSIS
    )
    assert (
        f"{pct(c['hardware'] / H['cash_eur'])} of the cash" in ANALYSIS
        and f"electricity {pct(c['energy'] / H['cash_eur'])}" in ANALYSIS
    )
    for x in REPORT["cloud"]:
        be = (
            f"month {x['breakeven_month']} ({x['breakeven_label']})" if x["breakeven_month"] else "not within 60 months"
        )
        row = f"| {x['name']} | {eur(x['total_eur'])} | {eur(x['monthly_avg_eur'])} | {eur(x['advantage_eur'])} | {eur(x['advantage_cash_eur'])} | {be} |"
        assert row in ANALYSIS
    for g in TOR[N1]:
        row = f"| {TOR[N1][g]['label']} | {eur(spread(N1, g))} | {eur(spread(N2, g))} | {eur(spread(N3, g))} |"
        assert row in ANALYSIS, g
    for m in REPORT["montecarlo"]["scenarios"]:
        row = f"| {m['name']} | {pct(m['p_home_cheaper'])} | {eur(m['p5_eur'])} | {eur(m['median_eur'])} | {eur(m['p95_eur'])} |"
        assert row in ANALYSIS
    for r in BENCH["montecarlo"]:
        row = f"| {r['samples']:,} | {r['seconds'] * 1000:,.1f} ms | {r['samples'] / r['seconds']:,.0f} | {BENCH['reference_s'] * r['samples']:,.1f} s |"
        assert row in ANALYSIS


def test_analysis_derived_claims() -> None:
    big, ref, single = MCB[1_000_000], BENCH["reference_s"], BENCH["single_s"]
    assert f"Vectorising pays {ref * 1_000_000 / big:,.0f} times" in ANALYSIS
    assert f"one evaluation alone takes {single * 1e6:,.0f} µs, {single / (big / 1_000_000):.0f} times" in ANALYSIS
    assert f"480 months take {HZ[480] / HZ[60]:.1f} times as long as 60" in ANALYSIS
    assert f"largest relative difference is {BENCH['verification']['max_rel_error']:.2e}" in ANALYSIS
    home_groups = [g for g in TOR[N1] if g not in ("cloud_price", "storage_size")]
    top = max(home_groups, key=lambda g: spread(N1, g))
    assert (
        top == "hardware_price"
        and f"{100 * spread(N1, top) / spread(N1, 'cloud_price'):.0f}% of the cloud-price swing" in ANALYSIS
    )
    assert spread(N1, "energy_price") == pytest.approx(spread(N1, "power"))
    assert spread(N2, "storage_size") == 0
    assert min(x["life_months"] for x in S["hardware"]) == 60 and H["components_eur"]["hardware"] == S["capex_eur"]
    assert MC[N1]["p_home_cheaper"] == 1.0 and MC[N3]["p_home_cheaper"] == 1.0


def test_readme_output_matches_a_real_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["run", "--samples", "200"]) == 0
    got = capsys.readouterr().out.strip().splitlines()
    block = re.search(r"```text\n(.*?)```", README, re.S)
    assert block is not None
    assert got == block.group(1).strip().splitlines()
    assert report.eur(4257.5) == "€4,258"
