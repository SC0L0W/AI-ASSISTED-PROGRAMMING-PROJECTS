#!/usr/bin/env python3
"""
Dog-legged concrete stair - parametric STAAD.Pro modeller with UI
=================================================================

    pip install openstaadpy          (needs STAAD.Pro installed, Windows)
    python doglegged_stair_ui.py     (UI)
    python doglegged_stair_ui.py --std stair.std      (headless .std export)

Workflow
  1. In STAAD.Pro create/open an EMPTY Space model, units = Meter / kN.
  2. Run this script, enter parameters, press "Preview" to check the shape.
  3. Press "Build in STAAD" -> nodes, plates, thickness, material, supports,
     load cases and combinations are pushed through openstaadpy.
  4. "Export .std" writes a stand-alone STAAD input file (no STAAD needed)
     - use it as fallback or to cross-check the API route.

Plan layout (Y is vertical):
    Flight 1 : z = 0 .. W              runs +X  (lower floor -> landing)
    Landing  : x = Lh .. Lh+Lw         spans both flights
    Flight 2 : z = W+gap .. 2W+gap     runs -X  (landing -> upper floor)
Model datum = mid-surface of the waist slab; steps are not meshed, their
weight is applied as an equivalent area load on plan area.

NOTE ON openstaadpy: every API call lives in class StaadBackend, using the
OpenSTAAD method names. Calls go through _try(), which tries alternative
names and logs failures instead of crashing - if your STAAD version names
something differently, fix it in that one class.
"""
import math
import sys
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAVE_TK = True
except ImportError:                      # headless / no Tk: model + export still work
    tk = ttk = filedialog = messagebox = None
    HAVE_TK = False

# ---------------------------------------------------------------- parameters
# (group, key, label, unit, default)
FIELDS = [
    ("Geometry", "n_risers",       "Risers per flight",          "-",     10),
    ("Geometry", "floor_height",   "Floor-to-floor height",      "m",     3.0),
    ("Geometry", "going",          "Going (tread)",              "m",     0.250),
    ("Geometry", "flight_width",   "Flight width (each)",        "m",     1.200),
    ("Geometry", "well_gap",       "Well gap between flights",   "m",     0.0),
    ("Geometry", "landing_length", "Landing length (X)",         "m",     1.200),
    ("Sections", "waist_t",        "Waist slab thickness",       "m",     0.175),
    ("Sections", "landing_t",      "Landing slab thickness",     "m",     0.200),
    ("Mesh",     "mesh",           "Target plate size",          "m",     0.30),
    ("Material", "E",              "Young's modulus E",          "kN/m2", 28.0e6),
    ("Material", "poisson",        "Poisson's ratio",            "-",     0.17),
    ("Material", "density",        "Density",                    "kN/m3", 25.0),
    ("Loads",    "finishes",       "Finishes (plan area)",       "kN/m2", 1.0),
    ("Loads",    "live",           "Imposed load (plan area)",   "kN/m2", 3.0),
    ("Loads",    "gamma_g",        "ULS factor on DL",           "-",     1.35),
    ("Loads",    "gamma_q",        "ULS factor on LL",           "-",     1.50),
]
OPTIONS = [  # (key, label, default)
    ("landing_walls", "Landing edges bear on walls (vertical supports)", True),
    ("top_pinned",    "Top of flight 2: PINNED (else vertical+Z roller)", False),
]


def parse_params(raw):
    p = {}
    for _, key, label, _, default in FIELDS:
        try:
            v = float(raw[key])
        except (ValueError, TypeError):
            raise ValueError(f"'{label}' is not a number")
        p[key] = int(round(v)) if key == "n_risers" else v
    for key, _, _ in OPTIONS:
        p[key] = bool(raw.get(key, False))
    if p["n_risers"] < 2:
        raise ValueError("Need at least 2 risers per flight")
    for k in ("floor_height", "going", "flight_width", "landing_length",
              "waist_t", "landing_t", "mesh", "E", "density"):
        if p[k] <= 0:
            raise ValueError(f"'{k}' must be > 0")
    if p["well_gap"] < 0:
        raise ValueError("Well gap must be >= 0")
    return p


