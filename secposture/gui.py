"""PyQt6 desktop app: edit a scenario, run cases, explore uncertainty, export.

Run with:  python -m secposture.gui
"""
from __future__ import annotations

import sys

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
                             QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox,
                             QPushButton, QSpinBox, QSplitter, QTableWidget, QTableWidgetItem,
                             QTabWidget, QVBoxLayout, QWidget)

from .engine import Case, ItemAdjustment, LineItem, Scenario, run_all
from .reporting import (export_csv, export_excel, plot_attribution, plot_cnpv, plot_mc,
                        plot_tornado)
from .scenarios import example_scenario, load_json, save_json
from .uncertainty import monte_carlo, tornado

ITEM_COLS = ["ID", "Name", "Kind", "Unit cost ($)", "Units", "Lifetime (yr)",
             "Detection", "Delay", "Response"]
ADJ_FIELDS = [("units_add", "ΔUnits"), ("cost_mult", "×Cost"),
              ("maint_add", "ΔMaint"), ("lifetime_add", "ΔLife")]


class ChartPanel(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.fig = Figure(figsize=(8, 4.5), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        lay = QVBoxLayout(self)
        lay.addWidget(NavigationToolbar2QT(self.canvas, self))
        lay.addWidget(self.canvas)

    def draw(self, fn, *args) -> None:
        fn(self.fig, *args)
        self.canvas.draw_idle()


class MainWindow(QMainWindow):
    def __init__(self, scn: Scenario) -> None:
        super().__init__()
        self.setWindowTitle("Security Posture Lifecycle Cost Tool")
        self.resize(1300, 820)
        self.results = []
        self._build_menu()

        tabs = QTabWidget()
        tabs.addTab(self._build_inputs_tab(), "1 · Inputs")
        tabs.addTab(self._build_cases_tab(), "2 · Case adjustments")
        tabs.addTab(self._build_results_tab(), "3 · Results")
        tabs.addTab(self._build_uncertainty_tab(), "4 · Uncertainty")
        self.tabs = tabs
        self.setCentralWidget(tabs)
        self.load_scenario(scn)

    # ---------------- layout ----------------
    def _build_menu(self) -> None:
        m = self.menuBar().addMenu("&File")
        for text, slot, key in [("Open scenario…", self.open_json, "Ctrl+O"),
                                ("Save scenario…", self.save_json, "Ctrl+S"),
                                ("Export results to Excel…", self.export_xlsx, "Ctrl+E"),
                                ("Export CNPV to CSV…", self.export_csv, None),
                                ("Load example", lambda: self.load_scenario(example_scenario()), None)]:
            act = QAction(text, self)
            if key:
                act.setShortcut(key)
            act.triggered.connect(slot)
            m.addAction(act)

    def _build_inputs_tab(self) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        form = QFormLayout()
        self.f_wacc = self._dspin(0, 0.5, 0.005, 3)
        self.f_wrap = self._dspin(0.5, 5, 0.05, 2)
        self.f_maint = self._dspin(0, 0.5, 0.005, 3)
        self.f_buffer = self._dspin(0, 1, 0.01, 2)
        self.f_timeline = QSpinBox(); self.f_timeline.setRange(1, 100)
        self.f_inclusive = QComboBox(); self.f_inclusive.addItems(["≥ (inclusive)", "> (strict)"])
        self.f_profile = QComboBox(); self.f_profile.addItems(["flat", "escalating", "bathtub"])
        self.f_escal = self._dspin(0, 0.3, 0.005, 3)
        for label, wid in [("WACC", self.f_wacc), ("Labor wrap rate", self.f_wrap),
                           ("Maintenance rate (of CAPEX)", self.f_maint),
                           ("Replacement buffer", self.f_buffer),
                           ("Project timeline (yr)", self.f_timeline),
                           ("Buffer test", self.f_inclusive),
                           ("Maintenance profile", self.f_profile),
                           ("Escalation per year", self.f_escal)]:
            form.addRow(label, wid)
        run = QPushButton("▶  Run cases")
        run.setStyleSheet("background:#16a34a;color:white;font-weight:600;padding:8px;")
        run.clicked.connect(self.run_cases)
        form.addRow(run)
        left = QWidget(); left.setLayout(form); left.setMaximumWidth(340)

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Line items</b> — C.x.y capital, L.x.y labor. "
                               "Detection + Delay + Response must equal 1."))
        self.items_table = QTableWidget(0, len(ITEM_COLS))
        self.items_table.setHorizontalHeaderLabels(ITEM_COLS)
        self.items_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        right.addWidget(self.items_table)
        btns = QHBoxLayout()
        for text, slot in [("+ Capital item", lambda: self._add_item_row("capex")),
                           ("+ Labor item", lambda: self._add_item_row("labor")),
                           ("− Remove selected", self._remove_item_row)]:
            b = QPushButton(text); b.clicked.connect(slot); btns.addWidget(b)
        btns.addStretch()
        right.addLayout(btns)
        rw = QWidget(); rw.setLayout(right)
        lay.addWidget(left); lay.addWidget(rw, 1)
        return w

    def _build_cases_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(QLabel("Number of cases:"))
        self.n_cases = QSpinBox(); self.n_cases.setRange(1, 10)
        self.n_cases.valueChanged.connect(self._resize_cases)
        top.addWidget(self.n_cases); top.addStretch()
        lay.addLayout(top)
        lay.addWidget(QLabel("Per-case adjustments: ΔUnits and ΔLife are added, ×Cost multiplies, "
                             "ΔMaint is added to the maintenance rate. Row 0 holds case names and "
                             "WACC overrides (blank = baseline)."))
        self.adj_table = QTableWidget()
        lay.addWidget(self.adj_table)
        return w

    def _build_results_tab(self) -> QWidget:
        split = QSplitter(Qt.Orientation.Vertical)
        charts = QSplitter(Qt.Orientation.Horizontal)
        self.cnpv_chart, self.attr_chart = ChartPanel(), ChartPanel()
        charts.addWidget(self.cnpv_chart); charts.addWidget(self.attr_chart)
        self.summary = QTableWidget(0, 7)
        self.summary.setHorizontalHeaderLabels(["Case", "NPV", "CAPEX NPV", "Labor NPV",
                                                "Detection", "Delay", "Response"])
        self.summary.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        split.addWidget(charts); split.addWidget(self.summary)
        split.setSizes([560, 180])
        return split

    def _build_uncertainty_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        top = QHBoxLayout()
        top.addWidget(QLabel("Samples:"))
        self.mc_n = QSpinBox(); self.mc_n.setRange(50, 5000); self.mc_n.setValue(500)
        top.addWidget(self.mc_n)
        top.addWidget(QLabel("Tornado case:"))
        self.tornado_case = QComboBox(); top.addWidget(self.tornado_case)
        b = QPushButton("Run uncertainty analysis"); b.clicked.connect(self.run_uncertainty)
        top.addWidget(b); top.addStretch()
        lay.addLayout(top)
        split = QSplitter(Qt.Orientation.Horizontal)
        self.mc_chart, self.tornado_chart = ChartPanel(), ChartPanel()
        split.addWidget(self.mc_chart); split.addWidget(self.tornado_chart)
        lay.addWidget(split, 1)
        return w

    @staticmethod
    def _dspin(lo, hi, step, dec) -> QDoubleSpinBox:
        s = QDoubleSpinBox(); s.setRange(lo, hi); s.setSingleStep(step); s.setDecimals(dec)
        return s

    # ---------------- scenario <-> widgets ----------------
    def load_scenario(self, scn: Scenario) -> None:
        f = scn.financials
        self.f_wacc.setValue(f.wacc); self.f_wrap.setValue(f.wrap_rate)
        self.f_maint.setValue(f.maintenance_rate); self.f_buffer.setValue(f.replacement_buffer)
        self.f_timeline.setValue(f.timeline)
        self.f_inclusive.setCurrentIndex(0 if f.buffer_inclusive else 1)
        self.f_profile.setCurrentText(f.maint_profile); self.f_escal.setValue(f.maint_escalation)
        self.items_table.setRowCount(0)
        for it in scn.items:
            self._add_item_row(it.kind, it)
        self._cases = scn.cases
        self.n_cases.blockSignals(True); self.n_cases.setValue(len(scn.cases)); self.n_cases.blockSignals(False)
        self._fill_adj_table(scn.cases)
        self.run_cases()

    def _add_item_row(self, kind: str, it: LineItem | None = None) -> None:
        t = self.items_table
        r = t.rowCount(); t.insertRow(r)
        if it is None:
            prefix = "C" if kind == "capex" else "L"
            it = LineItem(f"{prefix}.9.{r + 1}", "New item", kind, 0, 0, 10 if kind == "capex" else 0)
        vals = [it.id, it.name, it.kind, it.unit_cost, it.units, it.lifetime,
                round(it.detection, 3), round(it.delay, 3), round(it.response, 3)]
        for c, v in enumerate(vals):
            cell = QTableWidgetItem(str(v))
            if c == 2:
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t.setItem(r, c, cell)
        if hasattr(self, "_cases"):
            self._fill_adj_table(self._read_cases(silent=True) or self._cases)

    def _remove_item_row(self) -> None:
        rows = sorted({i.row() for i in self.items_table.selectedIndexes()}, reverse=True)
        for r in rows:
            self.items_table.removeRow(r)
        self._fill_adj_table(self._read_cases(silent=True) or self._cases)

    def _item_ids(self) -> list[str]:
        return [self.items_table.item(r, 0).text() for r in range(self.items_table.rowCount())]

    def _fill_adj_table(self, cases: list[Case]) -> None:
        ids = self._item_ids()
        t = self.adj_table
        t.clear()
        t.setRowCount(len(ids) + 1)
        t.setColumnCount(len(cases) * len(ADJ_FIELDS))
        t.setHorizontalHeaderLabels([f"C{ci + 1} {lab}" for ci in range(len(cases)) for _, lab in ADJ_FIELDS])
        t.setVerticalHeaderLabels(["Case name / WACC"] + ids)
        for ci, case in enumerate(cases):
            base = ci * len(ADJ_FIELDS)
            t.setItem(0, base, QTableWidgetItem(case.name))
            w = case.financial_overrides.get("wacc")
            t.setItem(0, base + 1, QTableWidgetItem("" if w is None else str(w)))
            for ri, iid in enumerate(ids, start=1):
                a = case.adj(iid)
                for k, (fld, _) in enumerate(ADJ_FIELDS):
                    t.setItem(ri, base + k, QTableWidgetItem(str(getattr(a, fld))))
        t.resizeColumnsToContents()

    def _resize_cases(self, n: int) -> None:
        cases = self._read_cases(silent=True) or self._cases
        while len(cases) < n:
            cases.append(Case(f"Case {len(cases) + 1}"))
        self._cases = cases[:n]
        self._fill_adj_table(self._cases)

    def _read_cases(self, silent=False) -> list[Case] | None:
        t = self.adj_table
        try:
            cases = []
            for ci in range(t.columnCount() // len(ADJ_FIELDS)):
                base = ci * len(ADJ_FIELDS)
                name = (t.item(0, base).text() if t.item(0, base) else "") or f"Case {ci + 1}"
                w = t.item(0, base + 1).text().strip() if t.item(0, base + 1) else ""
                adjs = {}
                for ri, iid in enumerate(self._item_ids(), start=1):
                    v = [t.item(ri, base + k).text() if t.item(ri, base + k) else d
                         for k, d in enumerate(["0", "1", "0", "0"])]
                    a = ItemAdjustment(float(v[0]), float(v[1]), float(v[2]), int(float(v[3])))
                    if a != ItemAdjustment():
                        adjs[iid] = a
                cases.append(Case(name, {"wacc": float(w)} if w else {}, adjs))
            return cases
        except (ValueError, AttributeError) as e:
            if not silent:
                QMessageBox.warning(self, "Invalid adjustment", str(e))
            return None

    def current_scenario(self) -> Scenario | None:
        from .engine import Financials
        try:
            items = []
            for r in range(self.items_table.rowCount()):
                g = lambda c: self.items_table.item(r, c).text()  # noqa: E731
                items.append(LineItem(g(0), g(1), g(2), float(g(3)), float(g(4)), int(float(g(5))),
                                      float(g(6)), float(g(7)), float(g(8))))
        except ValueError as e:
            QMessageBox.warning(self, "Invalid line item", str(e))
            return None
        cases = self._read_cases()
        if cases is None:
            return None
        fin = Financials(self.f_wacc.value(), self.f_wrap.value(), self.f_maint.value(),
                         self.f_buffer.value(), self.f_timeline.value(),
                         self.f_inclusive.currentIndex() == 0, self.f_profile.currentText(),
                         self.f_escal.value())
        return Scenario(fin, items, cases)

    # ---------------- actions ----------------
    def run_cases(self) -> None:
        scn = self.current_scenario()
        if scn is None:
            return
        self.results = run_all(scn)
        self.cnpv_chart.draw(plot_cnpv, self.results)
        self.attr_chart.draw(plot_attribution, self.results)
        s = self.summary
        s.setRowCount(len(self.results))
        for r, res in enumerate(self.results):
            vals = [res.case, res.npv, res.capex_npv, res.labor_npv,
                    res.attribution["detection"], res.attribution["delay"], res.attribution["response"]]
            for c, v in enumerate(vals):
                s.setItem(r, c, QTableWidgetItem(v if c == 0 else f"${v:,.0f}"))
        self.tornado_case.clear()
        self.tornado_case.addItems([c.name for c in scn.cases])
        best = max(self.results, key=lambda x: x.npv)
        self.statusBar().showMessage(f"Ran {len(self.results)} cases. Lowest lifecycle cost: "
                                     f"{best.case} (${-best.npv / 1e6:,.1f}M NPV).")

    def run_uncertainty(self) -> None:
        scn = self.current_scenario()
        if scn is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            mcs = [monte_carlo(scn, c, n=self.mc_n.value()) for c in scn.cases]
            self.mc_chart.draw(plot_mc, mcs)
            case = scn.cases[max(self.tornado_case.currentIndex(), 0)]
            self.tornado_chart.draw(plot_tornado, tornado(scn, case), case.name)
        finally:
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(f"Monte Carlo: {self.mc_n.value()} samples per case.")

    def open_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open scenario", "", "JSON (*.json)")
        if path:
            self.load_scenario(load_json(path))

    def save_json(self) -> None:
        scn = self.current_scenario()
        path, _ = QFileDialog.getSaveFileName(self, "Save scenario", "scenario.json", "JSON (*.json)")
        if scn and path:
            save_json(scn, path)

    def export_xlsx(self) -> None:
        scn = self.current_scenario()
        path, _ = QFileDialog.getSaveFileName(self, "Export results", "results.xlsx", "Excel (*.xlsx)")
        if scn and path:
            export_excel(scn, run_all(scn), path)
            self.statusBar().showMessage(f"Exported {path}")

    def export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export CNPV", "cnpv.csv", "CSV (*.csv)")
        if path and self.results:
            export_csv(self.results, path)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow(example_scenario())
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
