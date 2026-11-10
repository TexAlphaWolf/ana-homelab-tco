"""Command line: example, validate, run, verify, bench, render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from homelabtco import __version__, analysis, bench, config, report, verify

EXAMPLE = Path(__file__).parent / "examples" / "homelab.yaml"


def load_scenario(arg: str | None) -> config.Scenario:
    return config.load(Path(arg) if arg else EXAMPLE)


def summary_lines(rep: dict[str, Any]) -> list[str]:
    s, h = rep["scenario"], rep["homelab"]
    lines = [
        f"{s['name']}: {s['horizon_months']} months from {s['start']}",
        f"home server: cash {report.eur(h['cash_eur'])}, residual value {report.eur(h['residual_eur'])}, "
        f"net {report.eur(h['net_eur'])} ({report.eur(h['monthly_net_avg_eur'])} a month)",
    ]
    for c in rep["cloud"]:
        be = (
            f"break-even month {c['breakeven_month']} ({c['breakeven_label']})"
            if c["breakeven_month"]
            else "no break-even"
        )
        lines.append(
            f"{c['name']}: cloud {report.eur(c['total_eur'])}; home server saves {report.eur(c['advantage_eur'])}; {be}"
        )
    return lines


def cmd_example(a: argparse.Namespace) -> int:
    text = EXAMPLE.read_text(encoding="utf-8")
    if a.output:
        out = Path(a.output)
        if out.exists():
            raise config.ConfigError(f"{out} already exists")
        out.write_text(text, encoding="utf-8")
        print(f"written: {out}")
    else:
        print(text, end="")
    return 0


def cmd_validate(a: argparse.Namespace) -> int:
    sc = load_scenario(a.file)
    print(
        f"ok: {sc.name}; {len(sc.hardware)} hardware items ({report.eur(sc.capex)}), {len(sc.clouds)} cloud alternatives, {sc.horizon_months} months"
    )
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    sc = load_scenario(a.file)
    rep = analysis.build_report(sc, a.samples, a.seed, a.swing)
    for line in summary_lines(rep):
        print(line)
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "report.json").write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
        (out / "report.md").write_text(report.render_report(rep), encoding="utf-8")
        report.report_figure(rep, out / "summary.png")
        print(f"written: {out / 'report.json'}, {out / 'report.md'}, {out / 'summary.png'}")
    return 0


def cmd_verify(a: argparse.Namespace) -> int:
    sc = load_scenario(a.file)
    checks = verify.verify(sc, a.draws, a.seed)
    bad = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'ok  ' if c.ok else 'FAIL'} {c.name}: largest relative difference {c.max_rel_error:.2e} ({c.detail})")
    print(f"{len(checks) - len(bad)} of {len(checks)} comparisons agree with the literal simulation")
    return 1 if bad else 0


def cmd_bench(a: argparse.Namespace) -> int:
    sc = load_scenario(a.file)
    sizes = [int(p.replace("_", "")) for p in a.sizes.split(",") if p.strip()]
    if not sizes or any(s < 1 for s in sizes):
        raise config.ConfigError("--sizes needs at least one positive whole number")
    result = bench.run_bench(
        sc, a.file or "bundled example", sizes, a.repeat, a.seed, a.draws, a.cmdline, lambda m: print(m, flush=True)
    )
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "bench.json").write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")
    (out / "bench.md").write_text(report.render_bench(result), encoding="utf-8")
    report.bench_figure(result, out / "summary.png")
    print(f"written: {out / 'bench.json'}, {out / 'bench.md'}, {out / 'summary.png'}")
    return 0 if result["verification"]["ok"] else 1


def cmd_render(a: argparse.Namespace) -> int:
    try:
        data = json.loads(Path(a.file).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise config.ConfigError(f"cannot read {a.file}: {exc}") from exc
    kind = data.get("kind") if isinstance(data, dict) else None
    if kind not in ("report", "bench"):
        raise config.ConfigError(f"{a.file} is neither a report.json nor a bench.json")
    text = report.render_report(data) if kind == "report" else report.render_bench(data)
    if a.output:
        Path(a.output).write_text(text, encoding="utf-8")
        print(f"written: {a.output}")
    else:
        print(text, end="")
    if a.figure:
        (report.report_figure if kind == "report" else report.bench_figure)(data, Path(a.figure))
        print(f"written: {a.figure}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tco", description="Total cost of a home server against cloud alternatives.")
    p.add_argument("--version", action="version", version=f"tco {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def scenario(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("file", nargs="?", help="scenario YAML (default: the bundled example)")

    e = sub.add_parser("example", help="print (or write) the bundled example scenario")
    e.add_argument("-o", "--output")
    e.set_defaults(func=cmd_example)

    v = sub.add_parser("validate", help="check a scenario file")
    scenario(v)
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="costs, comparison with the cloud, sensitivity and Monte Carlo")
    scenario(r)
    r.add_argument("--samples", type=int, default=20_000, help="Monte Carlo variants")
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--swing", type=float, default=0.2, help="sensitivity: how far each group moves (0.2 = 20%%)")
    r.add_argument("--out", help="write report.json, report.md and summary.png here")
    r.set_defaults(func=cmd_run)

    c = sub.add_parser(
        "verify", help="compare the model with the literal day-by-day simulation; exit 1 on a difference"
    )
    scenario(c)
    c.add_argument("--draws", type=int, default=25, help="random variants besides the scenario as written")
    c.add_argument("--seed", type=int, default=1)
    c.set_defaults(func=cmd_verify)

    b = sub.add_parser("bench", help="speed of the model, and agreement with the literal simulation")
    scenario(b)
    b.add_argument("--sizes", default="1000,10000,100000,1000000")
    b.add_argument("--repeat", type=int, default=5)
    b.add_argument("--draws", type=int, default=50)
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--out", default="tco-out")
    b.set_defaults(func=cmd_bench)

    n = sub.add_parser("render", help="rebuild the Markdown (and figure) from report.json or bench.json")
    n.add_argument("file")
    n.add_argument("-o", "--output")
    n.add_argument("--figure")
    n.set_defaults(func=cmd_render)
    return p


def main(argv: list[str] | None = None) -> int:
    given = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(given)
    args.cmdline = " ".join(given)
    try:
        return int(args.func(args))
    except (config.ConfigError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