# --------------------------------------------------------------- model build
class Model:
    def __init__(self):
        self.coords = []          # [(x,y,z)]  node id = index+1
        self.elems = []           # [(n1,n2,n3,n4)] plate id = index+1
        self.flights = []         # plate ids
        self.landing = []
        self.sup_bottom = []      # node ids
        self.sup_top = []
        self.sup_walls = []
        self.dl_press = {}        # plate id -> kN/m2 (downward)
        self.ll_press = {}
        self.info = {}
        self._nodes = {}

    def nid(self, x, y, z):
        k = (round(x, 4), round(y, 4), round(z, 4))
        if k not in self._nodes:
            self.coords.append(k)
            self._nodes[k] = len(self.coords)
        return self._nodes[k]


def build_model(p):
    n = p["n_risers"]
    R = p["floor_height"] / (2 * n)
    G = p["going"]
    W, gap, Lw = p["flight_width"], p["well_gap"], p["landing_length"]
    Lh, Hf = (n - 1) * G, (n - 1) * R
    Wtot = 2 * W + gap
    m = Model()

    def ndiv(L):
        return max(1, math.ceil(L / p["mesh"] - 1e-9))

    def lin(a, b, k):
        return [a + (b - a) * i / k for i in range(k + 1)]

    def grid(xy, zs):
        ids = []
        for i in range(len(xy) - 1):
            for j in range(len(zs) - 1):
                (x0, y0), (x1, y1) = xy[i], xy[i + 1]
                z0, z1 = zs[j], zs[j + 1]
                # order chosen so plate normal points +Y
                m.elems.append((m.nid(x0, y0, z0), m.nid(x0, y0, z1),
                                m.nid(x1, y1, z1), m.nid(x1, y1, z0)))
                ids.append(len(m.elems))
        return ids

    mx, mz = ndiv(Lh), ndiv(W)
    z1 = lin(0, W, mz)
    z2 = lin(W + gap, Wtot, mz)
    f1 = grid([(Lh * i / mx, Hf * i / mx) for i in range(mx + 1)], z1)
    f2 = grid([(Lh * i / mx, 2 * Hf - Hf * i / mx) for i in range(mx + 1)], z2)
    ml = ndiv(Lw)
    zl = sorted(set(round(z, 4) for z in z1 + z2))
    ld = grid([(Lh + Lw * i / ml, Hf) for i in range(ml + 1)], zl)
    m.flights, m.landing = f1 + f2, ld

    def pick(f):
        return [i + 1 for i, c in enumerate(m.coords) if f(*c)]

    e = 1e-6
    m.sup_bottom = pick(lambda x, y, z: abs(x) < e and abs(y) < e and z <= W + e)
    m.sup_top = pick(lambda x, y, z: abs(x) < e and abs(y - 2 * Hf) < e and z >= W + gap - e)
    if p["landing_walls"]:
        m.sup_walls = pick(lambda x, y, z: abs(y - Hf) < e and x > Lh + e and
                           (abs(x - (Lh + Lw)) < e or abs(z) < e or abs(z - Wtot) < e))

    dl_fl = 0.5 * R * p["density"] + p["finishes"]     # steps (avg R/2) + finishes
    dl_ld = p["finishes"]
    for i in m.flights:
        m.dl_press[i] = dl_fl
        m.ll_press[i] = p["live"]
    for i in m.landing:
        m.dl_press[i] = dl_ld
        m.ll_press[i] = p["live"]

    m.info = dict(R=R, G=G, Lh=Lh, Hf=Hf, Wtot=Wtot,
                  pitch=math.degrees(math.atan2(R, G)),
                  dl_flight=dl_fl, dl_landing=dl_ld,
                  nodes=len(m.coords), plates=len(m.elems))
    return m


