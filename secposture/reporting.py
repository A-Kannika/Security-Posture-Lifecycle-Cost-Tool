"""Charts and Excel/CSV export (shared by the GUI and the command line)."""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from openpyxl.styles import Font

from .engine import CaseResult, Scenario
from .uncertainty import MCResult

COLORS = ["#2563eb", "#d97706", "#059669", "#db2777", "#7c3aed",
          "#0891b2", "#65a30d", "#dc2626", "#4b5563", "#a16207"]
_money = FuncFormatter(lambda v, _: f"${v/1e6:,.0f}M")


def plot_cnpv(fig: Figure, results: list[CaseResult]) -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    for i, r in enumerate(results):
        ax.plot(r.years, r.cnpv, lw=2.2, color=COLORS[i % 10], label=r.case)
    ax.axhline(0, color="#999", lw=0.8)
    ax.yaxis.set_major_formatter(_money)
    ax.set(title="Cumulative NPV by case (higher = cheaper)", xlabel="Project year", ylabel="CNPV")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()


def plot_attribution(fig: Figure, results: list[CaseResult]) -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    names = [r.case for r in results]
    bottom = np.zeros(len(results))
    for k, col in zip(("detection", "delay", "response"), ("#2563eb", "#d97706", "#059669")):
        vals = np.array([-r.attribution[k] for r in results])
        ax.barh(names, vals, left=bottom, color=col, label=k.capitalize())
        bottom += vals
    ax.xaxis.set_major_formatter(_money)
    ax.set(title="Lifecycle cost (NPV) by security function")
    ax.invert_yaxis()
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.14))
    fig.tight_layout()


def plot_mc(fig: Figure, mcs: list[MCResult]) -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    for i, m in enumerate(mcs):
        c = COLORS[i % 10]
        ax.fill_between(m.years, m.band(10), m.band(90), color=c, alpha=0.18)
        ax.plot(m.years, m.band(50), color=c, lw=2.2, label=f"{m.case} (P50, P10–P90 band)")
    ax.yaxis.set_major_formatter(_money)
    ax.set(title="Cumulative NPV under uncertainty", xlabel="Project year", ylabel="CNPV")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()


def plot_tornado(fig: Figure, rows: list[tuple[str, float, float]], case: str) -> None:
    fig.clear()
    ax = fig.add_subplot(111)
    labels = [r[0] for r in rows][::-1]
    lo = np.array([r[1] for r in rows][::-1])
    hi = np.array([r[2] for r in rows][::-1])
    ax.barh(labels, lo, color="#2563eb", label="Input −20%")
    ax.barh(labels, hi, color="#d97706", label="Input +20%")
    ax.axvline(0, color="#333", lw=0.8)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: "$0" if abs(v) < 1 else f"${v/1e6:+,.1f}M"))
    ax.set(title=f"NPV sensitivity — {case}", xlabel="Change in NPV (right = cheaper)")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()


def export_excel(scn: Scenario, results: list[CaseResult], path: str | Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Case", "NPV", "CAPEX NPV", "Labor NPV", "Detection", "Delay", "Response"])
    for r in results:
        ws.append([r.case, r.npv, r.capex_npv, r.labor_npv,
                   r.attribution["detection"], r.attribution["delay"], r.attribution["response"]])
    for row in ws.iter_rows(min_row=2, min_col=2):
        for cell in row:
            cell.number_format = '"$"#,##0'
    for c in ws[1]:
        c.font = Font(bold=True)
    ws.column_dimensions["A"].width = 30

    cn = wb.create_sheet("CNPV")
    cn.append(["Year"] + [r.case for r in results])
    for y in results[0].years:
        cn.append([int(y)] + [float(r.cnpv[y]) for r in results])
    chart = LineChart()
    chart.title, chart.y_axis.title, chart.x_axis.title = "Cumulative NPV by case", "CNPV ($)", "Year"
    chart.add_data(Reference(cn, min_col=2, max_col=1 + len(results), min_row=1, max_row=cn.max_row),
                   titles_from_data=True)
    chart.set_categories(Reference(cn, min_col=1, min_row=2, max_row=cn.max_row))
    cn.add_chart(chart, "H2")

    names = {it.id: it.name for it in scn.items}
    for r in results:
        ts = wb.create_sheet(r.case[:28])
        ts.append(["ID", "Line item"] + [f"Y{y}" for y in r.years] + ["NPV"])
        for i, iid in enumerate(r.item_ids):
            ts.append([iid, names[iid]] + [float(v) for v in r.costs[i]] + [-float(r.discounted[i].sum())])
    wb.save(path)


def export_csv(results: list[CaseResult], path: str | Path) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["year"] + [r.case for r in results])
        for y in results[0].years:
            w.writerow([int(y)] + [round(float(r.cnpv[y]), 2) for r in results])
