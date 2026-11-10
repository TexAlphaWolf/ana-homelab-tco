from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from homelabtco import cli, model


def run(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str, str]:
    code = cli.main(list(args))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_example_prints_and_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "example")
    assert code == 0 and out.startswith("# An example scenario")
    f = tmp_path / "mine.yaml"
    code, out, _ = run(capsys, "example", "-o", str(f))
    assert code == 0 and f.read_text(encoding="utf-8").startswith("# An example scenario")
    code, _, err = run(capsys, "example", "-o", str(f))
    assert code == 2 and "already exists" in err
    code, out, _ = run(capsys, "validate", str(f))  # the written example is a valid scenario
    assert code == 0 and out.startswith("ok: Home server")


def test_validate_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "bad.yaml"
    f.write_text(
        "name: x\nhorizon_months: 0\nelectricity: {eur_per_kwh: 0.2}\nhardware: []\ncloud: {scenarios: []}\n",
        encoding="utf-8",
    )
    code, _, err = run(capsys, "validate", str(f))
    assert code == 2 and err.startswith("error: hardware")
    code, _, err = run(capsys, "validate", str(tmp_path / "nothing.yaml"))
    assert code == 2 and "cannot read" in err


def test_run_prints_the_summary_and_writes_the_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "run", "--samples", "500", "--out", str(tmp_path))
    assert code == 0
    assert "home server: cash €4,258, residual value €236, net €4,021 (€67 a month)" in out
    assert "break-even month 21 (2027-09)" in out and "no break-even" in out
    rep = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert rep["kind"] == "report" and rep["montecarlo"]["samples"] == 500
    assert (tmp_path / "summary.png").read_bytes()[1:4] == b"PNG"
    again = tmp_path / "again.md"
    code, _, _ = run(
        capsys, "render", str(tmp_path / "report.json"), "-o", str(again), "--figure", str(tmp_path / "f.png")
    )
    assert code == 0 and again.read_text(encoding="utf-8") == (tmp_path / "report.md").read_text(encoding="utf-8")
    code, out, _ = run(capsys, "render", str(tmp_path / "report.json"))
    assert code == 0 and out.startswith("# Total cost of ownership")


def test_verify_exit_codes(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    code, out, _ = run(capsys, "verify", "--draws", "3")
    assert code == 0 and "4 of 4 comparisons agree" in out
    monkeypatch.setattr(model, "breakeven", lambda home, cloud: np.full(home.shape[0], 9, dtype=np.int64))
    code, out, _ = run(capsys, "verify", "--draws", "1")
    assert code == 1 and "FAIL scenario as written" in out and "0 of 2" in out


def test_bench_and_render(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = run(capsys, "bench", "--sizes", "100,200", "--repeat", "1", "--draws", "3", "--out", str(tmp_path))
    assert code == 0 and "written:" in out and "horizon of 480 months" in out
    data = json.loads((tmp_path / "bench.json").read_text(encoding="utf-8"))
    assert data["kind"] == "bench" and data["verification"]["ok"] and data["verification"]["checks"] == 4
    assert [r["samples"] for r in data["montecarlo"]] == [100, 200]
    again = tmp_path / "again.md"
    code, _, _ = run(
        capsys, "render", str(tmp_path / "bench.json"), "-o", str(again), "--figure", str(tmp_path / "f.png")
    )
    assert code == 0 and again.read_text(encoding="utf-8") == (tmp_path / "bench.md").read_text(encoding="utf-8")
    assert (tmp_path / "f.png").read_bytes()[1:4] == b"PNG"


def test_bench_reports_a_mismatch_with_exit_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(model, "breakeven", lambda home, cloud: np.full(home.shape[0], 9, dtype=np.int64))
    code, _, _ = run(capsys, "bench", "--sizes", "50", "--repeat", "1", "--draws", "1", "--out", str(tmp_path))
    assert code == 1


@pytest.mark.parametrize(
    "args",
    [
        ["bench", "--sizes", "0"],
        ["bench", "--sizes", ""],
        ["render", "/nonexistent.json"],
        ["run", "--swing", "2"],
        ["run", "--samples", "0"],
    ],
)
def test_errors_are_exit_code_2(args: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = run(capsys, *args)
    assert code == 2 and err.startswith("error:")


def test_render_refuses_other_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    f = tmp_path / "x.json"
    f.write_text("[1, 2]", encoding="utf-8")
    code, _, err = run(capsys, "render", str(f))
    assert code == 2 and "neither" in err
    f.write_text("not json", encoding="utf-8")
    code, _, _ = run(capsys, "render", str(f))
    assert code == 2


def test_no_command_is_a_usage_error() -> None:
    with pytest.raises(SystemExit) as e:
        cli.main([])
    assert e.value.code == 2
