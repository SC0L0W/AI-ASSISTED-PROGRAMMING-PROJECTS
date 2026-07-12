"""
visualization.py
=================
3D visualization of the isolated pad footing, column stub, and reinforcement
mesh, using PyVista.

Design.Geometry / DesignResult objects (from design.py) are consumed directly.
All internal PyVista geometry is built in millimetres for consistency with the
rest of the application, then displayed with an equal aspect ratio.
"""

import numpy as np
import pyvista as pv

from design import Geometry, DesignResult, BAR_AREAS


def _bar_diameter_mm(bar_designation: str) -> float:
    """Approximate nominal bar diameter (mm) for Canadian metric bars."""
    diam_map = {
        "10M": 11.3, "15M": 16.0, "20M": 19.5, "25M": 25.2,
        "30M": 29.9, "35M": 35.7, "45M": 43.7, "55M": 56.4,
    }
    return diam_map.get(bar_designation, 16.0)


def _parse_bar_string(bar_str: str):
    """Extract (bar_designation, spacing_mm) from a string like '15M @ 200 mm o.c. (long dir.)'."""
    try:
        parts = bar_str.split("@")
        bar = parts[0].strip()
        spacing = float(parts[1].strip().split(" ")[0])
        return bar, spacing
    except Exception:
        return "15M", 200.0


class FootingScene:
    """Builds and manages the PyVista plotter scene for a footing design."""

    def __init__(self, plotter: pv.Plotter = None):
        self.plotter = plotter if plotter is not None else pv.Plotter()
        self.rebar_actors = []
        self.show_rebar = True

    def build(self, geo: Geometry, result: DesignResult = None):
        self.plotter.clear()
        self.rebar_actors = []

        L, B, t = geo.L, geo.B, geo.thickness
        c1, c2 = geo.col_width, geo.col_depth
        col_height = 800.0  # visual stub height above footing, mm

        # ---- Footing concrete block ----
        footing = pv.Cube(
            center=(0, 0, -t / 2.0),
            x_length=L, y_length=B, z_length=t,
        )
        self.plotter.add_mesh(footing, color="#c9c2b4", opacity=0.85,
                               show_edges=True, edge_color="#6e6656", label="Footing")

        # ---- Column stub ----
        column = pv.Cube(
            center=(0, 0, col_height / 2.0),
            x_length=c1, y_length=c2, z_length=col_height,
        )
        self.plotter.add_mesh(column, color="#8c8c8c", opacity=1.0,
                               show_edges=True, edge_color="#333333", label="Column")

        # ---- Reinforcement mesh (bottom, both directions) ----
        if result is not None and result.bar_L and result.bar_B:
            self._add_rebar_mesh(geo, result)

        # ---- Dimension annotations ----
        self._add_dimensions(geo)

        self.plotter.add_legend()
        self.plotter.show_axes()
        self.plotter.camera_position = "iso"
        self.plotter.set_background("white")

    def _add_rebar_mesh(self, geo: Geometry, result: DesignResult):
        L, B, t = geo.L, geo.B, geo.thickness
        cover = geo.cover
        z_bottom = -t + cover  # centroid of bottom bar layer, approx

        bar_L, spacing_L = _parse_bar_string(result.bar_L)
        bar_B, spacing_B = _parse_bar_string(result.bar_B)
        dia_L = _bar_diameter_mm(bar_L)
        dia_B = _bar_diameter_mm(bar_B)

        # Bars running in the L-direction (long axis), spaced along B
        n_bars_L = max(int(B // spacing_L), 1)
        y_positions = np.linspace(-B / 2 + cover, B / 2 - cover, n_bars_L)
        for y in y_positions:
            bar = pv.Cylinder(center=(0, y, z_bottom), direction=(1, 0, 0),
                               radius=dia_L / 2.0, height=L - 2 * cover)
            actor = self.plotter.add_mesh(bar, color="#b03a2e")
            self.rebar_actors.append(actor)

        # Bars running in the B-direction (short axis), spaced along L
        n_bars_B = max(int(L // spacing_B), 1)
        x_positions = np.linspace(-L / 2 + cover, L / 2 - cover, n_bars_B)
        for x in x_positions:
            bar = pv.Cylinder(center=(x, 0, z_bottom + dia_L), direction=(0, 1, 0),
                               radius=dia_B / 2.0, height=B - 2 * cover)
            actor = self.plotter.add_mesh(bar, color="#1f618d")
            self.rebar_actors.append(actor)

    def _add_dimensions(self, geo: Geometry):
        L, B, t = geo.L, geo.B, geo.thickness
        self.plotter.add_point_labels(
            points=[(0, -B / 2 - 150, -t / 2), (L / 2 + 150, 0, -t / 2), (0, 0, -t - 100)],
            labels=[f"L = {L:.0f} mm", f"B = {B:.0f} mm", f"t = {t:.0f} mm"],
            font_size=14, text_color="black", shape=None, always_visible=True,
        )

    def toggle_rebar(self):
        self.show_rebar = not self.show_rebar
        for actor in self.rebar_actors:
            actor.SetVisibility(self.show_rebar)
        self.plotter.render()


def build_scene(plotter: pv.Plotter, geo: Geometry, result: DesignResult = None) -> FootingScene:
    """Convenience function used by ui.py to (re)build the 3D scene."""
    scene = FootingScene(plotter)
    scene.build(geo, result)
    return scene