def stair_checks(p):
    """Rule-of-thumb comfort checks (UK-style values) - verify against local code."""
    n = p["n_risers"]
    R = p["floor_height"] / (2 * n)
    G = p["going"]
    pitch = math.degrees(math.atan2(R, G))
    out = [
        (f"Riser R = {R*1000:.1f} mm", 100 <= R * 1000 <= 220),
        (f"Going G = {G*1000:.0f} mm", G * 1000 >= 220),
        (f"2R + G = {(2*R+G)*1000:.0f} mm (550-700)", 550 <= (2 * R + G) * 1000 <= 700),
        (f"Pitch = {pitch:.1f} deg (<= 42)", pitch <= 42),
        (f"Total risers = {2*n}", True),
    ]
    return out


def tributary_nodal_loads(m, press):
    """Convert plan-area pressure to nodal loads (kN, down)  - exact for
    uniform pressure on projected area; avoids element-pressure API calls."""
    acc = {}
    for pid, q in press.items():
        nodes = m.elems[pid - 1]
        xs = [m.coords[k - 1][0] for k in nodes]
        zs = [m.coords[k - 1][2] for k in nodes]
        a = 0.0
        for i in range(4):
            j = (i + 1) % 4
            a += xs[i] * zs[j] - xs[j] * zs[i]
        f = q * abs(a) / 2.0 / 4.0
        for k in nodes:
            acc[k] = acc.get(k, 0.0) + f
    return acc


# ------------------------------------------------------------- .std exporter
def write_std(m, p, path):
    def rng(ids):
        ids = sorted(ids)
        out, s = [], ids[0]
        for a, b in zip(ids, ids[1:] + [None]):
            if b != a + 1:
                out.append(f"{s}" if s == a else f"{s} TO {a}")
                s = b
        return " ".join(out)

    def wrap(txt, w=76):
        lines, cur = [], ""
        for t in txt.split():
            if len(cur) + len(t) + 1 > w:
                lines.append(cur + " -")
                cur = t
            else:
                cur = (cur + " " + t).strip()
        return "\n".join(lines + [cur])

    i = m.info
    o = ["STAAD SPACE DOG-LEGGED CONCRETE STAIR (PARAMETRIC)",
         "START JOB INFORMATION", "END JOB INFORMATION",
         "INPUT WIDTH 79", "UNIT METER KN",
         f"* risers/flight={p['n_risers']} R={i['R']:.4f} G={i['G']} "
         f"pitch={i['pitch']:.1f} deg",
         "JOINT COORDINATES"]
    o += [f"{k+1} {x:.4f} {y:.4f} {z:.4f}" for k, (x, y, z) in enumerate(m.coords)]
    o += ["ELEMENT INCIDENCES SHELL"]
    o += [f"{k+1} {a} {b} {c} {d}" for k, (a, b, c, d) in enumerate(m.elems)]
    o += ["ELEMENT PROPERTY",
          wrap(f"{rng(m.flights)} THICKNESS {p['waist_t']}"),
          wrap(f"{rng(m.landing)} THICKNESS {p['landing_t']}"),
          "DEFINE MATERIAL START", "ISOTROPIC CONCRETE",
          f"E {p['E']:.4e}", f"POISSON {p['poisson']}",
          f"DENSITY {p['density']}", "ALPHA 1e-05", "DAMP 0.05",
          "TYPE CONCRETE", "STRENGTH FCU 30000", "END DEFINE MATERIAL",
          "CONSTANTS", "MATERIAL CONCRETE ALL", "SUPPORTS",
          wrap(f"{rng(m.sup_bottom)} PINNED")]
    if p["top_pinned"]:
        o.append(wrap(f"{rng(m.sup_top)} PINNED"))
    else:
        o.append(wrap(f"{rng(m.sup_top)} FIXED BUT FX MX MY MZ"))
    if m.sup_walls:
        o.append(wrap(f"{rng(m.sup_walls)} FIXED BUT FX FZ MX MY MZ"))
    o += ["LOAD 1 LOADTYPE DEAD TITLE DL: SELFWEIGHT + STEPS + FINISHES",
          "SELFWEIGHT Y -1", "ELEMENT LOAD",
          wrap(f"{rng(m.flights)} PR GY -{i['dl_flight']:.4f}"),
          wrap(f"{rng(m.landing)} PR GY -{i['dl_landing']:.4f}"),
          "LOAD 2 LOADTYPE LIVE TITLE LL: IMPOSED", "ELEMENT LOAD",
          wrap(f"{rng(m.flights + m.landing)} PR GY -{p['live']:.4f}"),
          f"LOAD COMB 3 ULS {p['gamma_g']}DL+{p['gamma_q']}LL",
          f"1 {p['gamma_g']} 2 {p['gamma_q']}",
          "LOAD COMB 4 SLS 1.0DL+1.0LL", "1 1.0 2 1.0",
          "PERFORM ANALYSIS", "LOAD LIST 3 4", "PRINT SUPPORT REACTION", "FINISH"]
    with open(path, "w") as fh:
        fh.write("\n".join(o) + "\n")


