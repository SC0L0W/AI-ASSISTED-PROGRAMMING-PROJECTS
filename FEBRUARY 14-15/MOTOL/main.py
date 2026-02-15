"""
Bridge STAAD Builder — Python Tkinter GUI
Generates and runs bridge truss models directly in STAAD.Pro via OpenSTAADPy.

Requirements:
    - STAAD.Pro (with an empty model open)
    - openstaadpy  (comes with STAAD.Pro or: pip install openstaadpy)
    - matplotlib   (pip install matplotlib)
    - Python 3.8+  (tkinter is built-in)

Usage:
    python bridge_staad_gui.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import math
import threading

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import matplotlib.patches as mpatches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

# ── palette ───────────────────────────────────────────────────────────────────
BG       = "#0a0f1a"
PANEL    = "#0d1526"
CARD     = "#111c30"
BORDER   = "#1e3a5f"
ACCENT   = "#f59e0b"
BLUE     = "#60a5fa"
TEXT     = "#c9d8f0"
MUTED    = "#475569"
GREEN    = "#22c55e"
RED      = "#ef4444"
PURPLE   = "#a78bfa"

# ── data ──────────────────────────────────────────────────────────────────────
BRIDGE_TYPES = ["Pratt Truss", "Warren Truss", "Howe Truss", "Bowstring Arch"]
BRIDGE_ICONS = {"Pratt Truss": "◇", "Warren Truss": "△",
                "Howe Truss": "▽", "Bowstring Arch": "⌒"}

CHORD_SECS = ["W21X50", "W18X35", "W16X31", "W14X26", "W24X55", "W18X46"]
DIAG_SECS  = ["L40404", "L50505", "L60606", "L30303", "L35353", "L45454"]

UNITS = {
    "Feet / Kip":    (1, 0),
    "Meter / kN":    (5, 4),
    "Inches / Kip":  (0, 0),
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Geometry
# ═══════════════════════════════════════════════════════════════════════════════

def compute_geometry(span, height, panels, btype):
    pw    = span / panels
    key   = btype.lower().split()[0]
    nodes = {}
    nid   = 1
    bot   = []
    top   = []

    for i in range(panels + 1):
        nodes[nid] = (round(i * pw, 4), 0.0, 0.0)
        bot.append(nid); nid += 1

    if key == "warren":
        for i in range(panels):
            nodes[nid] = (round((i + 0.5) * pw, 4), float(height), 0.0)
            top.append(nid); nid += 1
    elif key == "bowstring":
        for i in range(panels + 1):
            y = round(height * math.sin((i / panels) * math.pi), 4)
            nodes[nid] = (round(i * pw, 4), y, 0.0)
            top.append(nid); nid += 1
    else:
        for i in range(panels + 1):
            nodes[nid] = (round(i * pw, 4), float(height), 0.0)
            top.append(nid); nid += 1

    members = {}
    mid = 1
    bc, tc, vt, dg = [], [], [], []

    for i in range(panels):
        members[mid] = (bot[i], bot[i + 1]); bc.append(mid); mid += 1

    if key == "warren":
        for i in range(panels - 1):
            members[mid] = (top[i], top[i + 1]); tc.append(mid); mid += 1
        for i in range(panels):
            members[mid] = (bot[i], top[i]);     dg.append(mid); mid += 1
            members[mid] = (top[i], bot[i + 1]); dg.append(mid); mid += 1

    elif key in ("pratt", "howe"):
        for i in range(panels):
            members[mid] = (top[i], top[i + 1]); tc.append(mid); mid += 1
        for i in range(panels + 1):
            members[mid] = (bot[i], top[i]); vt.append(mid); mid += 1
        half = panels // 2
        for i in range(panels):
            if key == "pratt":
                p = (top[i], bot[i+1]) if i < half else (bot[i], top[i+1])
            else:
                p = (bot[i], top[i+1]) if i < half else (top[i], bot[i+1])
            members[mid] = p; dg.append(mid); mid += 1

    elif key == "bowstring":
        for i in range(panels):
            members[mid] = (top[i], top[i + 1]); tc.append(mid); mid += 1
        for i in range(panels + 1):
            members[mid] = (bot[i], top[i]); vt.append(mid); mid += 1
        for i in range(panels):
            members[mid] = (bot[i], top[i + 1]); dg.append(mid); mid += 1

    return nodes, members, bot, top, bc, tc, vt, dg


# ═══════════════════════════════════════════════════════════════════════════════
#  STAAD runner
# ═══════════════════════════════════════════════════════════════════════════════

def run_in_staad(cfg, log):
    try:
        from openstaadpy import os_analytical
    except ImportError:
        log("ERROR: openstaadpy not installed.\n"
            "Run:  pip install openstaadpy", error=True)
        return False

    span, height, panels = cfg["span"], cfg["height"], cfg["panels"]
    btype  = cfg["bridge_type"]
    lu, fu = UNITS[cfg["unit"]]
    csec, dsec = cfg["chord_sec"], cfg["diag_sec"]
    sl, sr = cfg["supp_l"], cfg["supp_r"]
    sw     = cfg["self_weight"]
    dl, ll, wl = cfg["dead"], cfg["live"], cfg["wind"]

    nodes, members, bot, top_n, bc, tc, vt, dg = \
        compute_geometry(span, height, panels, btype)
    tn, tm = len(nodes), len(members)

    try:
        log("Connecting to STAAD.Pro …")
        staad = os_analytical.connect()
        geo, prop, sup, load = (staad.Geometry, staad.Property,
                                staad.Support, staad.Load)

        log(f"Units → {cfg['unit']}  (length={lu}, force={fu})")
        staad.SetInputUnits(lu, fu)
        staad.SaveModel(True)

        log(f"Creating {tn} nodes …")
        for nid, (x, y, z) in nodes.items():
            geo.CreateNode(nid, x, y, z)

        log(f"Creating {tm} members …")
        for mid_, (n1, n2) in members.items():
            geo.CreateBeam(mid_, n1, n2)

        log("Assigning sections …")
        cc      = 1
        chord_p = prop.CreateBeamPropertyFromTable(cc, csec, 0, 0.0, 0.0)
        diag_p  = prop.CreateAnglePropertyFromTable(cc, dsec, 0, 0.0)

        prop.AssignBeamProperty(bc, chord_p)
        if tc: prop.AssignBeamProperty(tc, chord_p)
        if vt: prop.AssignBeamProperty(vt, diag_p)
        if dg: prop.AssignBeamProperty(dg, diag_p)
        prop.AssignMaterialToMember("STEEL", list(range(1, tm + 1)))

        if dg:
            log("Applying pin releases to diagonals …")
            sr_ = prop.CreateMemberPartialReleaseSpec(0, [0,1,1], [0.0,0.99,0.99])
            er_ = prop.CreateMemberPartialReleaseSpec(1, [0,1,1], [0.0,0.99,0.99])
            prop.AssignMemberSpecToBeam(dg, sr_)
            prop.AssignMemberSpecToBeam(dg, er_)

        log("Assigning supports …")
        sid_l = sup.CreateSupportFixed()  if sl == "Fixed"  else sup.CreateSupportPinned()
        sid_r = sup.CreateSupportPinned() if sr == "Pinned" else sup.CreateSupportFixed()
        sup.AssignSupportToNode([bot[0]],  sid_l)
        sup.AssignSupportToNode([bot[-1]], sid_r)

        log("Load Case 1 — Dead + Live …")
        c1 = load.CreateNewPrimaryLoadEx2("DEAD AND LIVE LOAD", 0, 1)
        load.SetLoadActive(c1)
        if sw:
            load.AddSelfWeightInXYZ(2, -1.0)
        if ll > 0:
            for n in bot[1:-1]:
                load.AddNodalLoad([n], 0.0, -ll, 0.0, 0.0, 0.0, 0.0)
        if dl > 0:
            load.AddMemberUniformForce(bc, 2, -dl, 0.0, 0.0, 0.0)

        log("Load Case 2 — Wind …")
        c2 = load.CreateNewPrimaryLoadEx2("WIND FROM LEFT", 3, 2)
        load.SetLoadActive(c2)
        if wl > 0:
            wm = vt if vt else bc
            load.AddMemberUniformForce(wm, 4, wl, 0.0, 0.0, 0.0)

        log("Load Combination 3 — 75% (DL+LL+WL) …")
        load.CreateNewLoadCombination("75 PERCENT DL LL WL", 3)
        load.AddLoadAndFactorToCombination(3, 1, 0.75)
        load.AddLoadAndFactorToCombination(3, 2, 0.75)

        log("Saving model …")
        staad.SaveModel(True)
        log("Running analysis …")
        staad.Command.PerformAnalysis(0)

        log(f"\n✔  SUCCESS\n"
            f"   {btype}  |  Span {span} ft  |  Height {height} ft  |  {panels} panels\n"
            f"   Nodes: {tn}   Members: {tm}", success=True)
        return True

    except Exception as exc:
        log(f"\n✘  {exc}", error=True)
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Preview (matplotlib)
# ═══════════════════════════════════════════════════════════════════════════════

def draw_preview(ax, span, height, panels, btype):
    ax.clear()
    ax.set_facecolor("#060f1a")
    nodes, members, bot, top_n, bc, tc, vt, dg = \
        compute_geometry(span, height, panels, btype)

    cmap = {}
    for m in bc + tc: cmap[m] = (ACCENT, 2.5)
    for m in dg:       cmap[m] = (BLUE,  1.6)
    for m in vt:       cmap[m] = (MUTED, 1.4)

    for mid_, (n1, n2) in members.items():
        x1, y1, _ = nodes[n1]; x2, y2, _ = nodes[n2]
        col, lw = cmap.get(mid_, (BLUE, 1.4))
        ax.plot([x1, x2], [y1, y2], color=col, linewidth=lw,
                solid_capstyle="round", solid_joinstyle="round")

    for nid_, (x, y, _) in nodes.items():
        ax.plot(x, y, "o", ms=4, color="#1e293b",
                mec=BLUE, mew=1.2, zorder=4)

    lx, ly, _ = nodes[bot[0]]
    rx, ry, _ = nodes[bot[-1]]
    ax.plot(lx, ly, "^", ms=11, color=ACCENT, zorder=5)
    ax.plot(rx, ry, "s", ms=9,  color=BLUE,   zorder=5)
    ax.axhline(-0.5, color=MUTED, lw=2)

    ax.set_xlim(-span * 0.05, span * 1.05)
    ax.set_ylim(-height * 0.3, height * 1.35)
    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")

    hs = [mpatches.Patch(color=ACCENT, label="Chord"),
          mpatches.Patch(color=BLUE,   label="Diagonal"),
          mpatches.Patch(color=MUTED,  label="Vertical")]
    ax.legend(handles=hs, loc="upper right", facecolor="#0a0f1a",
              edgecolor=BORDER, labelcolor=TEXT, fontsize=7, framealpha=0.9)
    ax.set_title(
        f"{btype}  —  Span {span} ft  ·  H {height} ft  ·  {panels} panels",
        color=ACCENT, fontsize=9, pad=6)


# ═══════════════════════════════════════════════════════════════════════════════
#  Scrollable frame
# ═══════════════════════════════════════════════════════════════════════════════

class ScrollFrame(tk.Frame):
    """A vertically scrollable container."""
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0, bd=0)
        self.vbar   = tk.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview)
        self.inner  = tk.Frame(self.canvas, bg=PANEL)
        self._wid   = self.canvas.create_window((0, 0),
                                                window=self.inner,
                                                anchor="nw")
        self.canvas.configure(yscrollcommand=self.vbar.set)
        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner.bind("<Configure>", self._on_inner)
        self.canvas.bind("<Configure>", self._on_canvas)
        # cross-platform scroll
        self.canvas.bind_all("<MouseWheel>", self._scroll)
        self.canvas.bind_all("<Button-4>",   self._scroll)
        self.canvas.bind_all("<Button-5>",   self._scroll)

    def _on_inner(self, _=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas(self, e):
        self.canvas.itemconfig(self._wid, width=e.width)

    def _scroll(self, e):
        if e.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif e.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")


# ═══════════════════════════════════════════════════════════════════════════════
#  Widget helpers
# ═══════════════════════════════════════════════════════════════════════════════

def mk_label(parent, text, size=9, color=MUTED, bold=False, **kw):
    font = ("Consolas", size, "bold") if bold else ("Consolas", size)
    return tk.Label(parent, text=text, font=font,
                    fg=color, bg=kw.pop("bg", PANEL), **kw)

def mk_entry(parent, var, width=8):
    return tk.Entry(parent, textvariable=var, width=width,
                    font=("Consolas", 10), fg=TEXT, bg=CARD,
                    insertbackground=ACCENT, relief="flat",
                    highlightthickness=1,
                    highlightbackground=BORDER,
                    highlightcolor=ACCENT)

def mk_combo(parent, values, var, width=14):
    s = ttk.Style()
    s.theme_use("default")
    s.configure("D.TCombobox",
                fieldbackground=CARD, background=CARD,
                foreground=TEXT, arrowcolor=ACCENT,
                bordercolor=BORDER, lightcolor=BORDER,
                darkcolor=BORDER, selectbackground=CARD,
                selectforeground=TEXT)
    return ttk.Combobox(parent, values=values, textvariable=var,
                        width=width, state="readonly",
                        style="D.TCombobox",
                        font=("Consolas", 10))

def mk_section(parent, text):
    f = tk.Frame(parent, bg=PANEL)
    mk_label(f, text, size=8, color=BLUE, bold=True).pack(side="left")
    tk.Frame(f, height=1, bg=BORDER).pack(side="left", fill="x",
                                           expand=True, padx=(6, 0))
    return f


# ═══════════════════════════════════════════════════════════════════════════════
#  Main App
# ═══════════════════════════════════════════════════════════════════════════════

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Bridge STAAD Builder  —  OpenSTAADPy")
        self.configure(bg=BG)
        self.geometry("1200x800")
        self.minsize(900, 640)
        self._init_vars()
        self._build()
        self._refresh()

    # ─ vars ──────────────────────────────────────────────────────────────────

    def _init_vars(self):
        self.v_btype  = tk.StringVar(value="Pratt Truss")
        self.v_span   = tk.DoubleVar(value=120.0)
        self.v_height = tk.DoubleVar(value=20.0)
        self.v_panels = tk.IntVar(value=8)
        self.v_unit   = tk.StringVar(value="Feet / Kip")
        self.v_supp_l = tk.StringVar(value="Fixed")
        self.v_supp_r = tk.StringVar(value="Pinned")
        self.v_chord  = tk.StringVar(value="W21X50")
        self.v_diag   = tk.StringVar(value="L40404")
        self.v_dead   = tk.DoubleVar(value=1.2)
        self.v_live   = tk.DoubleVar(value=20.0)
        self.v_wind   = tk.DoubleVar(value=0.6)
        self.v_sw     = tk.BooleanVar(value=True)
        for v in (self.v_btype, self.v_span, self.v_height, self.v_panels):
            v.trace_add("write", lambda *_: self.after(10, self._refresh))

    # ─ build ─────────────────────────────────────────────────────────────────

    def _build(self):
        # ── Header ───────────────────────────────────────────────────────────
        hdr = tk.Frame(self, bg="#060f1a", height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        mk_label(hdr, "⛓", size=18, color=ACCENT,
                 bg="#060f1a").pack(side="left", padx=(16, 8), pady=6)
        mk_label(hdr, "BRIDGE STAAD BUILDER", size=12, color=ACCENT,
                 bold=True, bg="#060f1a").pack(side="left")
        mk_label(hdr, "  OPENSTAADPY DIRECT RUNNER", size=8,
                 color=MUTED, bg="#060f1a").pack(side="left")
        self._dot = mk_label(hdr, "● READY", size=9, color=GREEN, bg="#060f1a")
        self._dot.pack(side="right", padx=16)
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

        # ── Body ─────────────────────────────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        # Left sidebar container — fixed width, never resizes
        sidebar_container = tk.Frame(body, bg=PANEL, width=295)
        sidebar_container.pack(side="left", fill="y")
        sidebar_container.pack_propagate(False)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        # Right panel
        right = tk.Frame(body, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        # ── Sidebar layout: Run button FIRST (bottom), scroll area fills rest ─
        # Pack run button at bottom BEFORE the scroll area so it is always visible
        run_area = tk.Frame(sidebar_container, bg=PANEL)
        run_area.pack(side="bottom", fill="x")
        tk.Frame(run_area, bg=BORDER, height=1).pack(fill="x")
        self._run_btn = tk.Button(
            run_area,
            text="▶   RUN IN STAAD.PRO",
            font=("Consolas", 11, "bold"),
            fg="#050a10",
            bg=ACCENT,
            activebackground="#d97706",
            activeforeground="#050a10",
            relief="flat",
            cursor="hand2",
            pady=13,
            command=self._on_run)
        self._run_btn.pack(fill="x")

        # Scrollable content above the run button
        scroll = ScrollFrame(sidebar_container, bg=PANEL)
        scroll.pack(fill="both", expand=True)
        self._build_controls(scroll.inner)

        # Right panel content
        self._build_right(right)

    # ─ sidebar controls ───────────────────────────────────────────────────────

    def _build_controls(self, sb):
        P = {"padx": 14}   # common horizontal padding

        # Bridge type
        mk_section(sb, "BRIDGE TYPE").pack(fill="x", pady=(12, 6), **P)
        g = tk.Frame(sb, bg=PANEL)
        g.pack(fill="x", pady=(0, 10), **P)
        self._type_btns = {}
        for i, bt in enumerate(BRIDGE_TYPES):
            r, c = divmod(i, 2)
            b = tk.Button(
                g, text=f"{BRIDGE_ICONS[bt]}\n{bt}",
                font=("Consolas", 8), wraplength=100,
                width=11, height=3, relief="flat", cursor="hand2",
                command=lambda x=bt: self._pick_type(x))
            b.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
            self._type_btns[bt] = b
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)
        self._pick_type("Pratt Truss")

        # Geometry
        mk_section(sb, "GEOMETRY").pack(fill="x", pady=(8, 6), **P)
        self._mk_slider(sb, "Span (ft)",   self.v_span,   40,  400, 10)
        self._mk_slider(sb, "Height (ft)", self.v_height,  5,   60,  1)
        self._mk_slider(sb, "Panels",      self.v_panels,  4,   16,  2)

        # Units & Supports
        mk_section(sb, "UNITS & SUPPORTS").pack(fill="x", pady=(10, 6), **P)
        self._mk_combo_row(sb, "Units",         self.v_unit,   list(UNITS), **P)
        self._mk_combo_row(sb, "Left support",  self.v_supp_l, ["Fixed", "Pinned"], **P)
        self._mk_combo_row(sb, "Right support", self.v_supp_r, ["Pinned", "Roller"], **P)

        # Sections
        mk_section(sb, "SECTIONS (AISC)").pack(fill="x", pady=(10, 6), **P)
        self._mk_combo_row(sb, "Chord",     self.v_chord, CHORD_SECS, **P)
        self._mk_combo_row(sb, "Diag/Vert", self.v_diag,  DIAG_SECS,  **P)

        # Loads
        mk_section(sb, "LOADS").pack(fill="x", pady=(10, 6), **P)
        self._mk_entry_row(sb, "Dead load (k/ft)",      self.v_dead, **P)
        self._mk_entry_row(sb, "Live load/node (kips)", self.v_live, **P)
        self._mk_entry_row(sb, "Wind load (k/ft)",      self.v_wind, **P)

        sw_row = tk.Frame(sb, bg=PANEL)
        sw_row.pack(fill="x", pady=4, **P)
        mk_label(sw_row, "Self weight").pack(side="left")
        tk.Checkbutton(
            sw_row, variable=self.v_sw, bg=PANEL,
            fg=TEXT, selectcolor=CARD,
            activebackground=PANEL,
            highlightthickness=0).pack(side="right")

        # Bottom spacer so content doesn't crowd the run button divider
        tk.Frame(sb, bg=PANEL, height=20).pack()

    # ─ widget factory helpers ────────────────────────────────────────────────

    def _mk_slider(self, parent, label, var, lo, hi, res, **kw):
        padx = kw.get("padx", 14)
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=1, padx=padx)
        mk_label(f, label, color=MUTED).pack(anchor="w")
        row = tk.Frame(f, bg=PANEL)
        row.pack(fill="x")
        s = tk.Scale(
            row, variable=var, from_=lo, to=hi, resolution=res,
            orient="horizontal", bg=PANEL, fg=TEXT, troughcolor=CARD,
            activebackground=ACCENT, highlightthickness=0,
            sliderrelief="flat", bd=0, font=("Consolas", 8),
            command=lambda *_: self.after(10, self._refresh))
        s.pack(side="left", fill="x", expand=True)
        val_lbl = mk_label(row, "", color=ACCENT, width=5)
        val_lbl.pack(side="right")
        def _upd(*_):
            try:
                v = var.get()
                val_lbl.config(text=f"{v:.0f}" if isinstance(v, float) else str(v))
            except Exception:
                pass
        var.trace_add("write", _upd)
        _upd()

    def _mk_combo_row(self, parent, label, var, values, **kw):
        padx = kw.get("padx", 14)
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=2, padx=padx)
        mk_label(f, label).pack(side="left")
        mk_combo(f, values, var, width=13).pack(side="right")

    def _mk_entry_row(self, parent, label, var, **kw):
        padx = kw.get("padx", 14)
        f = tk.Frame(parent, bg=PANEL)
        f.pack(fill="x", pady=2, padx=padx)
        mk_label(f, label).pack(side="left")
        mk_entry(f, var, width=8).pack(side="right")

    def _pick_type(self, bt):
        self.v_btype.set(bt)
        for name, btn in self._type_btns.items():
            if name == bt:
                btn.config(bg=CARD, fg=ACCENT,
                           highlightthickness=1,
                           highlightbackground=ACCENT)
            else:
                btn.config(bg=PANEL, fg=MUTED,
                           highlightthickness=1,
                           highlightbackground=BORDER)

    # ─ right panel ───────────────────────────────────────────────────────────

    def _build_right(self, parent):
        # Preview
        prev = tk.Frame(parent, bg="#060f1a", height=310)
        prev.pack(fill="x")
        prev.pack_propagate(False)

        if HAS_MPL:
            self._fig, self._ax = plt.subplots(figsize=(9, 3.0),
                                               facecolor="#060f1a")
            self._fig.subplots_adjust(left=0.01, right=0.99,
                                      top=0.88, bottom=0.04)
            self._mpl_canvas = FigureCanvasTkAgg(self._fig, master=prev)
            self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True)
        else:
            mk_label(prev, "pip install matplotlib  for live preview",
                     color=MUTED, size=10).pack(expand=True)

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # Stat bar
        stat = tk.Frame(parent, bg=PANEL, height=40)
        stat.pack(fill="x")
        stat.pack_propagate(False)
        self._stats = []
        for name, col in [("SPAN", ACCENT), ("HEIGHT", BLUE),
                          ("PANELS", PURPLE), ("TYPE", GREEN), ("CHORD", ACCENT)]:
            tk.Frame(stat, bg=BORDER, width=1).pack(side="left", fill="y")
            c = tk.Frame(stat, bg=PANEL)
            c.pack(side="left", fill="y", padx=1)
            mk_label(c, name, size=7, color=MUTED).pack(anchor="w", padx=8, pady=(4, 0))
            v = mk_label(c, "—", size=10, color=col, bold=True)
            v.pack(anchor="w", padx=8)
            self._stats.append((v, col))
        tk.Frame(stat, bg=BORDER, width=1).pack(side="left", fill="y")

        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")

        # Log header
        lhdr = tk.Frame(parent, bg="#060f1a", height=28)
        lhdr.pack(fill="x")
        lhdr.pack_propagate(False)
        mk_label(lhdr, "  OUTPUT LOG", size=8, color=BLUE, bold=True,
                 bg="#060f1a").pack(side="left", pady=4)
        tk.Button(lhdr, text="CLEAR", font=("Consolas", 7),
                  fg=MUTED, bg="#060f1a", relief="flat", cursor="hand2",
                  command=self._clear_log).pack(side="right", padx=8)

        # Log console
        self._log = scrolledtext.ScrolledText(
            parent, font=("Consolas", 9), bg="#040b15", fg=TEXT,
            insertbackground=ACCENT, relief="flat", wrap="word",
            selectbackground=BORDER)
        self._log.pack(fill="both", expand=True, padx=2, pady=2)
        self._log.tag_config("err",  foreground=RED)
        self._log.tag_config("ok",   foreground=GREEN)
        self._log.tag_config("info", foreground=BLUE)
        self._log.config(state="disabled")
        self._log_write(
            "Bridge STAAD Builder ready.\n"
            "Set your parameters and click  ▶ RUN IN STAAD.PRO\n",
            tag="info")

    # ─ preview ───────────────────────────────────────────────────────────────

    def _refresh(self):
        vals = [
            (f"{self.v_span.get():.0f} ft",          ACCENT),
            (f"{self.v_height.get():.0f} ft",         BLUE),
            (str(self.v_panels.get()),                PURPLE),
            (self.v_btype.get().split()[0].upper(),   GREEN),
            (self.v_chord.get(),                      ACCENT),
        ]
        for (lbl_w, _), (txt, col) in zip(self._stats, vals):
            lbl_w.config(text=txt, fg=col)

        if not HAS_MPL:
            return
        try:
            draw_preview(self._ax,
                         self.v_span.get(), self.v_height.get(),
                         self.v_panels.get(), self.v_btype.get())
            self._mpl_canvas.draw()
        except Exception:
            pass

    # ─ log ───────────────────────────────────────────────────────────────────

    def _log_write(self, msg, tag=None):
        self._log.config(state="normal")
        self._log.insert("end", msg + "\n", tag or "")
        self._log.see("end")
        self._log.config(state="disabled")

    def _clear_log(self):
        self._log.config(state="normal")
        self._log.delete("1.0", "end")
        self._log.config(state="disabled")

    # ─ run ───────────────────────────────────────────────────────────────────

    def _on_run(self):
        self._run_btn.config(state="disabled", text="⏳  Running …")
        self._dot.config(text="● RUNNING", fg=ACCENT)
        self._clear_log()
        self._log_write("Starting bridge model …\n", tag="info")

        cfg = {
            "bridge_type": self.v_btype.get(),
            "span":        self.v_span.get(),
            "height":      self.v_height.get(),
            "panels":      self.v_panels.get(),
            "unit":        self.v_unit.get(),
            "supp_l":      self.v_supp_l.get(),
            "supp_r":      self.v_supp_r.get(),
            "chord_sec":   self.v_chord.get(),
            "diag_sec":    self.v_diag.get(),
            "dead":        self.v_dead.get(),
            "live":        self.v_live.get(),
            "wind":        self.v_wind.get(),
            "self_weight": self.v_sw.get(),
        }

        def worker():
            def log(msg, error=False, success=False):
                tag = "err" if error else ("ok" if success else None)
                self.after(0, self._log_write, msg, tag)

            ok = run_in_staad(cfg, log)

            def done():
                if ok:
                    self._dot.config(text="● DONE", fg=GREEN)
                else:
                    self._dot.config(text="● ERROR", fg=RED)
                self._run_btn.config(state="normal",
                                     text="▶   RUN IN STAAD.PRO")
            self.after(0, done)

        threading.Thread(target=worker, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    App().mainloop()