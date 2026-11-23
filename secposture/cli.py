"""Command-line runner: python -m secposture.cli [scenario.json] --out results/"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure  # noqa: E402

from .engine import run_all  # noqa: E402
from .reporting import (export_csv, export_excel, plot_attribution, plot_cnpv,  # noqa: E402
                        plot_mc, plot_tornado)
from .scenarios import example_scenario, load_json  # noqa: E402
from .uncertainty import monte_carlo, tornado  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Compare lifecycle costs of security postures.")
    p.add_argument("scenario", nargs="?", help="scenario JSON (default: built-in example)")
    p.add_argument("--out", default="results", help="output folder")
    p.add_argument("--mc", type=int, default=500, help="Monte Carlo samples (0 to skip)")
    a = p.parse_args()

    scn = load_json(a.scenario) if a.scenario else example_scenario()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = run_all(scn)

    print(f"{'Case':32s} {'NPV':>14s} {'CAPEX':>14s} {'Labor':>14s}")
    for r in results:
        print(f"{r.case:32s} {r.npv:14,.0f} {r.capex_npv:14,.0f} {r.labor_npv:14,.0f}")

    def save(fn, name, *args):
        fig = Figure(figsize=(9, 5), dpi=120)
        fn(fig, *args)
        fig.savefig(out / name)

    save(plot_cnpv, "cnpv.png", results)
    save(plot_attribution, "attribution.png", results)
    save(plot_tornado, "tornado.png", tornado(scn, scn.cases[0]), scn.cases[0].name)
    if a.mc:
        mcs = [monte_carlo(scn, c, n=a.mc) for c in scn.cases]
        save(plot_mc, "monte_carlo.png", mcs)
        for m in mcs:
            lo, mid, hi = (sorted(m.npv_samples)[int(q * (len(m.npv_samples) - 1))] for q in (0.1, 0.5, 0.9))
            print(f"MC {m.case:29s} P10 {lo:14,.0f}  P50 {mid:14,.0f}  P90 {hi:14,.0f}")
    export_excel(scn, results, out / "results.xlsx")
    export_csv(results, out / "cnpv.csv")
    print(f"Saved charts and results to {out.resolve()}")


if __name__ == "__main__":
    main()