# ----------------------------------------------------------- openstaadpy side
class StaadBackend:
    def __init__(self, log):
        self.log = log
        self.staad = None

    # ---- plumbing
    def connect(self):
        try:
            from openstaadpy import os_analytical
        except ImportError:
            raise RuntimeError("openstaadpy not installed:  pip install openstaadpy")
        self.staad = os_analytical.connect()
        self._bind()

    def _bind(self):
        s = self.staad
        self.geo, self.prop = s.Geometry, s.Property
        self.sup, self.load = s.Support, s.Load
        try:
            self.log(f"Connected. File: {s.GetSTAADFile()}")
        except Exception:
            self.log("Connected to STAAD.Pro.")

    def _try(self, obj, names, *args, what=""):
        """Call first working method from names. Returns (ok, result)."""
        last = None
        for nm in names:
            f = getattr(obj, nm, None)
            if f is None:
                continue
            try:
                return True, f(*args)
            except Exception as ex:      # wrong signature / API difference
                last = ex
        self.log(f"  ! {what or names[0]} failed: {last or 'method not found'}")
        return False, last

    # ---- build
    def push(self, m, p, run_analysis=False):
        g, pr, su, ld = self.geo, self.prop, self.sup, self.load

        ok, cnt = self._try(g, ["GetNodeCount"], what="GetNodeCount")
        noff = int(cnt) if ok and cnt else 0
        ok, cnt = self._try(g, ["GetPlateCount"], what="GetPlateCount")
        eoff = int(cnt) if ok and cnt else 0
        if noff or eoff:
            self.log(f"Model not empty ({noff} nodes, {eoff} plates) - "
                     f"new items numbered after existing ones.")
        N = lambda k: k + noff
        E = lambda k: k + eoff

        self.log(f"Creating {len(m.coords)} nodes ...")
        for k, (x, y, z) in enumerate(m.coords, 1):
            self._try(g, ["CreateNode", "AddNode"], N(k), x, y, z, what=f"node {k}")

        self.log(f"Creating {len(m.elems)} plates ...")
        for k, q in enumerate(m.elems, 1):
            self._try(g, ["CreatePlate", "AddPlate"], E(k), *[N(a) for a in q],
                      what=f"plate {k}")

        # thickness
        self.log("Assigning plate thicknesses ...")
        for ids, t, nm in ((m.flights, p["waist_t"], "waist"),
                           (m.landing, p["landing_t"], "landing")):
            ok, pid = self._try(pr, ["CreatePlateThicknessProperty"], t,
                                what=f"{nm} thickness property")
            if not ok:
                continue
            lst = [E(i) for i in ids]
            ok, _ = self._try(pr, ["AssignPlateThickness"], lst, pid,
                              what=f"assign {nm} thickness (list)")
            if not ok:
                for i in lst:
                    self._try(pr, ["AssignPlateThickness"], i, pid)

        # material
        self.log("Material ...")
        allp = [E(i) for i in range(1, len(m.elems) + 1)]
        ok, mid = self._try(pr, ["CreateIsotropicMaterialProperty",
                                 "CreateMaterialProperty"],
                            "CONCRETE", p["E"], p["poisson"], p["density"], 1e-5,
                            0.05, what="create material")
        done = False
        if ok:
            done, _ = self._try(pr, ["AssignMaterialToPlate"], allp, "CONCRETE",
                                what="assign material")
        if not done:
            self.log("  -> set concrete constants manually in STAAD "
                     f"(E={p['E']:.3e}, nu={p['poisson']}, density={p['density']}) "
                     "or use Export .std.")

        # supports
        self.log("Supports ...")
        ok, sp = self._try(su, ["CreateSupportPinned"], what="pinned support")
        if ok:
            for k in m.sup_bottom + (m.sup_top if p["top_pinned"] else []):
                self._try(su, ["AssignSupportToNode"], N(k), sp)
        # release flags order: FX FY FZ MX MY MZ (1 = released)
        # top edge restrains FY,FZ ; walls restrain FY only
        groups = []
        if not p["top_pinned"]:
            groups.append((m.sup_top, [1, 0, 0, 1, 1, 1], "top edge"))
        if m.sup_walls:
            groups.append((m.sup_walls, [1, 0, 1, 1, 1, 1], "landing walls"))
        for nodes, rel, nm in groups:
            ok, sid = self._try(su, ["CreateSupportFixedBut"], what=f"FIXED BUT ({nm})")
            set_ok = False
            if ok:
                set_ok, _ = self._try(
                    su, ["SetSupportReleases", "SetSupportFixedButReleases",
                         "SetSupportReleaseSpec"], sid, rel,
                    what=f"set releases ({nm})")
            if ok and set_ok:
                for k in nodes:
                    self._try(su, ["AssignSupportToNode"], N(k), sid)
            else:
                self.log(f"  -> assign FIXED BUT ({nm}; restrain "
                         f"{'FY,FZ' if nm=='top edge' else 'FY only'}) manually "
                         f"to nodes {[N(k) for k in nodes]}")

        # loads
        self.log("Load cases ...")
        dl_nodal = tributary_nodal_loads(m, m.dl_press)
        ll_nodal = tributary_nodal_loads(m, m.ll_press)

        ok, dl = self._try(ld, ["CreateNewPrimaryLoad"], "DL: selfweight+steps+finishes")
        if ok:
            self._try(ld, ["SetLoadActive"], dl)
            self._try(ld, ["AddSelfWeightInXYZ"], 2, -1.0, what="selfweight")
            for k, f in dl_nodal.items():
                self._try(ld, ["AddNodalLoad"], N(k), 0.0, -f, 0.0, 0.0, 0.0, 0.0)
        ok, ll = self._try(ld, ["CreateNewPrimaryLoad"], "LL: imposed")
        if ok:
            self._try(ld, ["SetLoadActive"], ll)
            for k, f in ll_nodal.items():
                self._try(ld, ["AddNodalLoad"], N(k), 0.0, -f, 0.0, 0.0, 0.0, 0.0)
        for title, fg, fq in (("ULS", p["gamma_g"], p["gamma_q"]), ("SLS", 1.0, 1.0)):
            ok, cb = self._try(ld, ["CreateNewLoadCombination"],
                               f"{title} {fg}DL+{fq}LL")
            if ok:
                self._try(ld, ["AddLoadAndFactorToCombination"], cb, dl, fg)
                self._try(ld, ["AddLoadAndFactorToCombination"], cb, ll, fq)

        try:
            self.staad.UpdateStructure()
        except Exception:
            pass
        if run_analysis:
            self.log("Running analysis ...")
            self._try(self.staad, ["Analyze"], what="Analyze")
        self.log("Done. Check the model in STAAD (set model units to m / kN first).")


