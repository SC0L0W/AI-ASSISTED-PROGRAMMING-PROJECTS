#!/usr/bin/env python3
"""
generate_staad_truss.py
------------------------
Generates a STAAD.Pro "STAAD SPACE" command (.std) file for a parametric
single-peak (triangular / "fan") roof truss: flat bottom chord, two straight
top-chord slopes meeting at one central apex, and a "fan" diagonal pattern
where every panel gets exactly one diagonal, pointing toward the nearer
support (so the two panels flanking the apex, each with their own diagonal,
create the denser triangulated look near the middle). This matches the
classic STAAD "DXF import" truss layout. Includes:

  - JOINT COORDINATES
  - MEMBER INCIDENCES
  - GROUP DEFINITION (top/bottom chord, verticals, diagonals)
  - SUPPORTS
  - MATERIAL definition
  - MEMBER PROPERTY (angle sections, editable)
  - MEMBER TRUSS (axial-only members)
  - Dead / Live / Wind load cases
  - Load combinations
  - PERFORM ANALYSIS + PRINT commands
  - Steel design PARAMETER block (AISC)

Edit the values in the `TrussConfig` block at the bottom (or import this
module and call `build_truss()` yourself) to match your project, then run:

    python generate_staad_truss.py

This produces `truss_output.std` in the current directory.

NOTE: This is a general-purpose generator to speed up building STAAD
input files. Always review the generated geometry, section sizes and
loads in STAAD.Pro before using the model for design.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import List, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class TrussConfig:
    # --- Geometry ---
    span: float = 12.0            # overall span, m (support to support)
    num_panels: int = 8           # number of bottom-chord panels; EVEN so the
                                   # apex lands exactly on a node at mid-span
    peak_height: float = 2.0      # apex height above the (flat) bottom chord, m
    unit_length: str = "METER"
    unit_force: str = "KN"

    # --- Support ---
    support_type: str = "PINNED"  # PINNED, FIXED, or FIXED BUT ... (STAAD syntax)

    # --- Job info ---
    structure_type: str = "STAAD TRUSS"  # STAAD's structure-type keyword, e.g.
                                          # "STAAD TRUSS" or "STAAD SPACE"
    job_title: str = "PARAMETRIC ROOF TRUSS"
    engineer: str = "ENGINEER"

    # --- Leftover default material (STAAD adds this to new jobs; set False
    #     to omit it) ---
    include_default_material1: bool = True

    # --- Section sizes (STAAD "US (AISC 2023).DB3" ANGLE table labels) ---
    top_chord_section: str = "L2-1/2X2-1/2X3/16"
    bottom_chord_section: str = "L2-1/2X2-1/2X3/16"
    vertical_section: str = "L2-1/2X2-1/2X3/16"
    diagonal_section: str = "L2X2X1/8"

    # --- Material ---
    steel_fy: float = 248000.0    # kPa (36 ksi in SI-ish STAAD units, matches sample)
    steel_fu: float = 400000.0

    # --- Loads (kN/m on chord members, matches sample UNI PY / UNI Y syntax) ---
    dead_load_chord: float = -1.0     # UNI PY, kN/m, applied to top & bottom chord
    live_load_top_chord: float = -1.0 # UNI PY, kN/m, applied to top chord only
    wind1_left: float = 6.0           # UNI Y, kN/m, transverse wind on left top chord slope
    wind1_right: float = 9.0          # UNI Y, kN/m, transverse wind on right top chord slope
    wind2_top_chord: float = 8.0      # UNI Y, kN/m, longitudinal wind on top chord


# ---------------------------------------------------------------------------
# Geometry builder
# ---------------------------------------------------------------------------

class TrussBuilder:
    """
    Builds a symmetric, single-peak "fan" truss:

        top chord    : two straight slopes, rising linearly from 0 at each
                        support to `peak_height` at the central apex node
        bottom chord : flat, at y = 0
        verticals    : connect matching bottom/top panel points (interior only)
        diagonals    : one per panel; panels left of the apex get a diagonal
                        from their bottom-right corner to their top-left
                        corner, panels right of the apex get one from their
                        bottom-left corner to their top-right corner (so
                        diagonals always lean toward the nearer support).
                        The two end panels need no diagonal - the support
                        node ties top and bottom chord together directly,
                        forming a stable triangle on its own.

    Joint numbering:
        Bottom chord joints : 1 .. (num_panels+1)
        Top chord joints    : (num_panels+2) .. (num_panels+2 + num_panels-2)
                               i.e. interior points only; the two end joints
                               of the bottom chord (supports) double as the
                               truss end points.
    """

    def __init__(self, cfg: TrussConfig):
        self.cfg = cfg
        self.joints: List[Tuple[int, float, float, float]] = []
        self.bottom_joint_ids: List[int] = []
        self.top_joint_ids: List[int] = []  # same length as bottom_joint_ids;
                                             # top_joint_ids[0] and [-1] equal
                                             # bottom_joint_ids[0] and [-1]
        self.member_id_counters = {"top": 100, "bottom": 200, "vertical": 300, "diagonal": 400}
        self.members = {"top": [], "bottom": [], "vertical": [], "diagonal": []}

    # -- joints -------------------------------------------------------
    def _panel_x(self, i: int) -> float:
        return self.cfg.span * i / self.cfg.num_panels

    def _top_height(self, x: float) -> float:
        """Linear tent function: 0 at each support, `peak_height` at mid-span."""
        cfg = self.cfg
        half = cfg.span / 2.0
        dist_from_center = abs(x - half)
        frac = 1.0 - (dist_from_center / half if half else 0.0)
        return cfg.peak_height * frac

    def build_geometry(self):
        cfg = self.cfg
        n = cfg.num_panels
        jid = 1

        # bottom chord joints (0 .. n)
        for i in range(n + 1):
            x = self._panel_x(i)
            self.joints.append((jid, x, 0.0, 0.0))
            self.bottom_joint_ids.append(jid)
            jid += 1

        # top chord joints: ends reuse bottom chord end joints; interior points are new
        self.top_joint_ids = [None] * (n + 1)
        self.top_joint_ids[0] = self.bottom_joint_ids[0]
        self.top_joint_ids[n] = self.bottom_joint_ids[n]
        for i in range(1, n):
            x = self._panel_x(i)
            y = self._top_height(x)
            self.joints.append((jid, x, y, 0.0))
            self.top_joint_ids[i] = jid
            jid += 1

        return self

    # -- members --------------------------------------------------------
    def _next_id(self, kind: str) -> int:
        val = self.member_id_counters[kind]
        self.member_id_counters[kind] += 1
        return val

    def build_members(self):
        n = self.cfg.num_panels

        # bottom chord: consecutive bottom joints
        for i in range(n):
            a, b = self.bottom_joint_ids[i], self.bottom_joint_ids[i + 1]
            mid = self._next_id("bottom")
            self.members["bottom"].append((mid, a, b))

        # top chord: consecutive top joints
        for i in range(n):
            a, b = self.top_joint_ids[i], self.top_joint_ids[i + 1]
            mid = self._next_id("top")
            self.members["top"].append((mid, a, b))

        # verticals: interior panel points only (i = 1 .. n-1)
        for i in range(1, n):
            a, b = self.bottom_joint_ids[i], self.top_joint_ids[i]
            mid = self._next_id("vertical")
            self.members["vertical"].append((mid, a, b))

        # diagonals: fan pattern, one per interior panel, direction flips at the apex.
        # Panel k spans joint index (k-1) to k, for k = 1 .. n.
        #   k == 1 or k == n  -> no diagonal (support node already ties the
        #                        end panel into a stable triangle)
        #   k <= half         -> diagonal from bottom(k) to top(k-1)   [left of apex]
        #   k >  half         -> diagonal from bottom(k-1) to top(k)  [right of apex]
        half = n // 2
        for k in range(1, n + 1):
            if k == 1 or k == n:
                continue
            if k <= half:
                a, b = self.bottom_joint_ids[k], self.top_joint_ids[k - 1]
            else:
                a, b = self.bottom_joint_ids[k - 1], self.top_joint_ids[k]
            mid = self._next_id("diagonal")
            self.members["diagonal"].append((mid, a, b))

        return self

    def support_joints(self) -> Tuple[int, int]:
        return self.bottom_joint_ids[0], self.bottom_joint_ids[-1]


# ---------------------------------------------------------------------------
# STAAD text formatting helpers
# ---------------------------------------------------------------------------

def fmt_num(x: float) -> str:
    """Format a coordinate/number the way STAAD examples do: trim trailing
    zeros, no unnecessary decimals."""
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    s = f"{x:.5f}".rstrip("0").rstrip(".")
    return s


def chunk_lines(items: List[str], per_line: int = 3) -> List[str]:
    lines = []
    for i in range(0, len(items), per_line):
        lines.append(" ".join(items[i:i + per_line]))
    return lines


def id_range_or_list(ids: List[int]) -> str:
    """Collapse a consecutive run of ids into 'first TO last', else list them."""
    if not ids:
        return ""
    ids = sorted(ids)
    if ids == list(range(ids[0], ids[-1] + 1)):
        return f"{ids[0]} TO {ids[-1]}"
    return " ".join(str(i) for i in ids)


# ---------------------------------------------------------------------------
# Main .std file assembly
# ---------------------------------------------------------------------------

def build_truss(cfg: TrussConfig) -> str:
    tb = TrussBuilder(cfg).build_geometry().build_members()
    n = cfg.num_panels

    top_ids = [m[0] for m in tb.members["top"]]
    bottom_ids = [m[0] for m in tb.members["bottom"]]
    vert_ids = [m[0] for m in tb.members["vertical"]]
    diag_ids = [m[0] for m in tb.members["diagonal"]]

    # split top chord into "left half" / "right half" groups for wind loads
    half = len(top_ids) // 2
    top_left_ids = top_ids[:half] if half else top_ids
    top_right_ids = top_ids[half:] if half else []

    sup_a, sup_b = tb.support_joints()

    lines: List[str] = []
    add = lines.append

    # -- header ----------------------------------------------------------
    title = cfg.job_title
    if not title.upper().startswith(cfg.structure_type.upper()):
        title = f"{cfg.structure_type} {title}"
    add(title)
    add("START JOB INFORMATION")
    add(f"ENGINEER DATE {date.today():%d-%b-%y}")
    add("END JOB INFORMATION")
    add("SET Y UP")
    add("INPUT WIDTH 79")
    add(f"UNIT {cfg.unit_length} {cfg.unit_force}")

    # -- joint coordinates -------------------------------------------------
    add("JOINT COORDINATES")
    coord_tokens = []
    for jid, x, y, z in tb.joints:
        coord_tokens.append(f"{jid} {fmt_num(x)} {fmt_num(y)} {fmt_num(z)};")
    for line in chunk_lines(coord_tokens, per_line=3):
        add(line)

    # -- member incidences ---------------------------------------------------
    add("MEMBER INCIDENCES")
    inc_tokens = []
    for kind in ("top", "bottom", "vertical", "diagonal"):
        for mid, a, b in tb.members[kind]:
            inc_tokens.append(f"{mid} {a} {b};")
    for line in chunk_lines(inc_tokens, per_line=8):
        add(line)

    # -- groups -----------------------------------------------------------
    add("START GROUP DEFINITION")
    add("GEOMETRY")
    add("MEMBER")
    add(f"_TOPCHORD {id_range_or_list(top_ids)}")
    add(f"_BOTTOMCHORD {id_range_or_list(bottom_ids)}")
    add(f"_VERTICALWEB {id_range_or_list(vert_ids)}")
    add(f"_DIAGONALWEB {id_range_or_list(diag_ids)}")
    if top_left_ids:
        add(f"_TOPCHORDLEFT {id_range_or_list(top_left_ids)}")
    if top_right_ids:
        add(f"_TOPCHORDRIGHT {id_range_or_list(top_right_ids)}")
    add("END GROUP DEFINITION")

    # -- supports -----------------------------------------------------------
    add("SUPPORTS")
    add(f"{sup_a} {sup_b} {cfg.support_type}")

    # -- material --------------------------------------------------------
    add("*==========================================================")
    add("* MATERIAL")
    add("*==========================================================")
    add("DEFINE MATERIAL START")
    if cfg.include_default_material1:
        add("ISOTROPIC MATERIAL1")
        add("E 2e+08")
        add("POISSON 0.3")
        add("DENSITY 76.8195")
        add("ALPHA 1.2e-05")
        add("G 7.69231e+07")
    add("ISOTROPIC STEEL")
    add("E 1.99947e+08")
    add("POISSON 0.3")
    add("DENSITY 76.8191")
    add("ALPHA 6.5e-06")
    add("DAMP 0.03")
    add("G 7.7221e+07")
    add("TYPE STEEL")
    add(f"STRENGTH FY {fmt_num(cfg.steel_fy)} FU {fmt_num(cfg.steel_fu)} RY 1.5 RT 1.2")
    add("END DEFINE MATERIAL")

    # -- properties --------------------------------------------------------
    add("MEMBER PROPERTY 'US (AISC 2023).DB3'")
    add(f"_TOPCHORD TABLE 'ANGLE' LD '{cfg.top_chord_section}'")
    add(f"_BOTTOMCHORD TABLE 'ANGLE' LD '{cfg.bottom_chord_section}'")
    add(f"_VERTICALWEB TABLE 'ANGLE' LD '{cfg.vertical_section}'")
    add(f"_DIAGONALWEB TABLE 'ANGLE' LD '{cfg.diagonal_section}'")
    add("CONSTANTS")
    add("MATERIAL STEEL ALL")

    # -- truss member designation ------------------------------------------
    add("*==========================================================")
    add("* TRUSS MEMBERS - AXIAL ONLY")
    add("*==========================================================")
    add("MEMBER TRUSS")
    all_member_ids = top_ids + bottom_ids + vert_ids + diag_ids
    for line in chunk_lines([id_range_or_list(all_member_ids)], per_line=1):
        add(line)

    # -- load 1: dead --------------------------------------------------------
    add("*==========================================================")
    add("* LOAD 1 - DEAD LOAD")
    add("*==========================================================")
    add("LOAD 1 LOADTYPE Dead  TITLE DEAD LOAD")
    add("SELFWEIGHT Y -1")
    add("MEMBER LOAD")
    add(f"_TOPCHORD UNI PY {fmt_num(cfg.dead_load_chord)}")
    add(f"_BOTTOMCHORD UNI PY {fmt_num(cfg.dead_load_chord)}")

    # -- load 2: live --------------------------------------------------------
    add("*==========================================================")
    add("* LOAD 2 - ROOF LIVE LOAD")
    add("*==========================================================")
    add("LOAD 2 LOADTYPE Live  TITLE ROOF LIVE LOAD")
    add("MEMBER LOAD")
    add(f"_TOPCHORD UNI PY {fmt_num(cfg.live_load_top_chord)}")

    # -- load 3: transverse wind ----------------------------------------------
    add("*==========================================================")
    add("* LOAD 3 - TRANSVERSE WIND")
    add("*==========================================================")
    add("LOAD 3 LOADTYPE Wind  TITLE WIND 1")
    add("MEMBER LOAD")
    if top_left_ids:
        add(f"_TOPCHORDLEFT UNI Y {fmt_num(cfg.wind1_left)}")
    if top_right_ids:
        add(f"_TOPCHORDRIGHT UNI Y {fmt_num(cfg.wind1_right)}")

    # -- load 4: longitudinal wind --------------------------------------------
    add("*==========================================================")
    add("* LOAD 4 - LONGITUDINAL WIND")
    add("*==========================================================")
    add("LOAD 4 LOADTYPE Wind  TITLE WIND 2")
    add("MEMBER LOAD")
    add(f"_TOPCHORD UNI Y {fmt_num(cfg.wind2_top_chord)}")

    # -- combinations ---------------------------------------------------------
    add("*==========================================================")
    add("* LOAD COMBINATIONS")
    add("*==========================================================")
    combos = [
        (5, "1.0D", [(1, 1.0)]),
        (6, "1.0D + 1.0L", [(1, 1.0), (2, 1.0)]),
        (7, "1.0D + 0.75L + 0.45W1", [(1, 1.0), (2, 0.75), (3, 0.45)]),
        (8, "1.0D + 0.75L + 0.45W2", [(1, 1.0), (2, 0.75), (4, 0.45)]),
        (9, "1.0D + 0.60W1", [(1, 1.0), (3, 0.6)]),
        (10, "1.0D + 0.60W2", [(1, 1.0), (4, 0.6)]),
        (11, "0.60D + 0.60W1", [(1, 0.6), (3, 0.6)]),
        (12, "0.60D + 0.60W2", [(1, 0.6), (4, 0.6)]),
    ]
    for cid, title, terms in combos:
        add(f"LOAD COMB {cid} {title}")
        add(" ".join(f"{lc} {fmt_num(fac)}" for lc, fac in terms))

    # -- analysis --------------------------------------------------------
    add("*==========================================================")
    add("* ANALYSIS")
    add("*==========================================================")
    add("PERFORM ANALYSIS")
    add("PRINT SUPPORT REACTION")
    add("PRINT MEMBER FORCES")
    add("PRINT JOINT DISPLACEMENTS")

    # -- steel design ---------------------------------------------------------
    add("*==========================================================")
    add("* STEEL DESIGN")
    add("*==========================================================")
    add("PARAMETER 1")
    add("CODE AISC UNIFIED 2010")
    add(f"FYLD {fmt_num(cfg.steel_fy)} ALL")
    add(f"FU {fmt_num(cfg.steel_fu)} ALL")
    add("TRACK 0 ALL")
    add("CHECK CODE ALL")
    add("FINISH")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    config = TrussConfig(
        span=16.0,
        num_panels=8,
        peak_height=2.0,
        structure_type="STAAD TRUSS",
        job_title="DXF IMPORT OF DRAWING1",
        include_default_material1=True,
    )
    output_text = build_truss(config)
    out_path = "truss_output.std"
    with open(out_path, "w") as f:
        f.write(output_text)
    print(f"Wrote {out_path} ({len(output_text.splitlines())} lines)")
