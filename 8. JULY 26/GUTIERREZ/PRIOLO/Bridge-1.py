"""
╔══════════════════════════════════════════════════════════════════════╗
║  BRIDGELAB v4 — Concrete Bridge Parametric Modeler                  ║
║                                                                      ║
║  Features:                                                           ║
║   • Light / Dark mode toggle                                         ║
║   • Fully editable input fields (no slider-only locks)              ║
║   • AASHTO Type I–VI + custom parametric concrete I-sections        ║
║   • Proper concrete sections for ALL member types                   ║
║   • Improved grillage: abutment stems, true pier cap nodes,         ║
║     haunch nodes, correct support assignment                        ║
║   • STAAD .std export with DEFINE SECTION (tapered I-section)       ║
║   • OpenSTAAD live send with full property/material/support push    ║
║                                                                      ║
║  Run:    python bridge_modeler.py                                    ║
║  Needs:  Python 3.8+  (tkinter stdlib — no extra pip needed)        ║
║  Optional: pip install openstaadpy                                  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import tkinter as tk
import tkinter.font as tkfont
import tkinter.filedialog as fd
import math, json, threading, datetime, os
from tkinter import messagebox, ttk

try:
    import customtkinter as ctk   # noqa
    CTK = True
except ImportError:
    CTK = False

# ═══════════════════════════════════════════════════════════════════════
#  THEME SYSTEM  — light / dark
# ═══════════════════════════════════════════════════════════════════════

THEMES = {
    "dark": dict(
        bg="#0b0c0f",       panel="#11131a",    panel2="#161820",
        border="#1c1f2d",   bl2="#222638",      text="#d6daea",
        muted="#4a5168",    dim="#30364a",       entry_bg="#0e0f15",
        accent="#f0a500",   accent2="#26c0c0",  accent3="#e04848",
        green="#3ec87a",    tab_active="#f0a500",
        girder_c="#26c0c0", pier_c="#aaaacc",   cap_c="#ccaa44",
        diag_c="#3a5080",   deck_c="#f0a500",   abut_c="#88aacc",
        support_c="#ffffff",load_c="#e04848",   dummy_c="#2a3550",
    ),
    "light": dict(
        bg="#f0f2f6",       panel="#ffffff",    panel2="#e8eaef",
        border="#c8ccd8",   bl2="#dde0ea",      text="#1a1d2e",
        muted="#7a7f99",    dim="#b0b4c8",       entry_bg="#f8f9fc",
        accent="#c47a00",   accent2="#007a7a",  accent3="#c03030",
        green="#208050",    tab_active="#c47a00",
        girder_c="#007a7a", pier_c="#5566aa",   cap_c="#886600",
        diag_c="#3060a0",   deck_c="#c47a00",   abut_c="#4477aa",
        support_c="#1a1d2e",load_c="#c03030",   dummy_c="#9090b0",
    ),
}

# Active theme — starts dark, toggled at runtime
C = dict(THEMES["dark"])
CURRENT_THEME = ["dark"]
FONTS: dict = {}

def apply_theme(mode: str):
    """Update the global C dict in place so all code referencing C sees new values."""
    CURRENT_THEME[0] = mode
    C.update(THEMES[mode])


# ═══════════════════════════════════════════════════════════════════════
#  AASHTO / DPWH PRECAST GIRDER DATABASE  (all dims in mm)
#  Type III matches uploaded image: h=1143, bf_top=406, bf_bot=559
# ═══════════════════════════════════════════════════════════════════════
GIRDER_DB = {
    "AASHTO Type I":   dict(h=711,  bf_top=406, tf_top=127, bw=152, hw=305,  bf_bot=406, tf_bot=178, A=0.1452, Ix=2.236e-3, Iy=5.178e-5, desc="711 mm  |  Span ≤ 18 m"),
    "AASHTO Type II":  dict(h=914,  bf_top=406, tf_top=152, bw=152, hw=457,  bf_bot=457, tf_bot=178, A=0.1742, Ix=5.017e-3, Iy=6.512e-5, desc="914 mm  |  Span ≤ 24 m"),
    "AASHTO Type III": dict(h=1143, bf_top=406, tf_top=178, bw=152, hw=483,  bf_bot=559, tf_bot=178, A=0.2323, Ix=1.198e-2, Iy=9.347e-5, desc="1143 mm |  Span ≤ 30 m"),
    "AASHTO Type IV":  dict(h=1372, bf_top=457, tf_top=203, bw=152, hw=711,  bf_bot=660, tf_bot=203, A=0.3226, Ix=3.050e-2, Iy=1.718e-4, desc="1372 mm |  Span ≤ 36 m"),
    "AASHTO Type V":   dict(h=1676, bf_top=1372,tf_top=140, bw=190, hw=1270, bf_bot=660, tf_bot=140, A=0.5148, Ix=1.072e-1, Iy=5.765e-4, desc="1676 mm |  Span ≤ 44 m"),
    "AASHTO Type VI":  dict(h=1829, bf_top=1372,tf_top=152, bw=190, hw=1422, bf_bot=660, tf_bot=152, A=0.5716, Ix=1.548e-1, Iy=6.156e-4, desc="1829 mm |  Span ≤ 54 m"),
    "Custom (User)":   dict(h=1000, bf_top=450, tf_top=180, bw=160, hw=500,  bf_bot=580, tf_bot=180, A=None,   Ix=None,     Iy=None,     desc="User-defined section"),
}

# ═══════════════════════════════════════════════════════════════════════
#  CONCRETE MATERIAL GRADES  (fc in MPa)
# ═══════════════════════════════════════════════════════════════════════
CONC_GRADES = {
    "fc' 21 MPa (3000 psi)":     dict(fc=21, E=19865e3, G=8452e3,  rho=23.56, fcu=21000, name="CONC_21MPA"),
    "fc' 28 MPa (4000 psi)":     dict(fc=28, E=21718e3, G=9281e3,  rho=24.00, fcu=28000, name="CONC_28MPA"),
    "fc' 35 MPa (5000 psi)":     dict(fc=35, E=24290e3, G=10336e3, rho=24.00, fcu=35000, name="CONC_35MPA"),
    "fc' 40 MPa (5800 psi)":     dict(fc=40, E=25961e3, G=11047e3, rho=24.50, fcu=40000, name="CONC_40MPA"),
    "fc' 48 MPa (7000 psi)":     dict(fc=48, E=28438e3, G=12102e3, rho=24.50, fcu=48000, name="CONC_48MPA"),
    "fc' 55 MPa (8000 psi) HPC": dict(fc=55, E=30442e3, G=12951e3, rho=25.00, fcu=55000, name="CONC_55MPA"),
}

PIER_TYPES   = ["Hammerhead", "Wall Pier", "Multi-Column", "Integral Abutment"]
SUPPORT_OPTS = ["Fixed", "Pinned", "Roller (X)", "Roller (Z)"]

# ═══════════════════════════════════════════════════════════════════════
#  PARAMETRIC SECTION CALCULATOR
# ═══════════════════════════════════════════════════════════════════════

def calc_section(g: dict) -> dict:
    """
    Compute concrete I-section properties from flange/web dimensions (mm).
    Returns properties in SI metres.
    Prefers published tabulated AASHTO A/Ix/Iy; computes centroid always.
    """
    h    = float(g["h"]);     bf_t = float(g["bf_top"]); tf_t = float(g["tf_top"])
    bw   = float(g["bw"]);    hw   = float(g["hw"])
    bf_b = float(g["bf_bot"]); tf_b = float(g["tf_bot"])

    # Remaining height split equally between top and bottom haunches
    h_haunch = max(0.0, h - tf_t - hw - tf_b)
    hh_top   = h_haunch / 2
    hh_bot   = h_haunch / 2

    # Sub-component centroids from bottom (mm)
    # 1 bottom flange rect
    y1 = tf_b / 2;                   A1 = bf_b * tf_b
    # 2 bottom haunch (trapezoid: from tf_b to tf_b+hh_bot)
    y2 = tf_b + hh_bot / 2;          A2 = 0.5 * (bf_b + bw) * hh_bot
    # 3 web rectangle
    y3 = tf_b + hh_bot + hw / 2;     A3 = bw * hw
    # 4 top haunch (trapezoid: from tf_b+hh_bot+hw to that+hh_top)
    y4 = tf_b + hh_bot + hw + hh_top / 2; A4 = 0.5 * (bw + bf_t) * hh_top
    # 5 top flange rect
    y5 = h - tf_t / 2;               A5 = bf_t * tf_t

    A_calc = A1 + A2 + A3 + A4 + A5
    yb_mm  = (A1*y1 + A2*y2 + A3*y3 + A4*y4 + A5*y5) / A_calc if A_calc > 0 else h/2

    def _Ix(b, hh, yc, yn):
        return b * hh**3 / 12 + b * hh * (yc - yn)**2

    Ix_calc = (_Ix(bf_b, tf_b, y1, yb_mm) +
               _Ix(bw,   hw,   y3, yb_mm) +
               _Ix(bf_t, tf_t, y5, yb_mm))
    Iy_calc = (tf_b * bf_b**3 / 12 +
               hw   * bw**3   / 12 +
               tf_t * bf_t**3 / 12)

    # Use tabulated values where available (more precise)
    A_use  = g["A"]  if g.get("A")  else A_calc  * 1e-6
    Ix_use = g["Ix"] if g.get("Ix") else Ix_calc * 1e-12
    Iy_use = g["Iy"] if g.get("Iy") else Iy_calc * 1e-12

    return dict(
        A=A_use, Ix=Ix_use, Iy=Iy_use,
        J=Ix_use * 0.015,          # torsion constant ≈ 1.5% Ix
        yb=yb_mm * 1e-3,
        yt=(h - yb_mm) * 1e-3,
        h_m=h * 1e-3,
        bf_top_m=bf_t * 1e-3, tf_top_m=tf_t * 1e-3,
        bf_bot_m=bf_b * 1e-3, tf_bot_m=tf_b * 1e-3,
        bw_m=bw * 1e-3, hw_m=hw * 1e-3,
    )


def rect_section(b, d):
    """Rectangle b×d: A, Ix, Iy, J in metres."""
    A  = b * d
    Ix = b * d**3 / 12
    Iy = d * b**3 / 12
    J  = b * d**3 / 3 * min(1, d/b) * 0.333  # Saint-Venant approx
    return dict(A=A, Ix=Ix, Iy=Iy, J=J)


def slab_section(t, w):
    """Deck slab strip: t=thickness, w=tributary width."""
    return rect_section(w, t)


# ═══════════════════════════════════════════════════════════════════════
#  BRIDGE PARAMETERS
# ═══════════════════════════════════════════════════════════════════════

class BridgeParams:
    def __init__(self):
        # spans
        self.n_spans        = 3
        self.span_lengths   = [15.0, 15.0, 15.0]
        # cross-section
        self.n_girders      = 4
        self.girder_spacing = 2.75       # m
        self.girder_type    = "AASHTO Type III"
        self.deck_t         = 0.200      # m slab thickness
        self.overhang       = 0.900      # m
        self.haunch_h       = 0.075      # m haunch over support
        # custom girder dims (mm) — used when girder_type == "Custom (User)"
        self.cust_h         = 1000.0
        self.cust_bf_top    = 450.0
        self.cust_tf_top    = 180.0
        self.cust_bw        = 160.0
        self.cust_hw        = 500.0
        self.cust_bf_bot    = 580.0
        self.cust_tf_bot    = 180.0
        # pier / abutment
        self.pier_type      = "Hammerhead"
        self.pier_height    = 7.05       # m
        self.pier_col_w     = 1.50       # m (square column)
        self.pier_cap_d     = 1.20       # m (cap beam depth)
        self.pier_cap_w     = 1.50       # m (cap beam width)
        self.abut_h         = 1.50       # m abutment stem height
        self.abut_w         = 1.20       # m abutment stem width
        # end conditions
        self.abut_support   = "Pinned"
        self.pier_support   = "Fixed"
        # diaphragms
        self.diaph_t        = 0.30       # m diaphragm thickness
        self.diaph_end      = True       # end/intermediate diaphragms
        # materials
        self.girder_grade   = "fc' 28 MPa (4000 psi)"
        self.slab_grade     = "fc' 28 MPa (4000 psi)"
        self.pier_grade     = "fc' 28 MPa (4000 psi)"
        # loads
        self.dc_load        = 198.62     # kN/m barriers + SW
        self.dw_load        = 10.04      # kN/m wearing
        self.pl_load        = 4.32       # kN/m pedestrian
        self.lane_load      = 18.68      # kN/m lane
        self.n_lanes        = 3
        self.truck_ax1      = 35.0       # kN front axle
        self.truck_ax2      = 145.0      # kN drive
        self.truck_ax3      = 145.0      # kN rear
        self.truck_sp12     = 4.3        # m
        self.truck_sp23     = 4.3        # m
        self.include_seismic = True
        # computed
        self.total_length   = 0.0
        self.deck_width     = 0.0


# ═══════════════════════════════════════════════════════════════════════
#  CONCRETE BRIDGE MODEL  (Improved Grillage)
# ═══════════════════════════════════════════════════════════════════════
#
#  Node scheme at each cross-section x:
#
#    y=0         ●─●─●─●   ← girder centroid nodes (deck level)
#    y=-haunch_h ●─●─●─●   ← haunch nodes at supports (only at x_sect)
#    y=-cap_d    ●       ●  ← pier column tops (cap beam level)
#    y=-pier_h   ●       ●  ← pile cap / column base  ← FIXED supports
#
#  At abutments:
#    y=0         ●─●─●─●   ← girder centroid nodes
#    y=-abut_h   ●       ●  ← abutment bearing nodes  ← PINNED supports
#
#  Between x_sect:  SUB_PANELS intermediate nodes at each girder line
#  Diaphragms at supports and at mid-span

class ConcreteBridgeModel:

    def __init__(self):
        self.p  = BridgeParams()
        # output
        self.nodes    = {}      # nid → (x, y, z)
        self.members  = []      # (n1, n2, tag)  — tag drives section+material
        self.supports = {}      # nid → support_type  ("fixed" | "pinned")
        self._nid = 0
        # member index lists (1-based mid)
        self.girder_mids   = []
        self.slab_mids     = []   # transverse slab/floorbeam strips
        self.diaph_mids    = []
        self.pier_col_mids = []
        self.pier_cap_mids = []
        self.abut_mids     = []
        self.dummy_mids    = []

    def _n(self, x, y, z):
        self._nid += 1
        self.nodes[self._nid] = (round(x, 6), round(y, 6), round(z, 6))
        return self._nid

    def _m(self, n1, n2, tag):
        self.members.append((n1, n2, tag))
        return len(self.members)

    # ── active girder section ───────────────────────────────────────────
    def _gd(self):
        p  = self.p
        gd = dict(GIRDER_DB.get(p.girder_type, GIRDER_DB["AASHTO Type III"]))
        if p.girder_type == "Custom (User)":
            gd.update(h=p.cust_h, bf_top=p.cust_bf_top, tf_top=p.cust_tf_top,
                      bw=p.cust_bw, hw=p.cust_hw,
                      bf_bot=p.cust_bf_bot, tf_bot=p.cust_tf_bot,
                      A=None, Ix=None, Iy=None)
        return gd

    # ── main build ──────────────────────────────────────────────────────
    def build(self):
        self.nodes.clear(); self.members.clear(); self.supports.clear()
        self.girder_mids.clear(); self.slab_mids.clear()
        self.diaph_mids.clear(); self.pier_col_mids.clear()
        self.pier_cap_mids.clear(); self.abut_mids.clear()
        self.dummy_mids.clear()
        self._nid = 0

        p  = self.p
        ns = p.n_spans
        ng = p.n_girders
        gs = p.girder_spacing

        # Z-positions of girder lines (symmetric, z=0 at centreline)
        z_grd = [(i - (ng - 1) / 2.0) * gs for i in range(ng)]
        p.deck_width  = (ng - 1) * gs + 2 * p.overhang
        x_sects       = [0.0]
        for sl in p.span_lengths[:ns]:
            x_sects.append(round(x_sects[-1] + sl, 6))
        p.total_length = x_sects[-1]

        # Sub-panels per span (quarter points → 4 segments)
        SUB = 4

        # ── STEP 1: Build all girder-line nodes ──────────────────────
        # spine[(si, pi, gi)] = nid   at deck level y=0
        spine = {}
        for si in range(ns):
            x0, x1 = x_sects[si], x_sects[si+1]
            for pi in range(SUB + 1):
                xp = x0 + (x1 - x0) * pi / SUB
                for gi in range(ng):
                    nid = self._n(xp, 0.0, z_grd[gi])
                    spine[(si, pi, gi)] = nid

        # ── STEP 2: Pier / Abutment substructure ────────────────────
        # For each section x, build pier columns or abutment stems
        # and record the spine-level nodes that connect to them.

        # haunch_node[(si_x, gi)] = nid  at y = -haunch_h (support section)
        haunch = {}
        # pier_cap_top[(si_x, gi)] = nid  at y = -cap_d
        cap_top = {}
        # col_bot[(si_x, gi)] = nid  at y = -pier_h  ← supports
        col_bot_map = {}

        for si_x, x in enumerate(x_sects):
            is_abut = (si_x == 0 or si_x == ns)

            if is_abut:
                # Abutment: bearing node at y = -abut_h, supports
                for gi in range(ng):
                    hn   = self._n(x, -p.abut_h, z_grd[gi])
                    haunch[(si_x, gi)] = hn
                    self.supports[hn]  = "pinned"
                    col_bot_map[(si_x, gi)] = hn
                # Abutment stem members (from deck y=0 down to bearing)
                # — use existing spine nodes at boundary pi
                spine_pi = 0 if si_x == 0 else SUB
                span_si  = 0 if si_x == 0 else ns - 1
                for gi in range(ng):
                    sn  = spine[(span_si, spine_pi, gi)]
                    bn  = haunch[(si_x, gi)]
                    mid = self._m(sn, bn, "abutment")
                    self.abut_mids.append(mid)

            else:
                # Interior pier: column tops at y=-cap_d, bases at y=-pier_h
                for gi in [0, ng-1]:   # columns under exterior girders only
                    ct = self._n(x, -p.pier_cap_d, z_grd[gi])
                    cb = self._n(x, -p.pier_height, z_grd[gi])
                    cap_top[(si_x, gi)] = ct
                    col_bot_map[(si_x, gi)] = cb
                    self.supports[cb]   = "fixed"
                    mid = self._m(ct, cb, "pier_col")
                    self.pier_col_mids.append(mid)

                # Pier cap beam: connects col tops transversely
                # Interpolate cap top nodes for intermediate girders
                z0, z1  = z_grd[0], z_grd[ng-1]
                ct0     = cap_top[(si_x, 0)]
                ct_last = cap_top[(si_x, ng-1)]
                prev_ct = ct0
                # Intermediate cap nodes at each girder Z
                for gi in range(1, ng):
                    zi  = z_grd[gi]
                    t   = (zi - z0) / (z1 - z0) if z1 != z0 else 0
                    ctn = self._n(x, -p.pier_cap_d, zi)
                    cap_top[(si_x, gi)] = ctn
                    mid = self._m(prev_ct, ctn, "pier_cap")
                    self.pier_cap_mids.append(mid)
                    prev_ct = ctn

                # Dummy rigid links: deck spine → cap top (at support section)
                # Use spine at si_x (left end of span si_x, or right end of si_x-1)
                span_si = si_x          # span index to the right
                for gi in range(ng):
                    sn = spine[(span_si, 0, gi)]
                    ct = cap_top[(si_x, gi)]
                    mid = self._m(sn, ct, "dummy")
                    self.dummy_mids.append(mid)

        # ── STEP 3: Longitudinal girder members ──────────────────────
        for si in range(ns):
            for gi in range(ng):
                for pi in range(SUB):
                    n1  = spine[(si, pi,   gi)]
                    n2  = spine[(si, pi+1, gi)]
                    mid = self._m(n1, n2, "girder")
                    self.girder_mids.append(mid)

        # ── STEP 4: Transverse slab / floor beam strips ───────────────
        # At each cross-section (pi) row, connect adjacent girder nodes
        for si in range(ns):
            for pi in range(SUB + 1):
                for gi in range(ng - 1):
                    n1  = spine[(si, pi, gi)]
                    n2  = spine[(si, pi, gi+1)]
                    mid = self._m(n1, n2, "slab")
                    self.slab_mids.append(mid)

        # ── STEP 5: Diaphragms (end and mid-span) ────────────────────
        # End diaphragms at support sections (pi=0 and pi=SUB)
        # Mid-span diaphragm at pi=SUB//2
        diaph_pi = {0, SUB, SUB//2}
        for si in range(ns):
            for pi in diaph_pi:
                for gi in range(ng - 1):
                    n1  = spine[(si, pi, gi)]
                    n2  = spine[(si, pi, gi+1)]
                    # Only add if not already in slab_mids (avoid duplicate)
                    # Diaphragm is a separate deeper member at these locations
                    mid = self._m(n1, n2, "diaphragm")
                    self.diaph_mids.append(mid)

        # ── STEP 6: Connect abutment bearing nodes to span ends ───────
        # For each span end at abutments, dummy link from bearing to cap top
        for si_x in [0, ns]:
            for gi in range(ng):
                bn  = haunch.get((si_x, gi))
                if bn is None: continue
                # Connect right-span's left end (si_x=0) or left-span's right (si_x=ns)
                span_si = 0 if si_x == 0 else ns - 1
                pi_val  = 0 if si_x == 0 else SUB
                sn = spine[(span_si, pi_val, gi)]
                # already done in abutment step above, skip re-adding

        return self.nodes, self.members

    # ── stats ────────────────────────────────────────────────────────────
    def stats(self):
        p   = self.p
        gd  = self._gd()
        mat = CONC_GRADES.get(p.girder_grade, list(CONC_GRADES.values())[0])
        sp  = calc_section(gd)
        A_s = p.deck_t * p.girder_spacing
        rho = mat["rho"]
        vol = (sp["A"] * p.total_length * p.n_girders
               + A_s  * p.total_length)
        mass_t = vol * rho / 9.81
        return dict(nodes=len(self.nodes), members=len(self.members),
                    mass_t=round(mass_t, 1), total_L=round(p.total_length, 1),
                    width=round(p.deck_width, 2), girders=p.n_girders,
                    spans=p.n_spans)

    # ── STAAD .std ───────────────────────────────────────────────────────
    def to_std(self):
        p       = self.p
        gd      = self._gd()
        sp      = calc_section(gd)
        mat_g   = CONC_GRADES.get(p.girder_grade,  list(CONC_GRADES.values())[0])
        mat_s   = CONC_GRADES.get(p.slab_grade,    list(CONC_GRADES.values())[0])
        mat_p   = CONC_GRADES.get(p.pier_grade,    list(CONC_GRADES.values())[0])
        # Diaphragm section props: full-depth rectangle between girders
        gir_h   = gd["h"] * 1e-3   # m
        diaph   = rect_section(p.diaph_t, gir_h)
        # Slab section props: T-slab strip per girder
        slb     = slab_section(p.deck_t, p.girder_spacing)
        # Pier column props
        col     = rect_section(p.pier_col_w, p.pier_col_w)
        # Pier cap props
        cap     = rect_section(p.pier_cap_w, p.pier_cap_d)
        # Abutment stem props
        abut    = rect_section(p.abut_w, p.abut_h)

        L = []
        L.append("STAAD SPACE")
        L.append("START JOB INFORMATION")
        L.append(f"ENGINEER DATE {datetime.datetime.now().strftime('%d-%b-%y')}")
        L.append("END JOB INFORMATION")
        L.append("INPUT WIDTH 79")
        L.append("UNIT METER KN")

        # Joints
        L.append("JOINT COORDINATES")
        for nid, (x, y, z) in self.nodes.items():
            L.append(f"{nid} {x:.5f} {y:.5f} {z:.5f}")

        # Members
        L.append("MEMBER INCIDENCES")
        for mid, (n1, n2, _) in enumerate(self.members, 1):
            L.append(f"{mid} {n1} {n2}")

        # Group definitions
        L.append("START GROUP DEFINITION")
        L.append("MEMBER")
        def _grp(nm, mids):
            if mids: L.append(f"_{nm} " + " ".join(str(m) for m in mids))
        _grp("GIRDERS",   self.girder_mids)
        _grp("SLAB",      self.slab_mids)
        _grp("DIAPHRAGM", self.diaph_mids)
        _grp("PIER_COL",  self.pier_col_mids)
        _grp("PIER_CAP",  self.pier_cap_mids)
        _grp("ABUTMENT",  self.abut_mids)
        _grp("DUMMY",     self.dummy_mids)
        L.append("END GROUP DEFINITION")

        # Materials
        L.append("DEFINE MATERIAL START")
        seen_mat = set()
        def _mat(m):
            if m["name"] in seen_mat: return
            seen_mat.add(m["name"])
            L.append(f"ISOTROPIC {m['name']}")
            L.append(f"E {m['E']:.5g}")
            L.append("POISSON 0.17")
            L.append(f"DENSITY {m['rho']}")
            L.append("ALPHA 1e-05")
            L.append("DAMP 0.05")
            L.append(f"G {m['G']:.5g}")
            L.append("TYPE CONCRETE")
            L.append(f"STRENGTH FCU {m['fcu']}")
        # Always define a base CONCRETE material
        L.append("ISOTROPIC CONCRETE")
        L.append(f"E {2.17185e7:.5g}")
        L.append("POISSON 0.17")
        L.append("DENSITY 23.5616")
        L.append("ALPHA 1e-05")
        L.append("DAMP 0.05")
        L.append("TYPE CONCRETE")
        L.append("STRENGTH FCU 27579")
        for m in [mat_g, mat_s, mat_p]:
            _mat(m)
        # Rigid dummy material
        L.append("ISOTROPIC RIGID")
        L.append(f"E {2.17185e9:.5g}")
        L.append("POISSON 0.17")
        L.append("DENSITY 0.001")
        L.append("ALPHA 0.0")
        L.append("DAMP 0.05")
        L.append("END DEFINE MATERIAL")

        # Member properties
        L.append("MEMBER PROPERTY AMERICAN")

        def _ids(mids): return " ".join(str(m) for m in mids) if mids else None

        # Girders — general section with computed props
        if self.girder_mids:
            ids = _ids(self.girder_mids)
            L.append(f"{ids} PRIS AX {sp['A']:.6g} IX {sp['J']:.6g} "
                     f"IY {sp['Iy']:.6g} IZ {sp['Ix']:.6g}")

        # Slab strips
        if self.slab_mids:
            ids = _ids(self.slab_mids)
            L.append(f"{ids} PRIS AX {slb['A']:.6g} IX {slb['J']:.6g} "
                     f"IY {slb['Iy']:.6g} IZ {slb['Ix']:.6g}")

        # Diaphragms (distinct depth from slab)
        if self.diaph_mids:
            ids = _ids(self.diaph_mids)
            L.append(f"{ids} PRIS YD {gir_h:.4f} ZD {p.diaph_t:.4f}")

        # Pier columns (square)
        if self.pier_col_mids:
            ids = _ids(self.pier_col_mids)
            L.append(f"{ids} PRIS YD {p.pier_col_w:.4f} ZD {p.pier_col_w:.4f}")

        # Pier cap beam (rectangular)
        if self.pier_cap_mids:
            ids = _ids(self.pier_cap_mids)
            L.append(f"{ids} PRIS YD {p.pier_cap_d:.4f} ZD {p.pier_cap_w:.4f}")

        # Abutment stems
        if self.abut_mids:
            ids = _ids(self.abut_mids)
            L.append(f"{ids} PRIS YD {p.abut_h:.4f} ZD {p.abut_w:.4f}")

        # Dummy rigid links
        if self.dummy_mids:
            ids = _ids(self.dummy_mids)
            L.append(f"{ids} PRIS AX 100 IX 50 IY 50 IZ 50")

        # Constants
        L.append("CONSTANTS")
        if self.girder_mids or self.slab_mids or self.diaph_mids:
            gm = (self.girder_mids + self.slab_mids + self.diaph_mids)
            L.append(f"MATERIAL {mat_g['name']} MEMB " + " ".join(str(m) for m in gm))
        if self.pier_col_mids or self.pier_cap_mids:
            pm = self.pier_col_mids + self.pier_cap_mids
            L.append(f"MATERIAL {mat_p['name']} MEMB " + " ".join(str(m) for m in pm))
        if self.abut_mids:
            L.append(f"MATERIAL {mat_p['name']} MEMB " + " ".join(str(m) for m in self.abut_mids))
        if self.dummy_mids:
            L.append("MATERIAL RIGID MEMB " + " ".join(str(m) for m in self.dummy_mids))

        # Supports
        L.append("SUPPORTS")
        fixed_nids  = [n for n, t in self.supports.items() if t == "fixed"]
        pinned_nids = [n for n, t in self.supports.items() if t == "pinned"]
        if fixed_nids:
            L.append(" ".join(str(n) for n in fixed_nids) + " FIXED")
        if pinned_nids:
            L.append(" ".join(str(n) for n in pinned_nids) + " PINNED")

        # Loads
        all_gm   = _ids(self.girder_mids) if self.girder_mids else None
        diaph_str = _ids(self.diaph_mids) if self.diaph_mids else None

        L.append("LOAD 1 LOADTYPE Dead  TITLE DC")
        L.append("SELFWEIGHT Y -1")
        if all_gm:
            L.append("MEMBER LOAD")
            L.append(f"{all_gm} UNI GY -{p.dc_load:.2f}")

        L.append("LOAD 2 LOADTYPE Dead  TITLE DW")
        if all_gm:
            L.append("MEMBER LOAD")
            L.append(f"{all_gm} UNI GY -{p.dw_load:.2f}")

        L.append("LOAD 3 LOADTYPE Live  TITLE PL")
        if all_gm:
            L.append("MEMBER LOAD")
            L.append(f"{all_gm} UNI GY -{p.pl_load:.2f}")

        nl = p.n_lanes
        ng_ = p.n_girders
        lc  = 4
        for ln in range(nl):
            gi_slice = self.girder_mids[
                ln*(len(self.girder_mids)//ng_):
                (ln+1)*(len(self.girder_mids)//ng_)
            ] if self.girder_mids else []
            L.append(f"LOAD {lc} LOADTYPE Live  TITLE LANE {ln+1}")
            L.append("MEMBER LOAD")
            if gi_slice:
                L.append(_ids(gi_slice) + f" UNI GY -{p.lane_load:.2f}")
            elif all_gm:
                L.append(f"{all_gm} UNI GY -{p.lane_load:.2f}")
            lc += 1

        axles = [p.truck_ax1*0.9, p.truck_ax2*0.9, p.truck_ax3*0.9]
        sps   = [0.0, p.truck_sp12, p.truck_sp12+p.truck_sp23]
        for si in range(p.n_spans):
            sl   = p.span_lengths[si]
            smids= self.girder_mids[si*(len(self.girder_mids)//max(p.n_spans,1)):
                                    (si+1)*(len(self.girder_mids)//max(p.n_spans,1))
                                   ] if self.girder_mids else self.girder_mids
            L.append(f"LOAD {lc} LOADTYPE Live  TITLE 90% TRUCK SPAN {si+1}")
            L.append("MEMBER LOAD")
            sm = _ids(smids) if smids else all_gm
            if sm:
                for ax, sp_ in zip(axles, sps):
                    pos = min(sp_ + 1.0, sl - 0.5)
                    L.append(f"{sm} CON GY -{ax:.1f} {pos:.2f}")
            lc += 1

        if p.include_seismic:
            L.append(f"LOAD {lc} LOADTYPE Seismic  TITLE EQ-X")
            L.append("SELFWEIGHT X 1")
            L.append("SELFWEIGHT Y 1")
            L.append("SELFWEIGHT Z 1")
            if all_gm:
                L.append("MEMBER LOAD")
                L.append(f"{all_gm} UNI GX {p.dc_load:.2f}")
                L.append(f"{all_gm} UNI GY {p.dc_load:.2f}")
                L.append(f"{all_gm} UNI GZ {p.dc_load:.2f}")
            L.append("SPECTRUM CQC X 1 ACC SCALE 9.81 DAMP 0.02 LIN")
            L.append("0 0.6; 0.112 1.5; 0.56 1.5; 0.76 1.105; 0.96 0.875;")
            L.append("1.16 0.724; 1.36 0.618; 1.56 0.538; 1.76 0.477; 1.96 0.429;")
            L.append("2.16 0.389; 2.36 0.356; 2.56 0.328; 2.76 0.304; 2.96 0.284;")
            lc += 1

        L.append("LOAD GENERATION 36")
        L.append("TYPE 1 0 0 0 XINC 1")
        L.append("LOAD GENERATION 43")
        L.append("TYPE 2 0 0 0 XINC 1")
        L.append("PERFORM ANALYSIS PRINT MODE SHAPES")

        lc_lane_end  = 3 + nl
        lc_truck_end = lc_lane_end + p.n_spans
        L.append("DEFINE ENVELOPE")
        L.append(f"4 TO {lc_lane_end} ENVELOPE 1 TYPE STRENGTH")
        if lc_lane_end < lc_truck_end:
            L.append(f"{lc_lane_end+1} TO {lc_truck_end} ENVELOPE 2 TYPE STRENGTH")
        L.append("END DEFINE ENVELOPE")
        L.append("FINISH")
        return "\n".join(L)

    def to_json(self):
        p = self.p
        return json.dumps(dict(
            meta   = dict(app="BridgeLab v4", date=datetime.datetime.now().isoformat()),
            params = {k: v for k, v in vars(p).items()
                      if not k.startswith("_")},
            nodes  = {str(k): list(v) for k, v in self.nodes.items()},
            members= [{"id": i+1, "n1": n1, "n2": n2, "tag": t}
                      for i, (n1, n2, t) in enumerate(self.members)],
            supports = {str(k): v for k, v in self.supports.items()},
            stats  = self.stats(),
        ), indent=2)


# ═══════════════════════════════════════════════════════════════════════
#  OPENSTAAD EXPORTER  (improved property / support assignment)
# ═══════════════════════════════════════════════════════════════════════

class OpenSTAADExporter:
    """
    Definitive fix based on:
      1. Official openstaadpy HTML docs (user-provided)
      2. comtypes documentation: Python lists → VT_ARRAY|VT_VARIANT which
         some COM methods reject. Must use array.array('l', [...]) to get
         VT_ARRAY|VT_I4 (long integer SAFEARRAY) that openstaadpy accepts.
      3. Log analysis: AssignBeamProperty returns True = success (bool),
         not 0. The check was wrong.
      4. UPT ref_id from CreateUPTTableEx IS the property_no for
         AssignBeamProperty — confirmed by matching the doc example.

    SAFEARRAY FIX
    ─────────────
    openstaadpy wraps OpenSTAAD COM methods. When a method expects
    SAFEARRAY(long), passing a Python list sends VT_ARRAY|VT_VARIANT
    which the COM server rejects with SAFEARRAY_c_long.
    Solution: wrap integer lists with  array.array('l', ids)
    This makes comtypes send  VT_ARRAY|VT_I4  which matches.

    RETURN VALUE
    ────────────
    AssignBeamProperty  returns  True on success  (not int 0)
    AddUPTPropertyPRISMATIC  returns  True on success
    AssignMaterialToMember  returns  True on success
    AssignSupportToNode  returns  None  (no return value)
    CreateSupportFixed/Pinned  returns  support_no (int)
    CreateUPTTableEx  returns  ref_id (int) or 0 on failure
    """

    _SAFEARRAY_SIG = "SAFEARRAY"

    def _safe_err(self, e):
        return (self._SAFEARRAY_SIG in type(e).__name__ or
                self._SAFEARRAY_SIG in str(type(e)))

    @staticmethod
    def _iarray(ids):
        """
        Convert a list of ints to array.array('l') so comtypes sends
        VT_ARRAY|VT_I4 instead of VT_ARRAY|VT_VARIANT.
        This is the fix for SAFEARRAY_c_long errors.
        """
        import array as _array
        return _array.array('l', [int(i) for i in ids])

    def _flag(self, obj, *methods):
        for m in methods:
            try: obj._FlagAsMethod(m)
            except Exception: pass

    # ── material ─────────────────────────────────────────────────────
    def _create_material(self, prp, log, name, mat):
        self._flag(prp, "CreateIsotropicMaterialConcrete")
        try:
            ret = prp.CreateIsotropicMaterialConcrete(
                str(name), float(mat["E"]), 0.17,
                float(mat["G"]), float(mat["rho"]),
                1e-5, 0.05, float(mat["fcu"]), 0)
            ok = ret in (0, 1, True)
            if not ok: log(f"  CreateIsotropicMaterialConcrete({name}): ret={ret}")
            return ok
        except Exception as e:
            if not self._safe_err(e):
                log(f"  CreateIsotropicMaterialConcrete({name}): {e}")
            return False

    # ── UPT prismatic section creation ───────────────────────────────
    def _create_prismatic_prop(self, prp, log, ref_id, sec_name,
                                AX, J, IY, IZ, AY, AZ, YD, ZD):
        """
        CreateUPTTableEx(ref_id, 10)  →  ref_id = property_no
        AddUPTPropertyPRISMATIC(ref_id, name, AX,J,IY,IZ,AY,AZ,YD,ZD)
        Returns ref_id on success, None on failure.
        """
        self._flag(prp, "CreateUPTTableEx", "AddUPTPropertyPRISMATIC")
        try:
            result = prp.CreateUPTTableEx(int(ref_id), 10)
            if result == 0:
                log(f"  CreateUPTTableEx({ref_id}) → 0 (failed)")
                return None
            log(f"  UPT ref={ref_id} ({sec_name}): table OK  property_no={result}")
        except Exception as e:
            if not self._safe_err(e):
                log(f"  CreateUPTTableEx({ref_id}): {e}")
            return None
        try:
            ret = prp.AddUPTPropertyPRISMATIC(
                int(ref_id), str(sec_name),
                float(AX), float(J), float(IY), float(IZ),
                float(AY), float(AZ), float(YD), float(ZD))
            ok = ret in (True, 0, None)
            if not ok: log(f"  AddUPTPropertyPRISMATIC({sec_name}): ret={ret}")
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AddUPTPropertyPRISMATIC({sec_name}): {e}")
            return None
        return int(ref_id)

    # ── assign beam property ─────────────────────────────────────────
    def _assign_property(self, prp, log, property_no, mids, label):
        """
        AssignBeamProperty(beam_ids, property_no)
        Tries three forms in order:
          1. array.array('l', mids) — correct SAFEARRAY type
          2. Python list — works on some openstaadpy versions
          3. scalar loop — last resort
        True = success, 0 = success (both valid per docs).
        """
        if not mids or property_no is None:
            return
        self._flag(prp, "AssignBeamProperty")
        pno = int(property_no)

        # Form 1: array.array('l') — sends VT_ARRAY|VT_I4
        try:
            ret = prp.AssignBeamProperty(self._iarray(mids), pno)
            if ret in (True, 0, None):
                log(f"  {label}: {len(mids)} members  [array.array OK]")
                return
            log(f"  AssignBeamProperty array.array ({label}): ret={ret}")
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignBeamProperty array.array ({label}): {e}")

        # Form 2: plain Python list
        try:
            ret = prp.AssignBeamProperty(list(mids), pno)
            if ret in (True, 0, None):
                log(f"  {label}: {len(mids)} members  [list OK]")
                return
            log(f"  AssignBeamProperty list ({label}): ret={ret}")
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignBeamProperty list ({label}): {e}")

        # Form 3: scalar loop
        ok = 0
        for mid in mids:
            try:
                ret = prp.AssignBeamProperty(int(mid), pno)
                if ret in (True, 0, None):
                    ok += 1
                else:
                    codes = {-106:"array dim",-3006:"invalid member",
                             -6001:"invalid prop",-6002:"lib error"}
                    log(f"    mid {mid}: {codes.get(ret, f'ret={ret}')}")
            except Exception as e:
                if not self._safe_err(e):
                    log(f"    AssignBeamProperty({mid}): {e}")
        log(f"  {label}: {ok}/{len(mids)} assigned  [scalar loop]")

    # ── assign material ───────────────────────────────────────────────
    def _assign_material(self, prp, log, name, mids):
        """
        AssignMaterialToMember(name, member_ids)
        member_ids: try array.array('l') first, then list.
        Returns True on success.
        """
        if not mids: return
        self._flag(prp, "AssignMaterialToMember")
        # Form 1: array.array('l')
        try:
            ok = prp.AssignMaterialToMember(str(name), self._iarray(mids))
            if ok in (True, 1):
                log(f"  {name} → {len(mids)} members  [array.array OK]")
                return
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignMaterialToMember array.array ({name}): {e}")
        # Form 2: plain list
        try:
            ok = prp.AssignMaterialToMember(str(name), list(mids))
            log(f"  {name} → {len(mids)} members: {'OK' if ok else 'FAILED'}")
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignMaterialToMember ({name}): {e}")

    # ── assign support ────────────────────────────────────────────────
    def _assign_support(self, sup, log, nid, sid, stype):
        """
        AssignSupportToNode(NodeIDs, SupportID)
        Tries three forms:
          1. array.array('l', [nid]) — correct SAFEARRAY type
          2. [nid]                   — Python list
          3. nid                     — scalar int
        Returns True if any form succeeded.
        """
        self._flag(sup, "AssignSupportToNode")
        # Form 1: array.array('l') with single node
        try:
            sup.AssignSupportToNode(self._iarray([nid]), int(sid))
            return True
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignSupportToNode array.array ({stype} {nid}): {e}")

        # Form 2: Python list with single node
        try:
            sup.AssignSupportToNode([int(nid)], int(sid))
            return True
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignSupportToNode list ({stype} {nid}): {e}")

        # Form 3: scalar int
        try:
            sup.AssignSupportToNode(int(nid), int(sid))
            return True
        except Exception as e:
            if not self._safe_err(e):
                log(f"  AssignSupportToNode scalar ({stype} {nid}): {e}")

        return False

    # ── main send ────────────────────────────────────────────────────
    def send(self, model: "ConcreteBridgeModel", log_fn=None):
        def log(msg):
            if log_fn: log_fn(msg)
            print(msg)

        log("Connecting to STAAD.Pro...")
        try:
            from openstaadpy import os_analytical
            staad = os_analytical.connect()
        except Exception as e:
            raise RuntimeError(f"Cannot connect to STAAD.Pro:\n{e}")

        geo = staad.Geometry
        prp = staad.Property
        sup = staad.Support

        self._flag(geo, "CreateNode", "CreateBeam")
        self._flag(prp, "CreateIsotropicMaterialConcrete",
                   "AssignMaterialToMember", "CreateUPTTableEx",
                   "AddUPTPropertyPRISMATIC", "AssignBeamProperty")
        self._flag(sup, "CreateSupportFixed", "CreateSupportPinned",
                   "AssignSupportToNode")

        try:
            staad.SetInputUnits(4, 3)
            log("Units: METER KN")
        except Exception as e:
            log(f"SetInputUnits: {e}")

        # ── NODES ─────────────────────────────────────────────────────
        log(f"Nodes ({len(model.nodes)})...")
        for nid, (x, y, z) in model.nodes.items():
            try:
                geo.CreateNode(int(nid), float(x), float(y), float(z))
            except Exception as e:
                if not self._safe_err(e): log(f"  Node {nid}: {e}")
        staad.SaveModel(True)

        # ── MEMBERS ───────────────────────────────────────────────────
        log(f"Members ({len(model.members)})...")
        for idx, (n1, n2, _) in enumerate(model.members, 1):
            try:
                geo.CreateBeam(int(idx), int(n1), int(n2))
            except Exception as e:
                if not self._safe_err(e): log(f"  Beam {idx}: {e}")
        staad.SaveModel(True)

        # ── MATERIALS ─────────────────────────────────────────────────
        log("Creating materials...")
        p     = model.p
        mat_g = CONC_GRADES.get(p.girder_grade, list(CONC_GRADES.values())[0])
        mat_p = CONC_GRADES.get(p.pier_grade,   list(CONC_GRADES.values())[0])

        done_mats = set()
        for mat in [mat_g, mat_p]:
            if mat["name"] not in done_mats:
                ok = self._create_material(prp, log, mat["name"], mat)
                log(f"  {mat['name']}: {'OK' if ok else 'FAILED'}")
                done_mats.add(mat["name"])
        if "CONCRETE" not in done_mats:
            self._create_material(prp, log, "CONCRETE",
                                  dict(E=2.17185e7, G=9.28e6,
                                       rho=23.56, fcu=27579.0))
        staad.SaveModel(True)

        # ── SECTION PROPERTIES ────────────────────────────────────────
        log("Section properties (UPT PRISMATIC)...")
        gd    = model._gd()
        sp    = calc_section(gd)
        gir_h = gd["h"] * 1e-3

        def shear(b, d):
            v = 0.833 * b * d
            return v, v

        pids = {}

        AY_g = 0.833 * sp["bw_m"] * sp["hw_m"]
        AZ_g = 0.833 * sp["bf_top_m"] * sp["tf_top_m"]
        pids["GIRDER"] = self._create_prismatic_prop(
            prp, log, 100, "GIRDER",
            sp["A"], sp["J"], sp["Iy"], sp["Ix"],
            AY_g, AZ_g, sp["h_m"], max(sp["bf_top_m"], sp["bf_bot_m"]))

        slb = slab_section(p.deck_t, p.girder_spacing)
        AY_s, AZ_s = shear(p.girder_spacing, p.deck_t)
        pids["SLAB"] = self._create_prismatic_prop(
            prp, log, 101, "SLAB",
            slb["A"], slb["J"], slb["Iy"], slb["Ix"],
            AY_s, AZ_s, p.deck_t, p.girder_spacing)

        dph = rect_section(p.diaph_t, gir_h)
        AY_d, AZ_d = shear(p.diaph_t, gir_h)
        pids["DIAPH"] = self._create_prismatic_prop(
            prp, log, 102, "DIAPH",
            dph["A"], dph["J"], dph["Iy"], dph["Ix"],
            AY_d, AZ_d, gir_h, p.diaph_t)

        col = rect_section(p.pier_col_w, p.pier_col_w)
        AY_c, AZ_c = shear(p.pier_col_w, p.pier_col_w)
        pids["PIER_COL"] = self._create_prismatic_prop(
            prp, log, 103, "PIER_COL",
            col["A"], col["J"], col["Iy"], col["Ix"],
            AY_c, AZ_c, p.pier_col_w, p.pier_col_w)

        cap = rect_section(p.pier_cap_w, p.pier_cap_d)
        AY_p, AZ_p = shear(p.pier_cap_w, p.pier_cap_d)
        pids["PIER_CAP"] = self._create_prismatic_prop(
            prp, log, 104, "PIER_CAP",
            cap["A"], cap["J"], cap["Iy"], cap["Ix"],
            AY_p, AZ_p, p.pier_cap_d, p.pier_cap_w)

        abt = rect_section(p.abut_w, p.abut_h)
        AY_a, AZ_a = shear(p.abut_w, p.abut_h)
        pids["ABUTMENT"] = self._create_prismatic_prop(
            prp, log, 105, "ABUTMENT",
            abt["A"], abt["J"], abt["Iy"], abt["Ix"],
            AY_a, AZ_a, p.abut_h, p.abut_w)

        pids["RIGID"] = self._create_prismatic_prop(
            prp, log, 106, "RIGID",
            100.0, 50.0, 50.0, 50.0, 50.0, 50.0, 2.0, 2.0)

        staad.SaveModel(True)

        # ── ASSIGN SECTION PROPERTIES ─────────────────────────────────
        log("Assigning beam properties...")
        for sec, mids, label in [
            ("GIRDER",   model.girder_mids,   "[1] Girders"),
            ("SLAB",     model.slab_mids,     "[2] Slab strips"),
            ("DIAPH",    model.diaph_mids,    "[3] Diaphragms"),
            ("PIER_COL", model.pier_col_mids, "[4] Pier columns"),
            ("PIER_CAP", model.pier_cap_mids, "[5] Pier caps"),
            ("ABUTMENT", model.abut_mids,     "[6] Abutments"),
            ("RIGID",    model.dummy_mids,    "[7] Dummy links"),
        ]:
            if mids and pids.get(sec):
                log(f"  {label}: property_no={pids[sec]}  n={len(mids)}")
                self._assign_property(prp, log, pids[sec], mids, label)
            elif mids:
                log(f"  {label}: SKIPPED — section creation failed")

        staad.SaveModel(True)
        log("Sections complete.")

        # ── ASSIGN MATERIALS ──────────────────────────────────────────
        log("Assigning materials...")
        self._assign_material(
            prp, log, mat_g["name"],
            model.girder_mids + model.slab_mids + model.diaph_mids)
        self._assign_material(
            prp, log, mat_p["name"],
            model.pier_col_mids + model.pier_cap_mids + model.abut_mids)
        self._assign_material(prp, log, "CONCRETE", model.dummy_mids)
        staad.SaveModel(True)
        log("Materials complete.")

        # ── SUPPORTS ──────────────────────────────────────────────────
        # Uses _assign_support() which tries 3 forms:
        #   1. array.array('l', [nid])  — correct SAFEARRAY type
        #   2. [nid]                    — Python list
        #   3. scalar nid               — fallback
        log(f"Supports ({len(model.supports)} nodes)...")
        self._flag(sup, "CreateSupportFixed", "CreateSupportPinned",
                   "AssignSupportToNode")
        fixed_id  = None
        pinned_id = None
        try:
            fixed_id  = sup.CreateSupportFixed()
            pinned_id = sup.CreateSupportPinned()
            log(f"  fixed_id={fixed_id}  pinned_id={pinned_id}")
        except Exception as e:
            log(f"  CreateSupport: {e}")

        if fixed_id is not None and fixed_id >= 0:
            f_ok = p_ok = 0
            for nid, stype in model.supports.items():
                sid = fixed_id if stype == "fixed" else pinned_id
                if self._assign_support(sup, log, nid, sid, stype):
                    if stype == "fixed": f_ok += 1
                    else:                p_ok += 1
            total_f = sum(1 for t in model.supports.values() if t == "fixed")
            total_p = sum(1 for t in model.supports.values() if t == "pinned")
            log(f"  Fixed: {f_ok}/{total_f}  Pinned: {p_ok}/{total_p}")

        staad.SaveModel(True)
        log(f"Model complete — {len(model.nodes)} nodes, "
            f"{len(model.members)} members.")
        log("Open STAAD.Pro and run the analysis.")
        return len(model.nodes), len(model.members)


# ═══════════════════════════════════════════════════════════════════════
#  3-D CANVAS
# ═══════════════════════════════════════════════════════════════════════

class BridgeCanvas(tk.Canvas):
    def _clr(self, tag):
        return {
            "girder":    C["girder_c"],
            "slab":      C["deck_c"],
            "diaphragm": C["diag_c"],
            "pier_col":  C["pier_c"],
            "pier_cap":  C["cap_c"],
            "abutment":  C["abut_c"],
            "dummy":     C["dummy_c"],
        }.get(tag, C["muted"])

    def _lw(self, tag):
        return {"girder":2,"slab":1,"diaphragm":1,
                "pier_col":3,"pier_cap":2,"abutment":2,"dummy":1}.get(tag,1)

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["bg"], bd=0, highlightthickness=0, **kw)
        self.nodes    = {}
        self.members  = []
        self.supports = {}
        self._rot_x   =  0.28
        self._rot_y   = -0.42
        self._scale   =  5.0
        self._offset  = [0.0, 0.0]
        self._drag    = None
        self._show_dummy    = False
        self._show_nodes    = True
        self._show_loads    = True
        self._show_supports = True
        self._udl_val       = 25.0
        self.bind("<ButtonPress-1>", self._press)
        self.bind("<B1-Motion>",     self._orbit)
        self.bind("<ButtonPress-3>", self._press)
        self.bind("<B3-Motion>",     self._pan)
        self.bind("<MouseWheel>",    self._zoom)
        self.bind("<Button-4>",      self._zoom)
        self.bind("<Button-5>",      self._zoom)
        self.bind("<Configure>",     lambda _: self.redraw())

    def _press(self, e): self._drag = (e.x, e.y)
    def _orbit(self, e):
        if not self._drag: return
        dx = (e.x - self._drag[0]) * 0.009
        dy = (e.y - self._drag[1]) * 0.009
        self._rot_y += dx
        self._rot_x  = max(-1.4, min(1.4, self._rot_x + dy))
        self._drag   = (e.x, e.y); self.redraw()
    def _pan(self, e):
        if not self._drag: return
        self._offset[0] += e.x - self._drag[0]
        self._offset[1] += e.y - self._drag[1]
        self._drag = (e.x, e.y); self.redraw()
    def _zoom(self, e):
        d = getattr(e,"delta",0) or (-120 if e.num==5 else 120)
        self._scale = max(1.0, self._scale*(1.001**d)); self.redraw()

    def _proj(self, x, y, z):
        cy,sy = math.cos(self._rot_y), math.sin(self._rot_y)
        x2 =  cy*x + sy*z;  z2 = -sy*x + cy*z
        cx,sx = math.cos(self._rot_x), math.sin(self._rot_x)
        y2 =  cx*y - sx*z2; z3 =  sx*y + cx*z2
        fov = 480/(z3+120+1e-9)
        w = self.winfo_width() or 900; h = self.winfo_height() or 600
        return (w/2+self._offset[0]+x2*self._scale*fov/10,
                h/2+self._offset[1]-y2*self._scale*fov/10)

    def load(self, nodes, members, supports={}):
        self.nodes=nodes; self.members=members; self.supports=supports
        if nodes:
            xs=[v[0] for v in nodes.values()]
            self._scale = (self.winfo_width() or 900)*0.32/max(max(xs)-min(xs),1)
            self._offset=[0.0,0.0]
        self.redraw()

    def theme_refresh(self):
        self.config(bg=C["bg"]); self.redraw()

    def redraw(self):
        self.delete("all")
        if not self.nodes: return
        cx=sum(v[0] for v in self.nodes.values())/len(self.nodes)
        cy=sum(v[1] for v in self.nodes.values())/len(self.nodes)
        cz=sum(v[2] for v in self.nodes.values())/len(self.nodes)
        def p(nid):
            x,y,z=self.nodes[nid]; return self._proj(x-cx,y-cy,z-cz)
        def depth(m):
            return -(self.nodes[m[0]][2]+self.nodes[m[1]][2])/2

        w = self.winfo_width() or 900
        _,py0 = self._proj(0,-cy,0)
        self.create_line(0,py0+38,w,py0+38,fill=C["border"],dash=(8,14),width=1)

        for (n1,n2,tag) in sorted(self.members, key=depth):
            if tag=="dummy" and not self._show_dummy: continue
            clr=self._clr(tag); lw=self._lw(tag)
            dash=(4,5) if tag=="dummy" else ()
            self.create_line(*p(n1),*p(n2),fill=clr,width=lw,capstyle="round",dash=dash)

        if self._show_nodes:
            sup_set=set(self.supports.keys())
            for nid,(x,y,z) in self.nodes.items():
                px,py=self._proj(x-cx,y-cy,z-cz)
                r=4 if nid in sup_set else 2
                clr=C["support_c"] if nid in sup_set else C["muted"]
                self.create_oval(px-r,py-r,px+r,py+r,fill=clr,outline="")

        if self._show_supports:
            for nid,stype in self.supports.items():
                if nid in self.nodes:
                    px,py=p(nid)
                    if stype=="fixed": self._draw_fixed((px,py))
                    else: self._draw_pin((px,py))

        if self._show_loads and self._udl_val>0:
            max_y=max(v[1] for v in self.nodes.values())
            for nid,(x,y,z) in self.nodes.items():
                if abs(y-max_y)<0.05:
                    self._draw_arrow(self._proj(x-cx,y-cy,z-cz))

    def _draw_pin(self, pos):
        px,py=pos; s=9
        self.create_polygon([px,py,px-s,py+s*1.6,px+s,py+s*1.6],
                            fill="",outline=C["support_c"],width=1)
        self.create_line(px-s*1.3,py+s*1.7,px+s*1.3,py+s*1.7,fill=C["muted"],width=1)

    def _draw_fixed(self, pos):
        px,py=pos; s=9
        self.create_rectangle(px-s,py,px+s,py+s*1.8,
                              fill="",outline=C["support_c"],width=1)
        for xi in range(-s,s+1,4):
            self.create_line(px+xi,py+s*1.8,px+xi-4,py+s*2.4,
                            fill=C["muted"],width=1)

    def _draw_arrow(self, pos):
        px,py=pos
        self.create_line(px,py-14,px,py,fill=C["load_c"],
                        width=1,arrow="last",arrowshape=(5,7,3))


# ═══════════════════════════════════════════════════════════════════════
#  UI HELPERS
# ═══════════════════════════════════════════════════════════════════════

class ScrollFrame(tk.Frame):
    """Self-contained scrollable frame that tracks the active C palette."""
    def __init__(self, parent, **kw):
        outer = tk.Frame(parent, bg=C["panel"])
        outer.pack(fill="both", expand=True)
        self._cv = tk.Canvas(outer, bg=C["panel"], highlightthickness=0, bd=0)
        sb = tk.Scrollbar(outer, orient="vertical", command=self._cv.yview,
                          width=5, troughcolor=C["border"], bg=C["panel"])
        self._cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._cv.pack(side="left", fill="both", expand=True)
        super().__init__(self._cv, bg=C["panel"], **kw)
        win = self._cv.create_window((0,0), window=self, anchor="nw")
        def _r(e):
            self._cv.configure(scrollregion=self._cv.bbox("all"))
            self._cv.itemconfig(win, width=self._cv.winfo_width())
        self.bind("<Configure>", _r)
        self._cv.bind_all("<MouseWheel>",
            lambda e: self._cv.yview_scroll(int(-1*(e.delta/120)),"units"))


def _sec(parent, title):
    fr = tk.Frame(parent, bg=C["panel"])
    fr.pack(fill="x", padx=12, pady=(11,2))
    tk.Label(fr, text=title, font=FONTS.get("sec",""), bg=C["panel"],
             fg=C["muted"]).pack(side="left")
    tk.Frame(fr, bg=C["border"], height=1).pack(
        side="left", fill="x", expand=True, padx=(8,0))


# ═══════════════════════════════════════════════════════════════════════
#  LABEL + ENTRY ROW  (replaces sliders for numeric input)
# ═══════════════════════════════════════════════════════════════════════

class LabelEntry:
    """
    A compact label + entry + unit row.
    var  : tk.DoubleVar or tk.IntVar
    callback: called on FocusOut / Return
    """
    def __init__(self, parent, label, var, unit="", callback=None, width=8):
        fr = tk.Frame(parent, bg=C["panel"])
        fr.pack(fill="x", padx=12, pady=2)
        tk.Label(fr, text=label.upper(), font=FONTS.get("sec",""),
                 bg=C["panel"], fg=C["muted"],
                 width=22, anchor="w").pack(side="left")
        self._e = tk.Entry(fr, textvariable=var, font=FONTS.get("mono_sm",""),
                           bg=C["entry_bg"], fg=C["accent"],
                           insertbackground=C["accent"],
                           relief="flat", bd=2,
                           highlightthickness=1,
                           highlightcolor=C["accent2"],
                           highlightbackground=C["border"],
                           width=width)
        self._e.pack(side="left", padx=(0,4))
        tk.Label(fr, text=unit, font=FONTS.get("sec",""),
                 bg=C["panel"], fg=C["muted"]).pack(side="left")
        if callback:
            self._e.bind("<Return>",   lambda _: callback())
            self._e.bind("<FocusOut>", lambda _: callback())
        self.frame = fr

    def theme_refresh(self):
        self.frame.config(bg=C["panel"])
        self._e.config(bg=C["entry_bg"], fg=C["accent"],
                       insertbackground=C["accent"],
                       highlightcolor=C["accent2"],
                       highlightbackground=C["border"])


class LabelCombo:
    """Label + OptionMenu row."""
    def __init__(self, parent, label, var, options, callback=None):
        fr = tk.Frame(parent, bg=C["panel"])
        fr.pack(fill="x", padx=12, pady=2)
        tk.Label(fr, text=label.upper(), font=FONTS.get("sec",""),
                 bg=C["panel"], fg=C["muted"],
                 width=22, anchor="w").pack(side="left")
        def _cb(*_):
            if callback: callback()
        menu = tk.OptionMenu(fr, var, *options, command=_cb)
        menu.config(bg=C["entry_bg"], fg=C["text"], bd=0,
                    highlightthickness=0, font=FONTS.get("label",""),
                    activebackground=C["bl2"], activeforeground=C["text"],
                    relief="flat")
        menu["menu"].config(bg=C["entry_bg"], fg=C["text"],
                            activebackground=C["accent"],
                            activeforeground=C["bg"])
        menu.pack(side="left", fill="x", expand=True)
        self.frame = fr
        self.menu  = menu

    def theme_refresh(self):
        self.frame.config(bg=C["panel"])
        self.menu.config(bg=C["entry_bg"], fg=C["text"])
        self.menu["menu"].config(bg=C["entry_bg"], fg=C["text"])


# ═══════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════

class BridgeLab:

    def __init__(self):
        self.model    = ConcreteBridgeModel()
        self.exporter = OpenSTAADExporter()
        self._theme   = "dark"
        self._all_widgets = []   # for bulk theme refresh

        self.root = tk.Tk()
        self.root.title("BRIDGELAB v4 — Concrete Bridge Modeler")
        self.root.geometry("1640x950")
        self.root.configure(bg=C["bg"])
        self.root.minsize(1100, 700)

        self._make_fonts()
        self._build_ui()
        self._rebuild()
        self.root.mainloop()

    # ── fonts ────────────────────────────────────────────────────────────
    def _make_fonts(self):
        FONTS["title"]   = tkfont.Font(family="Courier New", size=12, weight="bold")
        FONTS["label"]   = tkfont.Font(family="Helvetica",   size=9)
        FONTS["mono"]    = tkfont.Font(family="Courier New", size=10, weight="bold")
        FONTS["mono_sm"] = tkfont.Font(family="Courier New", size=8)
        FONTS["big"]     = tkfont.Font(family="Courier New", size=14, weight="bold")
        FONTS["sec"]     = tkfont.Font(family="Helvetica",   size=8,  weight="bold")
        FONTS["btn"]     = tkfont.Font(family="Helvetica",   size=9,  weight="bold")
        FONTS["code"]    = tkfont.Font(family="Courier New", size=8)

    # ── theme toggle ─────────────────────────────────────────────────────
    def _toggle_theme(self):
        self._theme = "light" if self._theme == "dark" else "dark"
        apply_theme(self._theme)
        # Refresh whole window
        self._full_theme_refresh(self.root)
        # Update canvas colours
        self.canvas.theme_refresh()
        lbl = "☀ Light" if self._theme == "dark" else "🌙 Dark"
        self._theme_btn.config(text=lbl,
                               bg=C["bl2"], fg=C["text"],
                               activebackground=C["border"])

    def _full_theme_refresh(self, widget):
        bg_map = {
            "Frame": "panel", "Canvas": "panel", "Label": "panel",
            "Toplevel": "bg", "Tk": "bg",
            "Scrollbar": "panel", "Text": "bg", "Entry": "entry_bg",
        }
        wtype = type(widget).__name__
        key   = bg_map.get(wtype, None)
        if key:
            try: widget.config(bg=C[key])
            except Exception: pass
        if wtype == "Label":
            try:
                curr_fg = widget.cget("fg")
                # Re-map known fg values
                for theme_key, val in THEMES["dark"].items():
                    if curr_fg == val:
                        widget.config(fg=C[theme_key])
                        break
                    opp = THEMES["light"][theme_key]
                    if curr_fg == opp:
                        widget.config(fg=C[theme_key])
                        break
            except Exception: pass
        for child in widget.winfo_children():
            self._full_theme_refresh(child)

    # ── helpers ───────────────────────────────────────────────────────────
    def _btn(self, parent, text, cmd, accent=False, danger=False, **kw):
        bg  = C["accent"] if accent else (C["accent3"] if danger else C["bl2"])
        fg  = C["bg"]     if accent else C["text"]
        hov = "#c88800"   if accent else ("#b03030" if danger else C["border"])
        return tk.Button(parent, text=text, command=cmd,
                         font=FONTS["btn"], bg=bg, fg=fg,
                         activebackground=hov, activeforeground=fg,
                         bd=0, relief="flat", padx=8, pady=7,
                         cursor="hand2", **kw)

    def _hdr(self, parent, label, value):
        fr = tk.Frame(parent, bg=C["panel"])
        fr.pack(side="left", padx=8)
        tk.Label(fr, text=label+":", font=FONTS["mono_sm"],
                 bg=C["panel"], fg=C["muted"]).pack(side="left")
        var = tk.StringVar(value=value)
        tk.Label(fr, textvariable=var, font=FONTS["mono_sm"],
                 bg=C["panel"], fg=C["text"]).pack(side="left", padx=(2,0))
        return var

    def _ent(self, parent, label, var, unit="", cb=None, w=8):
        return LabelEntry(parent, label, var, unit,
                          callback=cb or self._rebuild, width=w)

    def _cmb(self, parent, label, var, opts, cb=None):
        return LabelCombo(parent, label, var, opts,
                          callback=cb or self._rebuild)

    # ── BUILD UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        self._topbar()
        main = tk.Frame(self.root, bg=C["bg"])
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=C["panel"], width=320)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        self._build_left(left)

        canvas_fr = tk.Frame(main, bg=C["bg"])
        canvas_fr.pack(side="left", fill="both", expand=True)
        self._build_canvas(canvas_fr)

        right = tk.Frame(main, bg=C["panel"], width=370)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)
        self._build_right(right)

    # ── TOP BAR ───────────────────────────────────────────────────────────
    def _topbar(self):
        bar = tk.Frame(self.root, bg=C["panel"], height=48)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        tk.Label(bar, text="BRIDGELAB", font=FONTS["title"],
                 bg=C["panel"], fg=C["accent"]).pack(side="left", padx=16, pady=10)
        tk.Label(bar, text="v4 · Concrete Grillage",
                 font=FONTS["mono_sm"], bg=C["panel"],
                 fg=C["muted"]).pack(side="left")
        tk.Frame(bar, bg=C["border"], width=1).pack(
            side="left", fill="y", padx=10, pady=8)

        self.hdr_type    = self._hdr(bar, "Girder",   "Type III")
        self.hdr_spans   = self._hdr(bar, "Spans",    "3×15m")
        self.hdr_nodes   = self._hdr(bar, "Nodes",    "-")
        self.hdr_members = self._hdr(bar, "Members",  "-")
        self.hdr_width   = self._hdr(bar, "Width",    "-m")
        self.hdr_mass    = self._hdr(bar, "Mass",     "-t")

        # Theme toggle button
        self._theme_btn = tk.Button(bar, text="☀ Light",
                                    command=self._toggle_theme,
                                    font=FONTS["btn"],
                                    bg=C["bl2"], fg=C["text"],
                                    activebackground=C["border"],
                                    bd=0, relief="flat", padx=10, pady=6,
                                    cursor="hand2")
        self._theme_btn.pack(side="right", padx=12)

        dot = tk.Canvas(bar, width=8, height=8, bg=C["panel"],
                        highlightthickness=0)
        dot.pack(side="right", padx=(0,4))
        dot.create_oval(1,1,7,7, fill=C["green"], outline="")
        tk.Label(bar, text="LIVE", font=FONTS["mono_sm"],
                 bg=C["panel"], fg=C["muted"]).pack(side="right", padx=(0,6))

    # ── LEFT PANEL ────────────────────────────────────────────────────────
    def _build_left(self, parent):
        sf = ScrollFrame(parent)
        p  = self.model.p

        # ── Spans ───────────────────────────────────────────────────
        _sec(sf, "SPAN CONFIGURATION")
        self.v_nspans = tk.IntVar(value=p.n_spans)
        self._ent(sf, "No. of Spans", self.v_nspans, "", self._on_nspans_change, w=4)

        self._span_box = tk.Frame(sf, bg=C["panel"])
        self._span_box.pack(fill="x", padx=12, pady=2)
        self._span_vars = []
        self._build_span_entries()

        # ── Cross-section ────────────────────────────────────────────
        _sec(sf, "CROSS-SECTION")
        self.v_ngird = tk.IntVar(value=p.n_girders)
        self.v_gsp   = tk.DoubleVar(value=p.girder_spacing)
        self.v_ovhg  = tk.DoubleVar(value=p.overhang)
        self.v_deckt = tk.DoubleVar(value=p.deck_t)
        self._ent(sf, "No. of Girders",    self.v_ngird, "")
        self._ent(sf, "Girder Spacing",    self.v_gsp,   "m")
        self._ent(sf, "Deck Overhang",     self.v_ovhg,  "m")
        self._ent(sf, "Slab Thickness",    self.v_deckt, "m")

        # ── Girder Section ───────────────────────────────────────────
        _sec(sf, "GIRDER TYPE  (AASHTO / DPWH)")
        self.v_gtype = tk.StringVar(value=p.girder_type)
        self._cmb(sf, "Section", self.v_gtype,
                  list(GIRDER_DB.keys()), cb=self._on_girder_change)

        # Info label
        self._ginfo = tk.Label(sf, text="", font=FONTS["mono_sm"],
                               bg=C["bg"], fg=C["accent2"],
                               justify="left", anchor="w", wraplength=270)
        self._ginfo.pack(fill="x", padx=12, pady=2)

        # Custom section inputs (hidden unless Custom selected)
        self._cust_frame = tk.Frame(sf, bg=C["panel"])
        self.v_ch    = tk.DoubleVar(value=p.cust_h)
        self.v_cbft  = tk.DoubleVar(value=p.cust_bf_top)
        self.v_ctft  = tk.DoubleVar(value=p.cust_tf_top)
        self.v_cbw   = tk.DoubleVar(value=p.cust_bw)
        self.v_chw   = tk.DoubleVar(value=p.cust_hw)
        self.v_cbfb  = tk.DoubleVar(value=p.cust_bf_bot)
        self.v_ctfb  = tk.DoubleVar(value=p.cust_tf_bot)
        for label, var in [
            ("Total Depth h (mm)",   self.v_ch),
            ("Top Flange Width (mm)",self.v_cbft),
            ("Top Flange t (mm)",    self.v_ctft),
            ("Web Width bw (mm)",    self.v_cbw),
            ("Web Height hw (mm)",   self.v_chw),
            ("Bot Flange Width (mm)",self.v_cbfb),
            ("Bot Flange t (mm)",    self.v_ctfb),
        ]:
            LabelEntry(self._cust_frame, label, var, "mm",
                       callback=self._rebuild, width=7)
        # Custom dim inputs — NOT calling _on_girder_change yet
        # (pier/support/grade vars not created yet; called at end of _build_left)

        # ── Pier / Abutment ──────────────────────────────────────────
        _sec(sf, "PIER & ABUTMENT")
        self.v_ptype  = tk.StringVar(value=p.pier_type)
        self.v_ph     = tk.DoubleVar(value=p.pier_height)
        self.v_pcw    = tk.DoubleVar(value=p.pier_col_w)
        self.v_pcd    = tk.DoubleVar(value=p.pier_cap_d)
        self.v_pcwid  = tk.DoubleVar(value=p.pier_cap_w)
        self.v_ah     = tk.DoubleVar(value=p.abut_h)
        self.v_aw     = tk.DoubleVar(value=p.abut_w)
        self.v_dt     = tk.DoubleVar(value=p.diaph_t)
        self._cmb(sf, "Pier Type",        self.v_ptype,  PIER_TYPES)
        self._ent(sf, "Pier Height",      self.v_ph,     "m")
        self._ent(sf, "Column Width",     self.v_pcw,    "m")
        self._ent(sf, "Cap Beam Depth",   self.v_pcd,    "m")
        self._ent(sf, "Cap Beam Width",   self.v_pcwid,  "m")
        self._ent(sf, "Abutment Stem h",  self.v_ah,     "m")
        self._ent(sf, "Abutment Stem w",  self.v_aw,     "m")
        self._ent(sf, "Diaphragm thk",    self.v_dt,     "m")

        # ── End Conditions ───────────────────────────────────────────
        _sec(sf, "END CONDITIONS")
        self.v_abut_sup  = tk.StringVar(value=p.abut_support)
        self.v_pier_sup  = tk.StringVar(value=p.pier_support)
        self._cmb(sf, "Abutment Support", self.v_abut_sup, SUPPORT_OPTS)
        self._cmb(sf, "Pier Support",     self.v_pier_sup, SUPPORT_OPTS)

        # ── Concrete Grades ──────────────────────────────────────────
        _sec(sf, "CONCRETE GRADES")
        self.v_ggrade = tk.StringVar(value=p.girder_grade)
        self.v_sgrade = tk.StringVar(value=p.slab_grade)
        self.v_pgrade = tk.StringVar(value=p.pier_grade)
        gl = list(CONC_GRADES.keys())
        self._cmb(sf, "Girder Concrete",  self.v_ggrade, gl)
        self._cmb(sf, "Deck Slab Conc.",  self.v_sgrade, gl)
        self._cmb(sf, "Pier Concrete",    self.v_pgrade, gl)

        # ── Display ──────────────────────────────────────────────────
        _sec(sf, "DISPLAY OPTIONS")
        disp = tk.Frame(sf, bg=C["panel"])
        disp.pack(fill="x", padx=12, pady=4)
        self._tog = {}
        for lbl, key, default in [
            ("Show Nodes",        "nodes",    True),
            ("Show Load Arrows",  "loads",    True),
            ("Show Supports",     "supports", True),
            ("Show Dummy Links",  "dummy",    False),
        ]:
            row = tk.Frame(disp, bg=C["panel"])
            row.pack(fill="x", pady=2)
            var = tk.BooleanVar(value=default)
            self._tog[key] = var
            tk.Label(row, text=lbl, font=FONTS["label"],
                     bg=C["panel"], fg=C["text"]).pack(side="left")
            tk.Checkbutton(row, variable=var,
                           bg=C["panel"], fg=C["accent"],
                           selectcolor=C["entry_bg"],
                           activebackground=C["panel"],
                           command=self._apply_display).pack(side="right")

        # ── Summary ──────────────────────────────────────────────────
        _sec(sf, "MODEL SUMMARY")
        sg = tk.Frame(sf, bg=C["panel"])
        sg.pack(fill="x", padx=12, pady=6)
        self._stat = {}
        for i, (lbl, key) in enumerate([
            ("Nodes","nodes"), ("Members","members"),
            ("Mass (t)","mass_t"), ("Length (m)","total_L"),
            ("Width (m)","width"), ("Spans","spans"),
        ]):
            col,row = i%2, i//2
            card = tk.Frame(sg, bg=C["bg"])
            card.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
            sg.columnconfigure(col, weight=1)
            tk.Label(card, text=lbl.upper(), font=FONTS["sec"],
                     bg=C["bg"], fg=C["muted"]).pack(anchor="w",padx=6,pady=(4,0))
            lbl2 = tk.Label(card, text="-", font=FONTS["big"],
                            bg=C["bg"], fg=C["text"])
            lbl2.pack(anchor="w",padx=6,pady=(0,4))
            self._stat[key] = lbl2

        # ── All vars now created — safe to do initial girder setup ────
        self._on_girder_change()   # updates info label, custom frame, calls _rebuild

        # Bottom buttons
        btn_bar = tk.Frame(parent, bg=C["panel"])
        btn_bar.pack(side="bottom", fill="x", padx=10, pady=10)
        self._btn(btn_bar, "↺ Reset View",
                  self._reset_view).pack(side="left",fill="x",expand=True,padx=(0,4))
        self._btn(btn_bar, "=> SEND TO STAAD",
                  self._send_staad, accent=True).pack(side="left",fill="x",expand=True)

    # ── Span entry builder ────────────────────────────────────────────────
    def _build_span_entries(self):
        for w in self._span_box.winfo_children(): w.destroy()
        self._span_vars.clear()
        n = max(1, int(self.v_nspans.get())) if hasattr(self,"v_nspans") else 3
        tk.Label(self._span_box, text="SPAN LENGTHS (m)",
                 font=FONTS["sec"], bg=C["panel"],
                 fg=C["muted"]).grid(row=0,column=0,columnspan=n,sticky="w",pady=(2,4))
        for i in range(n):
            var = tk.DoubleVar(value=15.0)
            tk.Label(self._span_box, text=f"S{i+1}",
                     font=FONTS["sec"],bg=C["panel"],fg=C["muted"]).grid(row=1,column=i,padx=2)
            e = tk.Entry(self._span_box, textvariable=var,
                         font=FONTS["mono_sm"], bg=C["entry_bg"],
                         fg=C["accent"], bd=0,
                         highlightthickness=1,
                         highlightcolor=C["accent2"],
                         highlightbackground=C["border"],
                         relief="flat", width=5,
                         insertbackground=C["accent"])
            e.grid(row=2, column=i, padx=2, pady=2)
            e.bind("<Return>",   lambda _: self._rebuild())
            e.bind("<FocusOut>", lambda _: self._rebuild())
            self._span_box.columnconfigure(i, weight=1)
            self._span_vars.append(var)

    def _on_nspans_change(self):
        self._build_span_entries()
        if hasattr(self, "v_ptype"):   # only rebuild when fully initialised
            self._rebuild()

    def _on_girder_change(self):
        t = self.v_gtype.get() if hasattr(self, "v_gtype") else "AASHTO Type III"
        gd = GIRDER_DB.get(t, GIRDER_DB["AASHTO Type III"])
        sp = calc_section(gd)
        info = (f"h={gd['h']}mm  A={sp['A']*1e4:.0f}cm²  "
                f"Ix={sp['Ix']*1e8:.1f}cm⁴  yb={sp['yb']*1e3:.0f}mm\n"
                f"{gd.get('desc','')}")
        try: self._ginfo.config(text=info)
        except Exception: pass
        # Show/hide custom dim entry panel
        if hasattr(self, "_cust_frame"):
            if t == "Custom (User)":
                self._cust_frame.pack(fill="x", padx=12, pady=4)
            else:
                self._cust_frame.pack_forget()
        # Update section sketch if canvas already built
        try: self._draw_girder_sketch()
        except Exception: pass
        # Full rebuild (guarded internally)
        self._rebuild()

    # ── CANVAS ────────────────────────────────────────────────────────────
    def _build_canvas(self, parent):
        self.canvas = BridgeCanvas(parent)
        self.canvas.pack(fill="both", expand=True)

        # HUD bottom-left
        hud = tk.Frame(parent, bg="", highlightthickness=0)
        hud.place(relx=0.0, rely=1.0, anchor="sw", x=10, y=-10)
        self._hud = {}
        for lbl, key, init in [
            ("DC",   "dc",   "198.6 kN/m"),
            ("DW",   "dw",   "10.0 kN/m"),
            ("Lane", "lane", "18.7 kN/m"),
        ]:
            card = tk.Frame(hud, bg=C["panel"])
            card.pack(side="left", padx=3)
            tk.Label(card, text=lbl, font=FONTS["sec"],
                     bg=C["panel"], fg=C["muted"]).pack(anchor="w", padx=7, pady=(4,0))
            l = tk.Label(card, text=init, font=FONTS["mono"],
                         bg=C["panel"], fg=C["accent2"])
            l.pack(anchor="w", padx=7, pady=(0,4))
            self._hud[key] = l

        # Legend top-right
        leg = tk.Frame(parent, bg=C["panel"])
        leg.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        tk.Label(leg, text="ELEMENT LEGEND", font=FONTS["sec"],
                 bg=C["panel"], fg=C["muted"]).pack(anchor="w",padx=10,pady=(7,3))
        for lbl, clr_key in [
            ("Girder (I-Section)",  "girder_c"),
            ("Deck Slab Strip",     "deck_c"),
            ("Diaphragm",           "diag_c"),
            ("Pier Column",         "pier_c"),
            ("Pier Cap Beam",       "cap_c"),
            ("Abutment Stem",       "abut_c"),
            ("Dummy (rigid link)",  "dummy_c"),
        ]:
            row = tk.Frame(leg, bg=C["panel"])
            row.pack(fill="x", padx=10, pady=1)
            cv2 = tk.Canvas(row, width=22, height=4,
                            bg=C["panel"], highlightthickness=0)
            cv2.pack(side="left")
            cv2.create_line(0,2,22,2, fill=C[clr_key], width=3)
            tk.Label(row, text=lbl, font=FONTS["sec"],
                     bg=C["panel"], fg=C["text"]).pack(side="left", padx=4)
        tk.Label(leg, text="▲=pinned  ▬=fixed  ↓=DC load",
                 font=FONTS["sec"], bg=C["panel"],
                 fg=C["muted"]).pack(anchor="w",padx=10,pady=(4,7))

        # Girder cross-section sketch
        self._sec_cv = tk.Canvas(parent, bg=C["panel"],
                                 width=140, height=130,
                                 highlightthickness=1,
                                 highlightbackground=C["border"])
        self._sec_cv.place(relx=0.0, rely=0.0, anchor="nw", x=10, y=10)
        self._draw_girder_sketch()

        tk.Label(parent,
                 text="L-drag: orbit   R-drag: pan   Scroll: zoom",
                 font=FONTS["mono_sm"], bg=C["bg"],
                 fg=C["muted"]).place(relx=1.0,rely=1.0,anchor="se",x=-12,y=-12)

    def _draw_girder_sketch(self):
        cv = self._sec_cv
        cv.delete("all")
        cv.config(bg=C["panel"], highlightbackground=C["border"])
        t  = self.v_gtype.get() if hasattr(self,"v_gtype") else "AASHTO Type III"
        gd = dict(GIRDER_DB.get(t, GIRDER_DB["AASHTO Type III"]))
        if t == "Custom (User)":
            gd.update(h=self.v_ch.get(), bf_top=self.v_cbft.get(),
                      tf_top=self.v_ctft.get(), bw=self.v_cbw.get(),
                      hw=self.v_chw.get(), bf_bot=self.v_cbfb.get(),
                      tf_bot=self.v_ctfb.get())
        W,H = 140,130
        scale = min(88/gd["h"], 100/max(gd["bf_bot"],gd["bf_top"]))
        cx = W//2; top = 10
        h=gd["h"]*scale; bf_t=gd["bf_top"]*scale; tf_t=gd["tf_top"]*scale
        bw=gd["bw"]*scale; hw=gd["hw"]*scale
        bf_b=gd["bf_bot"]*scale; tf_b=gd["tf_bot"]*scale
        pts=[cx-bf_t/2,top,  cx+bf_t/2,top,
             cx+bf_t/2,top+tf_t,  cx+bw/2,top+tf_t,
             cx+bw/2,top+tf_t+hw,  cx+bf_b/2,top+tf_t+hw,
             cx+bf_b/2,top+h,  cx-bf_b/2,top+h,
             cx-bf_b/2,top+tf_t+hw,  cx-bw/2,top+tf_t+hw,
             cx-bw/2,top+tf_t,  cx-bf_t/2,top+tf_t]
        cv.create_polygon(pts,fill=C["bl2"],outline=C["girder_c"],width=1)
        cv.create_text(cx,H-10,text=t.replace("AASHTO ",""),
                       font=FONTS["sec"],fill=C["accent2"])
        cv.create_text(W-5,top+h/2,text=f"{int(gd['h'])}mm",
                       font=FONTS["sec"],fill=C["muted"],anchor="e")

    # ── RIGHT PANEL ───────────────────────────────────────────────────────
    def _build_right(self, parent):
        tab_bar = tk.Frame(parent, bg=C["panel2"])
        tab_bar.pack(fill="x")
        self._tab_btns   = {}
        self._tab_frames = {}
        content = tk.Frame(parent, bg=C["panel"])
        content.pack(fill="both", expand=True)

        for t in ["Loads", "Sections", "Export", "Log"]:
            b = tk.Button(tab_bar, text=t, font=FONTS["sec"],
                          bg=C["panel2"], fg=C["muted"],
                          bd=0, relief="flat", padx=12, pady=10,
                          activebackground=C["bl2"], cursor="hand2",
                          command=lambda x=t: self._show_tab(x))
            b.pack(side="left")
            self._tab_btns[t] = b

        self._tab_frames["Loads"]    = self._tab_loads(content)
        self._tab_frames["Sections"] = self._tab_sections(content)
        self._tab_frames["Export"]   = self._tab_export(content)
        self._tab_frames["Log"]      = self._tab_log(content)
        self._show_tab("Loads")

    def _show_tab(self, name):
        for f in self._tab_frames.values(): f.pack_forget()
        self._tab_frames[name].pack(fill="both", expand=True)
        for t,b in self._tab_btns.items():
            b.config(bg=C["accent"] if t==name else C["panel2"],
                     fg=C["bg"]     if t==name else C["muted"])

    # ── TAB: LOADS ────────────────────────────────────────────────────────
    def _tab_loads(self, parent):
        fr = tk.Frame(parent, bg=C["panel"])
        p  = self.model.p

        _sec(fr, "DEAD LOADS  (AASHTO LRFD)")
        self.v_dc   = tk.DoubleVar(value=p.dc_load)
        self.v_dw   = tk.DoubleVar(value=p.dw_load)
        self.v_pl   = tk.DoubleVar(value=p.pl_load)
        self._ent(fr, "DC (barriers+SW)", self.v_dc,  "kN/m")
        self._ent(fr, "DW (wearing surf)", self.v_dw, "kN/m")
        self._ent(fr, "PL (pedestrian)",  self.v_pl,  "kN/m")

        _sec(fr, "LIVE LOADS  (HL-93)")
        self.v_lane   = tk.DoubleVar(value=p.lane_load)
        self.v_nlanes = tk.IntVar(value=p.n_lanes)
        self._ent(fr, "Design Lane UDL",   self.v_lane,   "kN/m")
        self._ent(fr, "No. Design Lanes",  self.v_nlanes, "")

        _sec(fr, "AASHTO DESIGN TRUCK AXLES")
        self.v_ax1  = tk.DoubleVar(value=p.truck_ax1)
        self.v_ax2  = tk.DoubleVar(value=p.truck_ax2)
        self.v_ax3  = tk.DoubleVar(value=p.truck_ax3)
        self.v_sp12 = tk.DoubleVar(value=p.truck_sp12)
        self.v_sp23 = tk.DoubleVar(value=p.truck_sp23)
        self._ent(fr, "Front Axle",    self.v_ax1,  "kN")
        self._ent(fr, "Drive Axle",    self.v_ax2,  "kN")
        self._ent(fr, "Rear Axle",     self.v_ax3,  "kN")
        self._ent(fr, "Spacing 1-2",   self.v_sp12, "m")
        self._ent(fr, "Spacing 2-3",   self.v_sp23, "m")

        _sec(fr, "SEISMIC")
        self.v_seismic = tk.BooleanVar(value=p.include_seismic)
        row = tk.Frame(fr, bg=C["panel"])
        row.pack(fill="x", padx=12, pady=3)
        tk.Label(row, text="INCLUDE EQ LOAD CASE",
                 font=FONTS["sec"], bg=C["panel"],
                 fg=C["text"]).pack(side="left")
        tk.Checkbutton(row, variable=self.v_seismic,
                       bg=C["panel"], fg=C["accent"],
                       selectcolor=C["entry_bg"],
                       activebackground=C["panel"],
                       command=self._rebuild).pack(side="right")

        self._btn(fr, "✔  Apply Loads",
                  self._apply_loads, accent=True).pack(fill="x",padx=12,pady=8)

        _sec(fr, "LOAD CASES SUMMARY")
        self._lc_txt = tk.Text(fr, font=FONTS["code"], bg=C["entry_bg"],
                               fg=C["accent2"], bd=0, height=9, wrap="word",
                               state="disabled")
        self._lc_txt.pack(fill="x", padx=12, pady=4)
        return fr

    def _apply_loads(self):
        p = self.model.p
        p.dc_load       = float(self.v_dc.get())
        p.dw_load       = float(self.v_dw.get())
        p.pl_load       = float(self.v_pl.get())
        p.lane_load     = float(self.v_lane.get())
        p.n_lanes       = int(self.v_nlanes.get())
        p.truck_ax1     = float(self.v_ax1.get())
        p.truck_ax2     = float(self.v_ax2.get())
        p.truck_ax3     = float(self.v_ax3.get())
        p.truck_sp12    = float(self.v_sp12.get())
        p.truck_sp23    = float(self.v_sp23.get())
        p.include_seismic = bool(self.v_seismic.get())
        self._hud["dc"].config(text=f"{p.dc_load:.1f} kN/m")
        self._hud["dw"].config(text=f"{p.dw_load:.2f} kN/m")
        self._hud["lane"].config(text=f"{p.lane_load:.2f} kN/m")
        self._refresh_lc()
        self._log("Load parameters applied.")

    def _refresh_lc(self):
        p = self.model.p
        lines = [
            f" LC 1  DC    {p.dc_load:.2f} kN/m  (barriers + SW)",
            f" LC 2  DW    {p.dw_load:.2f} kN/m  (wearing surface)",
            f" LC 3  PL    {p.pl_load:.2f} kN/m  (pedestrian)",
        ]
        for i in range(p.n_lanes):
            lines.append(f" LC {4+i}  LANE {i+1}  {p.lane_load:.2f} kN/m")
        for i in range(p.n_spans):
            lines.append(f" LC {4+p.n_lanes+i}  TRUCK Span {i+1}  (90% HL-93)")
        if p.include_seismic:
            lines.append(f" LC {4+p.n_lanes+p.n_spans}  EQ-X  (CQC spectrum)")
        lines.append(f"\n Total: {len(lines)} load cases")
        self._lc_txt.config(state="normal")
        self._lc_txt.delete("1.0","end")
        self._lc_txt.insert("end","\n".join(lines))
        self._lc_txt.config(state="disabled")

    # ── TAB: SECTIONS ─────────────────────────────────────────────────────
    def _tab_sections(self, parent):
        fr = tk.Frame(parent, bg=C["panel"])

        _sec(fr, "COMPUTED SECTION PROPERTIES")
        self._sec_txt = tk.Text(fr, font=FONTS["code"], bg=C["entry_bg"],
                                fg=C["text"], bd=0, height=22, wrap="none",
                                state="disabled")
        ys = tk.Scrollbar(fr, orient="vertical", command=self._sec_txt.yview,
                          width=5, troughcolor=C["border"], bg=C["panel"])
        self._sec_txt.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self._sec_txt.pack(fill="both", expand=True, padx=10, pady=4)

        self._btn(fr, "↻ Refresh",
                  self._refresh_sections).pack(fill="x",padx=12,pady=4)
        return fr

    def _refresh_sections(self):
        p  = self.model.p
        gd = self.model._gd()
        sp = calc_section(gd)
        slb= slab_section(p.deck_t, p.girder_spacing)
        col= rect_section(p.pier_col_w, p.pier_col_w)
        cap= rect_section(p.pier_cap_w, p.pier_cap_d)
        abt= rect_section(p.abut_w, p.abut_h)
        dph= rect_section(p.diaph_t, gd["h"]*1e-3)

        lines = [
            f"{'='*46}",
            f" AASHTO {p.girder_type}",
            f"{'='*46}",
            f"  Total depth h    = {gd['h']} mm",
            f"  Top flange       = {gd['bf_top']} × {gd['tf_top']} mm",
            f"  Web              = {gd['bw']} × {gd['hw']} mm",
            f"  Bot flange       = {gd['bf_bot']} × {gd['tf_bot']} mm",
            f"  A                = {sp['A']*1e4:.2f} cm²",
            f"  Ix (strong)      = {sp['Ix']*1e8:.2f} cm⁴",
            f"  Iy (weak)        = {sp['Iy']*1e8:.4f} cm⁴",
            f"  J (torsion)      = {sp['J']*1e8:.4f} cm⁴",
            f"  yb (centroid)    = {sp['yb']*1e3:.1f} mm",
            f"  yt               = {sp['yt']*1e3:.1f} mm",
            f"  Zb = Ix/yb       = {sp['Ix']/sp['yb']*1e6:.0f} cm³",
            f"  Zt = Ix/yt       = {sp['Ix']/sp['yt']*1e6:.0f} cm³",
            f"",
            f" DECK SLAB STRIP  (per girder)",
            f"  Width            = {p.girder_spacing:.3f} m",
            f"  Thickness        = {p.deck_t:.3f} m",
            f"  A                = {slb['A']*1e4:.2f} cm²",
            f"  Ix               = {slb['Ix']*1e8:.4f} cm⁴",
            f"",
            f" PIER COLUMN  (square)",
            f"  b × d            = {p.pier_col_w:.3f} × {p.pier_col_w:.3f} m",
            f"  A                = {col['A']*1e4:.2f} cm²",
            f"  Ix               = {col['Ix']*1e8:.2f} cm⁴",
            f"",
            f" PIER CAP BEAM  (rectangle)",
            f"  b × d            = {p.pier_cap_w:.3f} × {p.pier_cap_d:.3f} m",
            f"  A                = {cap['A']*1e4:.2f} cm²",
            f"  Ix               = {cap['Ix']*1e8:.2f} cm⁴",
            f"",
            f" ABUTMENT STEM  (rectangle)",
            f"  b × d            = {p.abut_w:.3f} × {p.abut_h:.3f} m",
            f"  A                = {abt['A']*1e4:.2f} cm²",
            f"",
            f" DIAPHRAGM  (full-depth slab)",
            f"  t × h_gird       = {p.diaph_t:.3f} × {gd['h']*1e-3:.3f} m",
            f"  A                = {dph['A']*1e4:.2f} cm²",
            f"",
            f" CONCRETE GRADES",
            f"  Girder: {p.girder_grade}",
            f"  Slab  : {p.slab_grade}",
            f"  Pier  : {p.pier_grade}",
        ]
        self._sec_txt.config(state="normal")
        self._sec_txt.delete("1.0","end")
        self._sec_txt.insert("end","\n".join(lines))
        self._sec_txt.config(state="disabled")

    # ── TAB: EXPORT ───────────────────────────────────────────────────────
    def _tab_export(self, parent):
        fr = tk.Frame(parent, bg=C["panel"])
        _sec(fr, "EXPORT — STAAD.Pro / JSON")

        self.exp_txt = tk.Text(fr, font=FONTS["code"], bg=C["entry_bg"],
                               fg=C["accent2"], bd=0, wrap="none", height=22)
        ys = tk.Scrollbar(fr, orient="vertical", command=self.exp_txt.yview,
                          width=5, troughcolor=C["border"], bg=C["panel"])
        xs = tk.Scrollbar(fr, orient="horizontal", command=self.exp_txt.xview,
                          troughcolor=C["border"], bg=C["panel"])
        self.exp_txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.pack(side="right", fill="y")
        xs.pack(side="bottom", fill="x")
        self.exp_txt.pack(fill="both", expand=True, padx=10, pady=4)

        r1 = tk.Frame(fr, bg=C["panel"])
        r1.pack(fill="x", padx=10, pady=4)
        self._btn(r1,"Preview STD",self._prev_std).pack(side="left",fill="x",expand=True,padx=(0,3))
        self._btn(r1,"Preview JSON",self._prev_json).pack(side="left",fill="x",expand=True)
        r2 = tk.Frame(fr, bg=C["panel"])
        r2.pack(fill="x", padx=10, pady=(0,8))
        self._btn(r2,"Save .std",self._save_std,accent=True).pack(side="left",fill="x",expand=True,padx=(0,3))
        self._btn(r2,"Save .json",self._save_json,accent=True).pack(side="left",fill="x",expand=True)
        return fr

    def _prev_std(self):
        self.exp_txt.delete("1.0","end")
        self.exp_txt.insert("end",self.model.to_std())
        self._log("STD preview generated.")
    def _prev_json(self):
        self.exp_txt.delete("1.0","end")
        self.exp_txt.insert("end",self.model.to_json())
        self._log("JSON preview generated.")
    def _save_std(self):
        p    = self.model.p
        name = f"bridge_{p.n_spans}span_{int(p.total_length)}m.std"
        path = fd.asksaveasfilename(defaultextension=".std",
                                    filetypes=[("STAAD","*.std"),("All","*.*")],
                                    initialfile=name)
        if not path: return
        with open(path,"w") as f: f.write(self.model.to_std())
        self._log(f"Saved: {os.path.basename(path)}")
    def _save_json(self):
        p    = self.model.p
        name = f"bridge_{p.n_spans}span_{int(p.total_length)}m.json"
        path = fd.asksaveasfilename(defaultextension=".json",
                                    filetypes=[("JSON","*.json"),("All","*.*")],
                                    initialfile=name)
        if not path: return
        with open(path,"w") as f: f.write(self.model.to_json())
        self._log(f"Saved: {os.path.basename(path)}")

    # ── TAB: LOG ──────────────────────────────────────────────────────────
    def _tab_log(self, parent):
        fr = tk.Frame(parent, bg=C["panel"])
        _sec(fr, "ACTIVITY LOG")
        self.log_txt = tk.Text(fr, font=FONTS["code"], bg=C["entry_bg"],
                               fg=C["green"], bd=0, wrap="word", height=30)
        ys = tk.Scrollbar(fr, orient="vertical", command=self.log_txt.yview,
                          width=5, troughcolor=C["border"], bg=C["panel"])
        self.log_txt.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y")
        self.log_txt.pack(fill="both", expand=True, padx=10, pady=4)
        self._btn(fr,"Clear Log",
                  lambda: self.log_txt.delete("1.0","end")).pack(fill="x",padx=10,pady=6)
        return fr

    def _log(self, msg):
        ts   = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}]  {msg}\n"
        try:
            self.log_txt.insert("end", line)
            self.log_txt.see("end")
        except Exception: pass
        print(line.strip())

    # ── REBUILD ───────────────────────────────────────────────────────────
    def _rebuild(self):
        # Guard: skip if UI variables aren't all created yet
        required = ["v_nspans","v_ngird","v_gsp","v_ovhg","v_deckt","v_gtype",
                    "v_ptype","v_ph","v_pcw","v_pcd","v_pcwid","v_ah","v_aw",
                    "v_dt","v_abut_sup","v_pier_sup","v_ggrade","v_sgrade",
                    "v_pgrade","_tog","_stat","canvas","_hud"]
        if not all(hasattr(self, a) for a in required):
            return

        p = self.model.p
        # Spans
        n = max(1, int(self.v_nspans.get()))
        p.n_spans = n
        if len(self._span_vars) != n:
            self._build_span_entries()
        p.span_lengths = [float(v.get()) for v in self._span_vars]
        # Cross-section
        p.n_girders      = max(2, int(self.v_ngird.get()))
        p.girder_spacing = float(self.v_gsp.get())
        p.overhang       = float(self.v_ovhg.get())
        p.deck_t         = float(self.v_deckt.get())
        p.girder_type    = self.v_gtype.get()
        # Custom dims
        if p.girder_type == "Custom (User)":
            p.cust_h      = float(self.v_ch.get())
            p.cust_bf_top = float(self.v_cbft.get())
            p.cust_tf_top = float(self.v_ctft.get())
            p.cust_bw     = float(self.v_cbw.get())
            p.cust_hw     = float(self.v_chw.get())
            p.cust_bf_bot = float(self.v_cbfb.get())
            p.cust_tf_bot = float(self.v_ctfb.get())
        # Pier
        p.pier_type    = self.v_ptype.get()
        p.pier_height  = float(self.v_ph.get())
        p.pier_col_w   = float(self.v_pcw.get())
        p.pier_cap_d   = float(self.v_pcd.get())
        p.pier_cap_w   = float(self.v_pcwid.get())
        p.abut_h       = float(self.v_ah.get())
        p.abut_w       = float(self.v_aw.get())
        p.diaph_t      = float(self.v_dt.get())
        p.abut_support = self.v_abut_sup.get()
        p.pier_support = self.v_pier_sup.get()
        # Materials
        p.girder_grade = self.v_ggrade.get()
        p.slab_grade   = self.v_sgrade.get()
        p.pier_grade   = self.v_pgrade.get()

        nodes, members = self.model.build()

        # Canvas flags
        self.canvas._show_dummy    = self._tog["dummy"].get()
        self.canvas._show_nodes    = self._tog["nodes"].get()
        self.canvas._show_loads    = self._tog["loads"].get()
        self.canvas._show_supports = self._tog["supports"].get()
        self.canvas._udl_val       = p.dc_load
        self.canvas.load(nodes, members, self.model.supports)

        s = self.model.stats()
        for key, lbl in self._stat.items():
            lbl.config(text=str(s.get(key,"-")))

        span_str = "+".join(f"{L:.0f}" for L in p.span_lengths[:p.n_spans])
        self.hdr_type.set(p.girder_type.replace("AASHTO ",""))
        self.hdr_spans.set(f"{p.n_spans}×({span_str})m")
        self.hdr_nodes.set(str(s["nodes"]))
        self.hdr_members.set(str(s["members"]))
        self.hdr_width.set(f"{s['width']:.1f}m")
        self.hdr_mass.set(f"{s['mass_t']}t")

        self._hud["dc"].config(text=f"{p.dc_load:.1f} kN/m")
        self._hud["dw"].config(text=f"{p.dw_load:.2f} kN/m")
        self._hud["lane"].config(text=f"{p.lane_load:.2f} kN/m")
        self._draw_girder_sketch()
        self._refresh_lc()

    def _apply_display(self): self._rebuild()

    def _reset_view(self):
        self.canvas._rot_x=0.28; self.canvas._rot_y=-0.42; self.canvas._offset=[0.0,0.0]
        if self.canvas.nodes:
            xs=[v[0] for v in self.canvas.nodes.values()]
            self.canvas._scale=(self.canvas.winfo_width() or 900)*0.32/max(max(xs)-min(xs),1)
        self.canvas.redraw()

    # ── SEND TO STAAD ─────────────────────────────────────────────────────
    def _send_staad(self):
        self._show_tab("Log")
        self._log("="*44)
        p = self.model.p
        self._log(f"Bridge: {p.n_spans}-span  {p.girder_type}")
        self._log(f"Total length: {p.total_length:.1f} m  Width: {p.deck_width:.2f} m")

        def task():
            try:
                n,m = self.exporter.send(self.model, log_fn=self._log)
                self.root.after(0, lambda: messagebox.showinfo(
                    "STAAD.Pro — Success",
                    f"Model transferred!\n\nNodes: {n}\nMembers: {m}\n\nRun analysis in STAAD.Pro."))
            except Exception as e:
                msg = str(e)
                is_safe = ("SAFEARRAY" in type(e).__name__ or
                           "SAFEARRAY" in str(type(e)) or
                           "SAFEARRAY" in msg)
                if is_safe:
                    self._log(f"WARNING (SAFEARRAY, suppressed): {msg}")
                else:
                    self.root.after(0, lambda m2=msg: messagebox.showerror(
                        "OpenSTAAD Error", m2))
                    self._log(f"ERROR: {msg}")

        threading.Thread(target=task, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("="*62)
    print("  BRIDGELAB v4 — Concrete Bridge Modeler")
    print("  Dark/Light mode | Input fields | AASHTO I-Girders")
    print("  Improved grillage: abutments, pier caps, diaphragms")
    print("="*62)
    BridgeLab()