# ------------------------------------------------------------------ preview
class Preview(tk.Canvas if HAVE_TK else object):
    def __init__(self, master, **kw):
        super().__init__(master, bg="white", highlightthickness=0, **kw)
        self.az, self.el, self.model = math.radians(-35), math.radians(28), None
        self._drag = None
        self.bind("<ButtonPress-1>", lambda e: setattr(self, "_drag", (e.x, e.y)))
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Configure>", lambda e: self.redraw())

    def _on_drag(self, e):
        if self._drag:
            dx, dy = e.x - self._drag[0], e.y - self._drag[1]
            self.az += dx * 0.01
            self.el = max(-1.5, min(1.5, self.el + dy * 0.01))
            self._drag = (e.x, e.y)
            self.redraw()

    def show(self, model):
        self.model = model
        self.redraw()

    def _proj(self, x, y, z):
        ca, sa, ce, se = math.cos(self.az), math.sin(self.az), math.cos(self.el), math.sin(self.el)
        xr = x * ca + z * sa
        zr = -x * sa + z * ca
        return xr, y * ce - zr * se, y * se + zr * ce      # sx, sy(up), depth

    def redraw(self):
        self.delete("all")
        m = self.model
        if not m:
            self.create_text(10, 10, anchor="nw", fill="#888",
                             text="Press Preview.  Drag to rotate.")
            return
        P = [self._proj(*c) for c in m.coords]
        xs, ys = [q[0] for q in P], [q[1] for q in P]
        w, h = max(self.winfo_width(), 50), max(self.winfo_height(), 50)
        s = 0.88 * min(w / max(max(xs) - min(xs), 1e-6), h / max(max(ys) - min(ys), 1e-6))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        T = lambda q: (w / 2 + (q[0] - cx) * s, h / 2 - (q[1] - cy) * s)
        fl, ld = set(m.flights), set(m.landing)
        order = sorted(range(len(m.elems)),
                       key=lambda i: sum(P[k - 1][2] for k in m.elems[i]))
        for i in order:
            pts = [c for k in m.elems[i] for c in T(P[k - 1])]
            col = "#b9c7d9" if (i + 1) in fl else "#d9c9b0"
            self.create_polygon(pts, fill=col, outline="#555")
        for ids, col in ((m.sup_bottom, "#d62728"), (m.sup_top, "#ff7f0e"),
                         (m.sup_walls, "#1f77b4")):
            for k in ids:
                x, y = T(P[k - 1])
                self.create_oval(x - 4, y - 4, x + 4, y + 4, fill=col, outline="")
        self.create_text(8, h - 8, anchor="sw", fill="#444", font=("TkDefaultFont", 8),
                         text="red: bottom pinned   orange: top edge   blue: landing walls"
                              "   |  drag = rotate")


