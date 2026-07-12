"""
ui.py
=====
PyQt5 desktop GUI for the pad footing design tool.

Layout:
    Left panel   : grouped input forms (Loads / Soil / Materials / Geometry)
                   + action buttons
    Right panel  : tabbed view -> "Results" (calculation summary with
                   colour-coded OK/NG indicators) and "3D View" (embedded
                   PyVista render window)
"""

import sys
import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QGroupBox, QDoubleSpinBox, QPushButton, QLabel, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QTextEdit, QFileDialog, QMessageBox, QSplitter,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from pyvistaqt import QtInteractor

from design import Loads, SoilProps, Materials, Geometry, auto_design, DesignResult
from visualization import build_scene


def _spin(minimum, maximum, value, decimals=2, step=1.0):
    box = QDoubleSpinBox()
    box.setRange(minimum, maximum)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    return box


class FootingDesignWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Isolated Pad Footing Design  —  NBCC 2020 / CSA A23.3-19")
        self.resize(1500, 900)

        self.last_result: DesignResult = None
        self.last_geometry: Geometry = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ---------------- Left: input panel ----------------
        input_widget = QWidget()
        input_layout = QVBoxLayout(input_widget)
        input_layout.addWidget(self._build_header())
        input_layout.addWidget(self._build_loads_group())
        input_layout.addWidget(self._build_soil_group())
        input_layout.addWidget(self._build_materials_group())
        input_layout.addWidget(self._build_geometry_group())
        input_layout.addWidget(self._build_buttons())
        input_layout.addStretch(1)

        input_widget.setMinimumWidth(380)
        input_widget.setMaximumWidth(420)
        splitter.addWidget(input_widget)

        # ---------------- Right: tabs (results / 3D) ----------------
        self.tabs = QTabWidget()
        self.results_tab = self._build_results_tab()
        self.view3d_tab = self._build_3d_tab()
        self.tabs.addTab(self.results_tab, "Results")
        self.tabs.addTab(self.view3d_tab, "3D View")
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    def _build_header(self):
        lbl = QLabel("PAD FOOTING DESIGN")
        f = QFont()
        f.setPointSize(16)
        f.setBold(True)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #1a3a5c; padding: 6px;")
        return lbl

    def _build_loads_group(self):
        box = QGroupBox("A. Loads")
        form = QFormLayout(box)

        self.in_D = _spin(0, 1e6, 500.0, 1, 10)
        self.in_L = _spin(0, 1e6, 250.0, 1, 10)
        self.in_W = _spin(-1e6, 1e6, 50.0, 1, 5)
        self.in_E = _spin(-1e6, 1e6, 0.0, 1, 5)
        self.in_Mx = _spin(-1e6, 1e6, 0.0, 1, 5)
        self.in_My = _spin(-1e6, 1e6, 0.0, 1, 5)

        form.addRow("Dead Load, D (kN):", self.in_D)
        form.addRow("Live Load, L (kN):", self.in_L)
        form.addRow("Wind Load, W (kN):", self.in_W)
        form.addRow("Seismic Load, E (kN):", self.in_E)
        form.addRow("Moment Mx (kN·m):", self.in_Mx)
        form.addRow("Moment My (kN·m):", self.in_My)
        return box

    def _build_soil_group(self):
        box = QGroupBox("B. Soil")
        form = QFormLayout(box)
        self.in_qallow = _spin(1, 5000, 150.0, 1, 5)
        form.addRow("Allowable Bearing Capacity (kPa):", self.in_qallow)
        return box

    def _build_materials_group(self):
        box = QGroupBox("C. Materials")
        form = QFormLayout(box)
        self.in_fc = _spin(15, 100, 25.0, 1, 1)
        self.in_fy = _spin(300, 600, 400.0, 0, 5)
        form.addRow("f'c (MPa):", self.in_fc)
        form.addRow("fy (MPa):", self.in_fy)
        return box

    def _build_geometry_group(self):
        box = QGroupBox("D. Geometry")
        form = QFormLayout(box)
        self.in_c1 = _spin(150, 3000, 400.0, 0, 25)
        self.in_c2 = _spin(150, 3000, 400.0, 0, 25)
        self.in_t = _spin(200, 3000, 500.0, 0, 25)
        form.addRow("Column Width, c1 (mm):", self.in_c1)
        form.addRow("Column Depth, c2 (mm):", self.in_c2)
        form.addRow("Initial Thickness, t (mm):", self.in_t)
        return box

    def _build_buttons(self):
        box = QGroupBox("Actions")
        layout = QVBoxLayout(box)

        self.btn_design = QPushButton("Design Footing")
        self.btn_auto = QPushButton("Auto Size")
        self.btn_3d = QPushButton("Show 3D")
        self.btn_export = QPushButton("Export Results")

        for b in (self.btn_design, self.btn_auto, self.btn_3d, self.btn_export):
            b.setMinimumHeight(36)
            layout.addWidget(b)

        self.btn_design.clicked.connect(self.on_design_footing)
        self.btn_auto.clicked.connect(self.on_auto_size)
        self.btn_3d.clicked.connect(self.on_show_3d)
        self.btn_export.clicked.connect(self.on_export)

        return box

    def _build_results_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.lbl_combo = QLabel("Governing load combination: —")
        self.lbl_dims = QLabel("Footing dimensions (L x B x t): —")
        self.lbl_pressure = QLabel("Soil pressure (max / min): —")
        for lbl in (self.lbl_combo, self.lbl_dims, self.lbl_pressure):
            lbl.setStyleSheet("font-size: 13px; padding: 2px;")
            layout.addWidget(lbl)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Check", "Value", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        layout.addWidget(QLabel("Calculation Log:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setMinimumHeight(200)
        layout.addWidget(self.log_box)

        return widget

    def _build_3d_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        btn_row = QHBoxLayout()
        self.btn_toggle_rebar = QPushButton("Toggle Reinforcement")
        self.btn_toggle_rebar.clicked.connect(self.on_toggle_rebar)
        btn_row.addWidget(self.btn_toggle_rebar)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.plotter = QtInteractor(widget)
        layout.addWidget(self.plotter.interactor)
        self.scene = None
        return widget

    # ------------------------------------------------------------------
    # Gather inputs into design.py data classes
    # ------------------------------------------------------------------
    def _gather_inputs(self):
        loads = Loads(
            D=self.in_D.value(), L=self.in_L.value(),
            W=self.in_W.value(), E=self.in_E.value(),
            Mx=self.in_Mx.value(), My=self.in_My.value(),
        )
        soil = SoilProps(q_allow=self.in_qallow.value())
        mat = Materials(fc=self.in_fc.value(), fy=self.in_fy.value())
        geo = Geometry(
            col_width=self.in_c1.value(), col_depth=self.in_c2.value(),
            thickness=self.in_t.value(),
            L=max(self.in_c1.value() + 600, 1500),
            B=max(self.in_c2.value() + 600, 1500),
        )
        return loads, soil, mat, geo

    # ------------------------------------------------------------------
    # Button actions
    # ------------------------------------------------------------------
    def on_design_footing(self):
        self._run_design()

    def on_auto_size(self):
        self._run_design()

    def _run_design(self):
        loads, soil, mat, geo = self._gather_inputs()
        result = auto_design(loads, soil, mat, geo)
        self.last_result = result
        self.last_geometry = result.geometry if result.ok else geo

        self._populate_results(result)
        self.tabs.setCurrentWidget(self.results_tab)

        if result.ok:
            self._render_3d(self.last_geometry, result)

    def _populate_results(self, result: DesignResult):
        if not result.ok:
            self.lbl_combo.setText("Governing load combination: N/A (did not converge)")
            self.lbl_dims.setText("Footing dimensions: N/A")
            self.lbl_pressure.setText("Soil pressure: N/A")
            self.table.setRowCount(0)
            self.log_box.setPlainText("\n".join(result.log))
            QMessageBox.warning(self, "Design Warning",
                                 "Auto-design did not converge. See calculation log for details.")
            return

        geo = result.geometry
        self.lbl_combo.setText(f"Governing load combination: {result.governing_combo}")
        self.lbl_dims.setText(
            f"Footing dimensions (L x B x t): {geo.L:.0f} x {geo.B:.0f} x {geo.thickness:.0f} mm")
        self.lbl_pressure.setText(
            f"Soil pressure — max: {result.q_max:.1f} kPa   min: {result.q_min:.1f} kPa")

        rows = [
            ("Bearing pressure utilization", f"{result.utilization['bearing']*100:.0f} %",
             result.utilization['bearing'] <= 1.0),
            ("Eccentricity within middle third", "e within kern" if result.within_kern else "e OUTSIDE kern",
             result.within_kern),
            ("Reinforcement — long direction", result.bar_L, True),
            ("Reinforcement — short direction", result.bar_B, True),
            ("Reinf. area required, long dir.", f"{result.As_req_L:.0f} mm²/m", True),
            ("Reinf. area required, short dir.", f"{result.As_req_B:.0f} mm²/m", True),
            ("One-way shear, long direction", f"util = {result.utilization['one_way_long']*100:.0f}%",
             result.one_way_status.get("long_dir", False)),
            ("One-way shear, short direction", f"util = {result.utilization['one_way_short']*100:.0f}%",
             result.one_way_status.get("short_dir", False)),
            ("Punching (two-way) shear", f"util = {result.utilization['punching']*100:.0f}%",
             result.punching_status),
        ]

        self.table.setRowCount(len(rows))
        for i, (check, value, ok) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(check))
            self.table.setItem(i, 1, QTableWidgetItem(str(value)))
            status_item = QTableWidgetItem("OK" if ok else "NG")
            status_item.setBackground(QColor("#c8e6c9") if ok else QColor("#ffcdd2"))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, status_item)

        self.log_box.setPlainText("\n".join(result.log))

    def on_show_3d(self):
        if self.last_geometry is None:
            loads, soil, mat, geo = self._gather_inputs()
            self.last_geometry = geo
        self._render_3d(self.last_geometry, self.last_result)
        self.tabs.setCurrentWidget(self.view3d_tab)

    def _render_3d(self, geo: Geometry, result: DesignResult):
        self.scene = build_scene(self.plotter, geo, result)
        self.plotter.reset_camera()

    def on_toggle_rebar(self):
        if self.scene is not None:
            self.scene.toggle_rebar()

    def on_export(self):
        if self.last_result is None or not self.last_result.ok:
            QMessageBox.information(self, "Export", "Run a successful design before exporting.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "footing_design_summary.txt", "Text Files (*.txt)")
        if not path:
            return

        result = self.last_result
        geo = result.geometry
        lines = []
        lines.append("=" * 70)
        lines.append("ISOLATED PAD FOOTING — DESIGN SUMMARY")
        lines.append(f"Generated: {datetime.datetime.now().isoformat(timespec='seconds')}")
        lines.append("Code basis: NBCC 2020 / CSA A23.3-19")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"Governing ULS combination : {result.governing_combo}")
        lines.append(f"Footing dimensions (LxBxt): {geo.L:.0f} x {geo.B:.0f} x {geo.thickness:.0f} mm")
        lines.append(f"Column dimensions (c1xc2) : {geo.col_width:.0f} x {geo.col_depth:.0f} mm")
        lines.append(f"Soil bearing q_max / q_min: {result.q_max:.1f} / {result.q_min:.1f} kPa")
        lines.append(f"Eccentricity within kern  : {result.within_kern}")
        lines.append("")
        lines.append(f"Reinforcement, long dir.  : {result.bar_L}  (As_req={result.As_req_L:.0f} mm^2/m)")
        lines.append(f"Reinforcement, short dir. : {result.bar_B}  (As_req={result.As_req_B:.0f} mm^2/m)")
        lines.append("")
        lines.append("Utilization ratios:")
        for k, v in result.utilization.items():
            lines.append(f"  {k:20s}: {v*100:.1f} %")
        lines.append("")
        lines.append("Calculation log:")
        lines.extend(f"  {l}" for l in result.log)
        lines.append("")
        lines.append("-" * 70)
        lines.append("NOTE: This tool uses simplified NBCC load combinations and the CSA")
        lines.append("A23.3 simplified one-way shear method. Engineer of record must verify")
        lines.append("against full code provisions prior to construction/permit issuance.")

        with open(path, "w") as f:
            f.write("\n".join(lines))

        QMessageBox.information(self, "Export Complete", f"Results exported to:\n{path}")


def run_app():
    app = QApplication(sys.argv)
    window = FootingDesignWindow()
    window.show()
    sys.exit(app.exec_())