# ----------------------------------------------------------------------- UI
class App(tk.Tk if HAVE_TK else object):
    def __init__(self):
        super().__init__()
        self.title("Dog-legged concrete stair  -  STAAD.Pro (openstaadpy)")
        self.geometry("1100x700")
        self.vars, self.opts = {}, {}
        left = ttk.Frame(self, padding=6)
        left.pack(side="left", fill="y")
        right = ttk.Frame(self, padding=6)
        right.pack(side="left", fill="both", expand=True)

        groups = {}
        for grp, key, label, unit, dflt in FIELDS:
            if grp not in groups:
                groups[grp] = ttk.LabelFrame(left, text=grp, padding=4)
                groups[grp].pack(fill="x", pady=2)
            r = ttk.Frame(groups[grp])
            r.pack(fill="x")
            ttk.Label(r, text=label, width=26).pack(side="left")
            v = tk.StringVar(value=str(dflt))
            ttk.Entry(r, textvariable=v, width=10).pack(side="left")
            ttk.Label(r, text=unit, width=6).pack(side="left")
            self.vars[key] = v
        of = ttk.LabelFrame(left, text="Supports", padding=4)
        of.pack(fill="x", pady=2)
        for key, label, d in OPTIONS:
            v = tk.BooleanVar(value=d)
            ttk.Checkbutton(of, text=label, variable=v).pack(anchor="w")
            self.opts[key] = v
        self.run_an = tk.BooleanVar(value=False)
        ttk.Checkbutton(left, text="Run analysis after build",
                        variable=self.run_an).pack(anchor="w", pady=2)

        bf = ttk.Frame(left)
        bf.pack(fill="x", pady=4)
        ttk.Button(bf, text="Preview", command=self.preview).pack(side="left", padx=2)
        ttk.Button(bf, text="Build in STAAD", command=self.build).pack(side="left", padx=2)
        ttk.Button(bf, text="Export .std", command=self.export).pack(side="left", padx=2)

        self.canvas = Preview(right, height=420)
        self.canvas.pack(fill="both", expand=True)
        self.checks = ttk.Label(right, justify="left", font=("TkDefaultFont", 9))
        self.checks.pack(anchor="w", pady=4)
        self.logbox = tk.Text(right, height=9, state="disabled", font=("Consolas", 9))
        self.logbox.pack(fill="x")
        self.preview()

    def log(self, msg):
        self.logbox.config(state="normal")
        self.logbox.insert("end", msg + "\n")
        self.logbox.see("end")
        self.logbox.config(state="disabled")
        self.update_idletasks()

    def _params(self):
        raw = {k: v.get() for k, v in self.vars.items()}
        raw.update({k: v.get() for k, v in self.opts.items()})
        return parse_params(raw)

    def preview(self):
        try:
            p = self._params()
            m = build_model(p)
        except ValueError as e:
            messagebox.showerror("Input error", str(e))
            return None, None
        self.canvas.show(m)
        i = m.info
        self.checks.config(text=(
            f"{i['nodes']} nodes, {i['plates']} plates | flight {i['Lh']:.2f} m plan x "
            f"{i['Hf']:.2f} m rise | DL flight {i['dl_flight']:.2f} kN/m2, landing "
            f"{i['dl_landing']:.2f} | total width {i['Wtot']:.2f} m\n" +
            "   ".join(("OK " if ok else "CHECK ") + t for t, ok in stair_checks(p))))
        return p, m

    def export(self):
        p, m = self.preview()
        if not m:
            return
        path = filedialog.asksaveasfilename(defaultextension=".std",
                                            initialfile="doglegged_stair.std",
                                            filetypes=[("STAAD input", "*.std")])
        if path:
            write_std(m, p, path)
            self.log(f"Wrote {path}")

    def build(self):
        p, m = self.preview()
        if not m:
            return
        try:
            be = StaadBackend(self.log)
            be.connect()
        except Exception as e:
            self.log(f"Could not connect to STAAD: {e}")
            messagebox.showerror("STAAD connection", str(e))
            return
        if not messagebox.askyesno(
                "Build in STAAD",
                "Add the stair to the currently open STAAD model?\n"
                "(Model units must be Meter / kN.)"):
            return
        try:
            be.push(m, p, self.run_an.get())
        except Exception as e:
            self.log(f"ERROR: {e}")
            messagebox.showerror("Build error", str(e))


if __name__ == "__main__":
    if "--std" in sys.argv:
        out = sys.argv[sys.argv.index("--std") + 1]
        prm = parse_params({**{k: d for _, k, _, _, d in FIELDS},
                            **{k: d for k, _, d in OPTIONS}})
        write_std(build_model(prm), prm, out)
        print("wrote", out)
    elif HAVE_TK:
        App().mainloop()
    else:
        sys.exit("tkinter not available - install it (e.g. python3-tk) or use --std")
