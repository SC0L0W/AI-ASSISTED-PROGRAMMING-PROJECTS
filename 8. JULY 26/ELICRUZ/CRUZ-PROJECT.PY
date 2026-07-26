#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECTANGULAR CONCRETE TANK DESIGNER  (PCA method, IS003.06D - Munshi)
===================================================================
Self-contained desktop app: pick the PCA plate cases, enter the tank, and it
computes wall/base-slab reinforcement, crack control, shear, bearing and
flotation, with a live section + pressure-diagram view.

Only the Python standard library is required (tkinter ships with Python).
Run:  python cruz_tank_design.py

Coefficients (PCA Chapter 2, all 10 plate cases) are embedded below at the
seven governing design locations plus the two governing shear locations.
Prepared for Engr. Elival Cruz - Evolution Homes Corporation.
"""
import math
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    HAVE_TK = True
except Exception:
    HAVE_TK = False

# ---------------------------------------------------------------------------
# EMBEDDED PCA CHAPTER-2 COEFFICIENTS
# COEF[case][b/a] = [Mx(BOT,0.5b), Mx(BOT,0.4b), Mx(0.5a,0.5b),
#                    My(0.5a,END), My(0.7a,END), My(0.5a,0.5b), My(TOP,0.5b)]
# SHEAR[case][b/a] = [Cs bottom-edge midpoint, Cs side-edge maximum]
# Moment = coef * q * a^2 / 1000 ;  Shear = Cs * q * a
# ---------------------------------------------------------------------------
COEF = {
  1: {4.0: [0, 0, 61, -62, -45, 13, 0], 3.0: [0, 0, 57, -62, -45, 15, 0], 2.5: [0, 0, 52, -62, -45, 17, 0], 2.0: [0, 0, 42, -60, -43, 20, 0], 1.75: [0, 0, 36, -57, -41, 20, 0], 1.5: [0, 0, 28, -52, -37, 21, 0], 1.25: [0, 0, 19, -45, -32, 19, 0], 1.0: [0, 0, 11, -35, -24, 16, 0], 0.75: [0, 0, 5, -22, -14, 11, 0], 0.5: [0, 0, 1, -11, -6, 5, 0]},
  2: {4.0: [0, 0, 56, -190, -244, 57, 89], 3.0: [0, 0, 48, -140, -169, 50, 74], 2.5: [0, 0, 42, -115, -131, 44, 62], 2.0: [0, 0, 33, -90, -94, 37, 46], 1.75: [0, 0, 28, -77, -77, 32, 37], 1.5: [0, 0, 22, -63, -59, 28, 27], 1.25: [0, 0, 16, -50, -43, 22, 18], 1.0: [0, 0, 9, -36, -28, 17, 10], 0.75: [0, 0, 4, -23, -15, 11, 4], 0.5: [0, 0, 1, -11, -6, 5, 1]},
  3: {4.0: [-149, -145, -6, -56, -75, 4, 15], 3.0: [-127, -122, 5, -55, -71, 10, 24], 2.5: [-109, -104, 11, -53, -67, 14, 28], 2.0: [-86, -82, 15, -50, -59, 16, 28], 1.75: [-73, -70, 16, -47, -52, 17, 25], 1.5: [-61, -57, 15, -43, -44, 17, 21], 1.25: [-48, -45, 13, -37, -35, 15, 16], 1.0: [-35, -33, 9, -30, -25, 13, 9], 0.75: [-23, -21, 5, -21, -15, 10, 4], 0.5: [-11, -11, 1, -10, -6, 5, 1]},
  4: {4.0: [-67, -67, 29, -37, -29, 6, 0], 3.0: [-66, -66, 29, -37, -29, 7, 0], 2.5: [-65, -64, 28, -37, -29, 8, 0], 2.0: [-62, -60, 26, -37, -29, 9, 0], 1.75: [-59, -57, 24, -36, -29, 11, 0], 1.5: [-53, -51, 21, -36, -28, 12, 0], 1.25: [-45, -43, 16, -33, -25, 13, 0], 1.0: [-35, -33, 11, -29, -21, 12, 0], 0.75: [-23, -21, 5, -20, -14, 10, 0], 0.5: [-11, -11, 1, -10, -6, 5, 0]},
  5: {4.0: [0, 0, 62, 0, 0, 13, 0], 3.0: [0, 0, 59, 0, 0, 14, 0], 2.5: [0, 0, 56, 0, 0, 16, 0], 2.0: [0, 0, 50, 0, 0, 18, 0], 1.75: [0, 0, 45, 0, 0, 20, 0], 1.5: [0, 0, 39, 0, 0, 21, 0], 1.25: [0, 0, 31, 0, 0, 22, 0], 1.0: [0, 0, 22, 0, 0, 22, 0], 0.75: [0, 0, 12, 0, 0, 19, 0], 0.5: [0, 0, 5, 0, 0, 12, 0]},
  6: {4.0: [0, 0, 122, -125, -105, 27, 0], 3.0: [0, 0, 114, -125, -105, 31, 0], 2.5: [0, 0, 103, -123, -104, 35, 0], 2.0: [0, 0, 85, -119, -100, 39, 0], 1.75: [0, 0, 71, -114, -96, 41, 0], 1.5: [0, 0, 55, -105, -89, 41, 0], 1.25: [0, 0, 38, -90, -77, 38, 0], 1.0: [0, 0, 22, -70, -60, 32, 0], 0.75: [0, 0, 9, -45, -40, 22, 0], 0.5: [0, 0, 3, -21, -20, 10, 0]},
  7: {4.0: [0, 0, 106, -518, -722, 159, 266], 3.0: [0, 0, 87, -368, -496, 137, 223], 2.5: [0, 0, 72, -293, -384, 118, 188], 2.0: [0, 0, 55, -219, -274, 95, 144], 1.75: [0, 0, 45, -182, -221, 81, 119], 1.5: [0, 0, 34, -145, -171, 66, 93], 1.25: [0, 0, 24, -110, -124, 51, 68], 1.0: [0, 0, 14, -76, -82, 36, 44], 0.75: [0, 0, 7, -46, -47, 22, 25], 0.5: [0, 0, 2, -21, -21, 10, 11]},
  8: {4.0: [-433, -417, -71, -152, -253, 4, 54], 3.0: [-351, -333, -29, -148, -241, 27, 89], 2.5: [-286, -269, -6, -142, -224, 39, 102], 2.0: [-206, -193, 14, -129, -192, 47, 102], 1.75: [-164, -153, 20, -119, -170, 47, 94], 1.5: [-124, -116, 22, -105, -142, 44, 81], 1.25: [-87, -82, 20, -87, -111, 39, 63], 1.0: [-56, -53, 14, -66, -78, 31, 43], 0.75: [-32, -30, 8, -43, -46, 21, 25], 0.5: [-14, -13, 3, -21, -21, 10, 11]},
  9: {4.0: [-125, -125, 63, -79, -75, 13, 0], 3.0: [-124, -123, 62, -79, -75, 14, 0], 2.5: [-122, -119, 60, -79, -75, 16, 0], 2.0: [-115, -111, 55, -78, -75, 21, 0], 1.75: [-107, -102, 51, -78, -74, 23, 0], 1.5: [-95, -90, 43, -76, -72, 26, 0], 1.25: [-77, -73, 33, -71, -67, 28, 0], 1.0: [-55, -52, 21, -60, -56, 26, 0], 0.75: [-32, -30, 10, -42, -39, 20, 0], 0.5: [-14, -13, 3, -21, -20, 10, 0]},
  10: {4.0: [0, 0, 123, 0, 0, 26, 0], 3.0: [0, 0, 118, 0, 0, 29, 0], 2.5: [0, 0, 112, 0, 0, 32, 0], 2.0: [0, 0, 100, 0, 0, 37, 0], 1.75: [0, 0, 91, 0, 0, 40, 0], 1.5: [0, 0, 78, 0, 0, 43, 0], 1.25: [0, 0, 63, 0, 0, 45, 0], 1.0: [0, 0, 44, 0, 0, 44, 0], 0.75: [0, 0, 25, 0, 0, 38, 0], 0.5: [0, 0, 9, 0, 0, 25, 0]},
}
SHEAR = {
  1: {4.0: [0.33, 0.41], 3.0: [0.33, 0.41], 2.5: [0.32, 0.41], 2.0: [0.3, 0.4], 1.75: [0.28, 0.39], 1.5: [0.26, 0.38], 1.25: [0.23, 0.35], 1.0: [0.2, 0.32], 0.75: [0.16, 0.26], 0.5: [0.11, 0.2]},
  2: {4.0: [0.39, 1.14], 3.0: [0.36, 0.76], 2.5: [0.33, 0.58], 2.0: [0.31, 0.41], 1.75: [0.28, 0.39], 1.5: [0.26, 0.37], 1.25: [0.23, 0.35], 1.0: [0.19, 0.31], 0.75: [0.15, 0.26], 0.5: [0.11, 0.2]},
  3: {4.0: [0.5, 0.38], 3.0: [0.5, 0.37], 2.5: [0.48, 0.33], 2.0: [0.45, 0.27], 1.75: [0.43, 0.26], 1.5: [0.4, 0.26], 1.25: [0.36, 0.25], 1.0: [0.32, 0.24], 0.75: [0.26, 0.22], 0.5: [0.19, 0.17]},
  4: {4.0: [0.4, 0.26], 3.0: [0.4, 0.26], 2.5: [0.4, 0.26], 2.0: [0.4, 0.27], 1.75: [0.39, 0.26], 1.5: [0.38, 0.26], 1.25: [0.36, 0.25], 1.0: [0.32, 0.24], 0.75: [0.26, 0.22], 0.5: [0.2, 0.17]},
  5: {4.0: [0.33, 0.2], 3.0: [0.33, 0.2], 2.5: [0.32, 0.2], 2.0: [0.32, 0.2], 1.75: [0.31, 0.2], 1.5: [0.29, 0.2], 1.25: [0.27, 0.2], 1.0: [0.25, 0.19], 0.75: [0.21, 0.18], 0.5: [0.15, 0.14]},
  6: {4.0: [0.5, 0.74], 3.0: [0.48, 0.74], 2.5: [0.47, 0.74], 2.0: [0.43, 0.72], 1.75: [0.4, 0.7], 1.5: [0.36, 0.67], 1.25: [0.31, 0.6], 1.0: [0.24, 0.52], 0.75: [0.18, 0.4], 0.5: [0.12, 0.26]},
  7: {4.0: [0.68, 3.74], 3.0: [0.61, 2.61], 2.5: [0.52, 2.1], 2.0: [0.45, 1.45], 1.75: [0.4, 1.3], 1.5: [0.35, 1.0], 1.25: [0.3, 0.78], 1.0: [0.24, 0.58], 0.75: [0.18, 0.4], 0.5: [0.12, 0.26]},
  8: {4.0: [1.03, 1.68], 3.0: [1.01, 1.59], 2.5: [0.95, 1.47], 2.0: [0.85, 1.26], 1.75: [0.75, 1.12], 1.5: [0.66, 0.95], 1.25: [0.56, 0.77], 1.0: [0.45, 0.58], 0.75: [0.33, 0.4], 0.5: [0.22, 0.25]},
  9: {4.0: [0.62, 0.55], 3.0: [0.62, 0.56], 2.5: [0.63, 0.56], 2.0: [0.62, 0.56], 1.75: [0.61, 0.56], 1.5: [0.58, 0.56], 1.25: [0.53, 0.53], 1.0: [0.45, 0.48], 0.75: [0.34, 0.39], 0.5: [0.22, 0.26]},
  10: {4.0: [0.5, 0.37], 3.0: [0.49, 0.37], 2.5: [0.48, 0.37], 2.0: [0.46, 0.37], 1.75: [0.45, 0.37], 1.5: [0.42, 0.36], 1.25: [0.39, 0.36], 1.0: [0.34, 0.34], 0.75: [0.27, 0.3], 0.5: [0.18, 0.23]},
}

CASE_EDGES = {
    1: ("triangular", "HINGED", "FIXED", "HINGED"),
    2: ("triangular", "FREE", "FIXED", "HINGED"),
    3: ("triangular", "FREE", "FIXED", "FIXED"),
    4: ("triangular", "HINGED", "FIXED", "FIXED"),
    5: ("triangular", "HINGED", "HINGED", "HINGED"),
    6: ("uniform", "HINGED", "FIXED", "HINGED"),
    7: ("uniform", "FREE", "FIXED", "HINGED"),
    8: ("uniform", "FREE", "FIXED", "FIXED"),
    9: ("uniform", "HINGED", "FIXED", "FIXED"),
    10: ("uniform", "HINGED", "HINGED", "HINGED"),
}
BA_TABLE = [4.0, 3.0, 2.5, 2.0, 1.75, 1.5, 1.25, 1.0, 0.75, 0.5]

# ACI 350 / PCA factors
SD_FLEX = 1.3      # sanitary durability factor, flexure
FF = 1.7           # lateral liquid/earth load factor (PCA p.1-5 Mod.1)
PHI_F = 0.9        # flexure
PHI_V = 0.85       # shear
ST_RATIO = 0.003   # shrinkage & temperature steel ratio
MAX_SPACING = 300  # mm
Z_LIMIT = 115      # crack-control z (kips/in)
FS_RATIO = 0.6     # service steel stress / fy


def use_table_ba(ratio):
    for v in sorted(BA_TABLE):
        if ratio <= v + 1e-9:
            return v
    return max(BA_TABLE)


def design(inp, tri_case, uni_case):
    """Full wall + slab + stability calc. Returns a results dict."""
    d = inp
    r = {}
    phi = math.radians(d["phi"])
    Ka = (1 - math.sin(phi)) / (1 + math.sin(phi)) if d["phi"] > 0 else 1.0
    K0 = 1 - math.sin(phi)
    k = Ka if d["kopt"] == "Ka" else K0
    a = d["HL"] + d["fb"]
    r["Ka"], r["K0"], r["k"], r["a"] = Ka, K0, k, a
    r["q_earth"] = k * d["gs"] * a
    r["q_surch"] = k * d["qs"]
    r["q_liquid"] = d["gw"] * d["HL"]

    # governing panel b/a
    panels = {"Long wall C1": d["L1"], "Long wall C2": d["L2"],
              "Long wall C3": d["L3"], "End wall": d["B"]}
    r["ba"] = {n: (use_table_ba(L / a) if a > 0 else 0) for n, L in panels.items()}
    gov = max(r["ba"].values()) if r["ba"] else 1.0
    r["gov"] = gov

    ct = COEF.get(tri_case, {}).get(gov)
    cu = COEF.get(uni_case, {}).get(gov)
    if ct is None or cu is None:
        r["error"] = "No embedded coefficients for that case / b-a."
        return r

    # Condition 2 (earth + surcharge) superposed at the 7 locations
    F = [ct[i] * r["q_earth"] * a * a / 1000.0 + cu[i] * r["q_surch"] * a * a / 1000.0
         for i in range(7)]
    r["M_cond2"] = max(abs(min(F)), abs(max(F)))
    # Condition 1 (liquid out): Mx at base, use liquid triangle height = H_L
    r["M_cond1"] = abs(ct[0] * r["q_liquid"] * d["HL"] * d["HL"] / 1000.0)
    r["M"] = max(r["M_cond2"], r["M_cond1"])
    r["Mu"] = FF * r["M"]
    r["M_req"] = SD_FLEX * r["Mu"]

    fc, fy = d["fc"], d["fy"]
    db = d["db"]
    d_eff = d["tw"] * 1000 - d["cover_e"] - db / 2.0
    r["d_eff"] = d_eff
    Rn = r["M_req"] * 1e6 / (PHI_F * 1000 * d_eff ** 2)
    rho = 0.85 * fc / fy * (1 - math.sqrt(max(0.0, 1 - 2 * Rn / (0.85 * fc))))
    r["As_flex"] = rho * 1000 * d_eff
    r["As_min"] = ST_RATIO * 1000 * d["tw"] * 1000
    r["As_design"] = max(r["As_flex"], r["As_min"])
    r["gov_by"] = "flexure" if r["As_flex"] >= r["As_min"] else "shrinkage & temp"

    Ab = math.pi * db ** 2 / 4.0
    r["Ab"] = Ab
    sp_area = 1000 * Ab / r["As_design"]
    dc = (min(d["cover_i"], 50.8) + db / 2.0) / 25.4
    fs = FS_RATIO * fy / 6.895
    fs_act = max(fs * min(1.0, r["As_flex"] / r["As_design"]), 1.0)
    bw = min((Z_LIMIT ** 3 / (2 * dc ** 2 * fs_act ** 3)) * 25.4, 10000.0)
    r["bw"] = bw
    r["spacing"] = min(math.floor(sp_area / 25) * 25, MAX_SPACING, math.floor(bw / 25) * 25)
    if math.floor(sp_area / 25) * 25 <= MAX_SPACING and math.floor(sp_area / 25) * 25 <= math.floor(bw / 25) * 25:
        r["sp_gov"] = "steel area"
    elif MAX_SPACING <= math.floor(bw / 25) * 25:
        r["sp_gov"] = "max spacing"
    else:
        r["sp_gov"] = "CRACK CONTROL"

    # shear
    sht = SHEAR.get(tri_case, {}).get(gov, [0, 0])
    shu = SHEAR.get(uni_case, {}).get(gov, [0, 0])
    Vb = sht[0] * r["q_earth"] * a + shu[0] * r["q_surch"] * a
    Vs = sht[1] * r["q_earth"] * a + shu[1] * r["q_surch"] * a
    r["Vu"] = FF * max(Vb, Vs)
    r["phiVc"] = PHI_V * 0.17 * math.sqrt(fc) * 1000 * d_eff / 1000.0
    r["shear_ok"] = r["Vu"] <= r["phiVc"]

    # layout recommendation
    tw_mm = d["tw"] * 1000
    reversal = (min(r["M_cond1"], r["M_cond2"]) / max(r["M_cond1"], r["M_cond2"])
                if max(r["M_cond1"], r["M_cond2"]) > 0 else 0)
    r["reversal"] = reversal
    if tw_mm > 250:
        r["layout"], r["layout_why"] = "Double face", "wall > 250 mm (ACI 318 two-layer rule)"
    elif d["HL"] > 0:
        r["layout"], r["layout_why"] = "Double face", "liquid-retaining (ACI 350 face crack control)"
    elif reversal > 0.25:
        r["layout"], r["layout_why"] = "Double face", "significant moment reversal (both faces in tension)"
    elif r["As_flex"] >= r["As_min"]:
        r["layout"], r["layout_why"] = "Double face", "flexure governs (centered mat costs more steel)"
    else:
        r["layout"], r["layout_why"] = "Single face", "thin, non-liquid wall, S&T governs"
    r["provide"] = f"{int(db)} mm @ {r['spacing']} mm, both directions" + \
                   (" (both faces)" if r["layout"] == "Double face" else " (single centered mat)")

    # ---- base slab & stability ----
    tw, tb, tt = d["tw"], d["tb"], d["tt"]
    extL = d["L1"] + d["L2"] + d["L3"] + 4 * tw
    extW = d["B"] + 2 * tw
    area = (extL + 2 * d["heel"]) * (extW + 2 * d["heel"])
    r["ext_len"], r["ext_wid"], r["base_area"] = extL, extW, area
    gc = d["gc"]
    W_walls = 2 * (extL + extW) * tw * a * gc
    W_part = 2 * d["B"] * tw * a * gc
    W_base = area * tb * gc
    W_top = extL * extW * tt * gc
    W_soil = extL * extW * d["cover"] * d["gs"]
    W_liq = (d["L1"] + d["L2"] + d["L3"]) * d["B"] * d["HL"] * d["gw"]
    W_empty = W_walls + W_part + W_base + W_top + W_soil
    W_full = W_empty + W_liq
    r["bearing"] = W_full / area if area else 0
    r["q_all"] = d["q_all"]
    r["bearing_ok"] = r["bearing"] <= d["q_all"]

    # net slab pressure & steel (short span = B, one-way strip, fixed ends)
    up = r["bearing"]
    dn_sw = tb * gc
    dn_liq = d["HL"] * d["gw"]
    net_full = up - dn_sw - dn_liq
    net_empty = W_empty / area - dn_sw
    r["net_press"] = max(abs(net_full), abs(net_empty))
    wu = FF * r["net_press"]
    Ls = d["B"]
    M_slab = wu * Ls * Ls / 12.0
    r["M_slab_req"] = SD_FLEX * M_slab
    d_slab = tb * 1000 - d["cover_e"] - db / 2.0
    Rn2 = r["M_slab_req"] * 1e6 / (PHI_F * 1000 * d_slab ** 2)
    rho2 = 0.85 * fc / fy * (1 - math.sqrt(max(0.0, 1 - 2 * Rn2 / (0.85 * fc))))
    As_slab_flex = rho2 * 1000 * d_slab
    As_slab_min = ST_RATIO * 1000 * tb * 1000
    r["As_slab"] = max(As_slab_flex, As_slab_min)
    r["slab_spacing"] = min(math.floor(1000 * Ab / r["As_slab"] / 25) * 25, MAX_SPACING)
    r["slab_provide"] = f"{int(db)} mm @ {r['slab_spacing']} mm, both directions"

    # flotation
    base_under = d["cover"] + a + tt + tb
    hw = max(0.0, base_under - d["GWT"])
    r["base_under"] = base_under
    r["hw"] = hw
    if hw <= 0:
        r["uplift"] = 0
        r["FS_float"] = None
        r["float_ok"] = True
    else:
        U = d["gw"] * hw * area
        soil_proj = (area - extL * extW) * base_under * d["gs"]
        R = W_empty + soil_proj
        r["uplift"] = U
        r["FS_float"] = R / U if U else 999
        r["float_ok"] = r["FS_float"] >= 1.2
    return r


# ===========================================================================
#  GUI
# ===========================================================================
DEFAULTS = {
    "project": "Septic Tank - 3 Chamber", "location": "Bamban, Tarlac",
    "L1": 1.8, "L2": 0.8, "L3": 0.8, "B": 1.2, "HL": 1.5, "fb": 0.3, "cover": 0.3,
    "tw": 0.20, "tb": 0.25, "tt": 0.15, "heel": 0.15,
    "fc": 28.0, "fy": 415.0, "gc": 24.0, "gw": 9.81, "gs": 19.9,
    "phi": 24.0, "qs": 12.0, "GWT": 5.0, "q_all": 95.0,
    "cover_i": 50.0, "cover_e": 75.0, "db": 12.0,
}
NUMERIC = [k for k in DEFAULTS if k not in ("project", "location")]

C_CONC = "#c9ccd1"; C_LIQ = "#8fc7e8"; C_SOIL = "#c8a97a"
C_EARTH = "#b5651d"; C_SURCH = "#7a5230"; C_LIQP = "#1f6f9a"; C_LINE = "#2b2b2b"
C_DIM = "#555"; C_HDR = "#1f3a5f"; C_OK = "#1e7d33"; C_BAD = "#c0392b"


class App:
    def __init__(self, root):
        self.root = root
        root.title("CRUZ Tank Designer  -  Rectangular Concrete Tank (PCA)")
        root.geometry("1240x820"); root.minsize(1080, 720)

        self.vars = {}
        for kk, vv in DEFAULTS.items():
            self.vars[kk] = tk.StringVar(value=str(vv))
        self.kopt = tk.StringVar(value="Ka")
        self.tri = tk.IntVar(value=3)
        self.uni = tk.IntVar(value=8)

        # header banner
        hdr = tk.Frame(root, bg=C_HDR)
        hdr.pack(fill="x")
        tk.Label(hdr, text="  CRUZ TANK DESIGNER", bg=C_HDR, fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side="left", pady=8)
        tk.Label(hdr, text="Rectangular Concrete Tank  |  PCA IS003.06D  |  ACI 350   ",
                 bg=C_HDR, fg="#bcd", font=("Segoe UI", 10)).pack(side="right", pady=12)

        nb = ttk.Notebook(root)
        nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.tab_in = ttk.Frame(nb); nb.add(self.tab_in, text="  1. Inputs & Case  ")
        self.tab_vis = ttk.Frame(nb); nb.add(self.tab_vis, text="  2. Section & Loads  ")
        self.tab_wall = ttk.Frame(nb); nb.add(self.tab_wall, text="  3. Wall Design  ")
        self.tab_sum = ttk.Frame(nb); nb.add(self.tab_sum, text="  4. Slabs / Stability / Summary  ")

        self._build_inputs()
        self._build_visual()
        self._build_wall()
        self._build_summary()

        for v in self.vars.values():
            v.trace_add("write", lambda *a: self.recompute())
        self.recompute()

    # ---------- tab 1 ----------
    def _build_inputs(self):
        f = self.tab_in
        cols = tk.Frame(f); cols.pack(fill="both", expand=True, padx=10, pady=8)

        def group(parent, title):
            lf = ttk.LabelFrame(parent, text=title); lf.pack(fill="x", pady=4); return lf

        def row(parent, label, key, unit=""):
            r = tk.Frame(parent); r.pack(fill="x", pady=1)
            tk.Label(r, text=label, width=24, anchor="w").pack(side="left")
            tk.Entry(r, textvariable=self.vars[key], width=10).pack(side="left")
            if unit:
                tk.Label(r, text=unit, fg="#777").pack(side="left")

        left = tk.Frame(cols); left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = tk.Frame(cols); right.pack(side="left", fill="both", expand=True)

        g = group(left, "Project")
        row(g, "Project", "project"); row(g, "Location", "location")
        g = group(left, "Geometry")
        for lab, key, u in [("Chamber 1 length L1", "L1", "m"), ("Chamber 2 length L2", "L2", "m"),
                            ("Chamber 3 length L3", "L3", "m"), ("Chamber width B", "B", "m"),
                            ("Liquid depth H_L", "HL", "m"), ("Freeboard", "fb", "m"),
                            ("Soil cover over lid", "cover", "m")]:
            row(g, lab, key, u)
        g = group(left, "Members")
        for lab, key, u in [("Wall thickness t_w", "tw", "m"), ("Base thickness t_b", "tb", "m"),
                            ("Top thickness t_t", "tt", "m"), ("Base projection (heel)", "heel", "m"),
                            ("Bar diameter", "db", "mm"),
                            ("Cover - interior", "cover_i", "mm"), ("Cover - exterior", "cover_e", "mm")]:
            row(g, lab, key, u)

        g = group(right, "Materials")
        for lab, key, u in [("f'c", "fc", "MPa"), ("fy", "fy", "MPa"),
                            ("gamma_concrete", "gc", "kN/m3"), ("gamma_water", "gw", "kN/m3")]:
            row(g, lab, key, u)
        g = group(right, "Soil")
        for lab, key, u in [("phi", "phi", "deg"), ("gamma_soil", "gs", "kN/m3"),
                            ("Surcharge q_s", "qs", "kPa"), ("GWT depth", "GWT", "m"),
                            ("Allow. bearing q_all", "q_all", "kPa")]:
            row(g, lab, key, u)
        kf = tk.Frame(g); kf.pack(fill="x", pady=2)
        tk.Label(kf, text="Lateral coef.", width=24, anchor="w").pack(side="left")
        ttk.Radiobutton(kf, text="Ka", variable=self.kopt, value="Ka",
                        command=self.recompute).pack(side="left")
        ttk.Radiobutton(kf, text="K0", variable=self.kopt, value="K0",
                        command=self.recompute).pack(side="left")

        g = group(right, "PCA plate case selection")
        tf = tk.Frame(g); tf.pack(fill="x", pady=2)
        tk.Label(tf, text="Triangular case (1-5)", width=24, anchor="w").pack(side="left")
        tri = ttk.Combobox(tf, textvariable=self.tri, width=6, state="readonly",
                           values=[1, 2, 3, 4, 5]); tri.pack(side="left")
        tri.bind("<<ComboboxSelected>>", lambda e: self.recompute())
        self.tri_lbl = tk.Label(tf, text="", fg="#555"); self.tri_lbl.pack(side="left", padx=6)
        uf = tk.Frame(g); uf.pack(fill="x", pady=2)
        tk.Label(uf, text="Uniform case (6-10)", width=24, anchor="w").pack(side="left")
        uni = ttk.Combobox(uf, textvariable=self.uni, width=6, state="readonly",
                           values=[6, 7, 8, 9, 10]); uni.pack(side="left")
        uni.bind("<<ComboboxSelected>>", lambda e: self.recompute())
        self.uni_lbl = tk.Label(uf, text="", fg="#555"); self.uni_lbl.pack(side="left", padx=6)
        self.compat = tk.Label(g, text="", font=("Segoe UI", 9, "bold")); self.compat.pack(anchor="w", pady=3)

        tk.Button(right, text="Reset to defaults", command=self.reset).pack(pady=8)

    # ---------- tab 2 ----------
    def _build_visual(self):
        f = self.tab_vis
        top = tk.Frame(f); top.pack(fill="both", expand=True, padx=6, pady=6)
        lf = ttk.LabelFrame(top, text="Longitudinal section")
        lf.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.sec = tk.Canvas(lf, bg="white", highlightthickness=0); self.sec.pack(fill="both", expand=True)
        rf = ttk.LabelFrame(top, text="Wall pressure diagram (transverse)")
        rf.pack(side="left", fill="both", expand=True, padx=(4, 0))
        self.load = tk.Canvas(rf, bg="white", highlightthickness=0); self.load.pack(fill="both", expand=True)
        bf = ttk.LabelFrame(f, text="Loads")
        bf.pack(fill="x", padx=6, pady=(0, 6))
        self.loadtxt = tk.Text(bf, height=7, font=("Consolas", 9), wrap="word"); self.loadtxt.pack(fill="x")
        self.sec.bind("<Configure>", lambda e: self.recompute())
        self.load.bind("<Configure>", lambda e: self.recompute())

    # ---------- tab 3 ----------
    def _build_wall(self):
        f = self.tab_wall
        self.walltxt = tk.Text(f, font=("Consolas", 10), wrap="word")
        self.walltxt.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------- tab 4 ----------
    def _build_summary(self):
        f = self.tab_sum
        self.sumframe = tk.Frame(f); self.sumframe.pack(fill="x", padx=10, pady=8)
        self.sumtxt = tk.Text(f, font=("Consolas", 10), wrap="word")
        self.sumtxt.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ---------- helpers ----------
    def reset(self):
        for kk, vv in DEFAULTS.items():
            self.vars[kk].set(str(vv))
        self.kopt.set("Ka"); self.tri.set(3); self.uni.set(8)

    def get_inputs(self):
        d = {"kopt": self.kopt.get()}
        for kk in NUMERIC:
            try:
                d[kk] = float(self.vars[kk].get())
            except (ValueError, tk.TclError):
                d[kk] = DEFAULTS[kk]
        d["project"] = self.vars["project"].get()
        d["location"] = self.vars["location"].get()
        return d

    def recompute(self):
        d = self.get_inputs()
        try:
            tri, uni = int(self.tri.get()), int(self.uni.get())
        except Exception:
            tri, uni = 3, 8
        r = design(d, tri, uni)
        self.tri_lbl.config(text=" / ".join(CASE_EDGES[tri][1:]))
        self.uni_lbl.config(text=" / ".join(CASE_EDGES[uni][1:]))
        if CASE_EDGES[tri][1:] == CASE_EDGES[uni][1:]:
            self.compat.config(text="OK - edge conditions match (superposable)", fg=C_OK)
        else:
            self.compat.config(text="WARNING - triangular & uniform edges differ; do not superpose",
                               fg=C_BAD)
        self.draw_section(d, r)
        self.draw_loads(d, r)
        self.write_loadtxt(d, r)
        self.write_wall(d, r, tri, uni)
        self.write_summary(d, r)

    # ---------- drawing ----------
    def draw_section(self, d, r):
        cv = self.sec; cv.delete("all")
        W = cv.winfo_width(); H = cv.winfo_height()
        if W < 60 or H < 60:
            return
        m = 46; tw, tb, tt = d["tw"], d["tb"], d["tt"]; a = r.get("a", 1.8)
        Lext = d["L1"] + d["L2"] + d["L3"] + 4 * tw
        Htot = tb + a + tt + d["cover"]
        if Lext <= 0 or Htot <= 0:
            return
        s = min((W - 2 * m) / Lext, (H - 2 * m) / Htot)
        ox = (W - Lext * s) / 2; oy = (H - Htot * s) / 2
        X = lambda x: ox + x * s
        Y = lambda y: oy + (Htot - y) * s
        cv.create_rectangle(X(0), Y(tb + a + tt + d["cover"]), X(Lext), Y(tb + a + tt),
                            fill=C_SOIL, outline="")
        yeg = Y(tb + a + tt + d["cover"])
        cv.create_line(X(-0.1 * Lext), yeg, X(1.1 * Lext), yeg, fill=C_EARTH, width=2)
        cv.create_text(X(1.1 * Lext), yeg - 8, text="EGL", fill=C_EARTH, anchor="e", font=("Segoe UI", 8))
        cv.create_rectangle(X(-d["heel"]), Y(tb), X(Lext + d["heel"]), Y(0), fill=C_CONC, outline=C_LINE)
        cv.create_rectangle(X(0), Y(tb + a + tt), X(Lext), Y(tb + a), fill=C_CONC, outline=C_LINE)
        xs = [0, tw + d["L1"], 2 * tw + d["L1"] + d["L2"], 3 * tw + d["L1"] + d["L2"] + d["L3"]]
        for xw in xs:
            cv.create_rectangle(X(xw), Y(tb + a), X(xw + tw), Y(tb), fill=C_CONC, outline=C_LINE)
        chambers = [(tw, d["L1"]), (2 * tw + d["L1"], d["L2"]), (3 * tw + d["L1"] + d["L2"], d["L3"])]
        for i, (x0, L) in enumerate(chambers, 1):
            if L > 0:
                cv.create_rectangle(X(x0), Y(tb + d["HL"]), X(x0 + L), Y(tb), fill=C_LIQ, outline="")
                cv.create_line(X(x0), Y(tb + d["HL"]), X(x0 + L), Y(tb + d["HL"]),
                               fill=C_LIQP, width=1, dash=(3, 2))
                cv.create_text(X(x0 + L / 2), Y(tb + d["HL"] / 2), text="C%d" % i,
                               fill="#0d4d6b", font=("Segoe UI", 9, "bold"))
        xd = X(-d["heel"]) - 14
        cv.create_line(xd, Y(tb), xd, Y(tb + a), fill=C_DIM)
        cv.create_text(xd - 4, (Y(tb) + Y(tb + a)) / 2, text="a=%.2fm" % a, angle=90,
                       fill=C_DIM, font=("Segoe UI", 8))
        cv.create_text((X(0) + X(Lext)) / 2, Y(0) + 14, text="External length = %.2f m" % Lext,
                       fill=C_DIM, font=("Segoe UI", 8))

    def draw_loads(self, d, r):
        cv = self.load; cv.delete("all")
        W = cv.winfo_width(); H = cv.winfo_height()
        if W < 60 or H < 60:
            return
        m = 60; a = r.get("a", 1.8)
        if a <= 0:
            return
        wx = W / 2; ty = m; by = H - m; pph = by - ty
        cv.create_line(wx, ty, wx, by, fill=C_LINE, width=6)
        cv.create_text(wx, ty - 14, text="WALL (height a)", fill=C_LINE, font=("Segoe UI", 9, "bold"))
        qe = r.get("q_earth", 0); qs = r.get("q_surch", 0); ql = r.get("q_liquid", 0)
        qmax = max(qe + qs, ql, 1e-6)
        pxk = (W / 2 - m - 30) / qmax
        pqe = qe * pxk; pqs = qs * pxk
        cv.create_polygon(wx, ty, wx - pqs, ty, wx - pqs, by, wx, by,
                          fill=C_SURCH, outline="", stipple="gray50")
        cv.create_polygon(wx - pqs, ty, wx - pqs, by, wx - pqs - pqe, by, fill=C_EARTH, outline=C_LINE)
        for ff in (0.25, 0.55, 0.85):
            yy = ty + ff * pph
            cv.create_line(wx - pqs - qe * ff * pxk, yy, wx, yy, fill=C_EARTH, arrow="last")
        cv.create_text(wx - pqs - pqe - 4, by + 14, text="earth %.1f kPa" % qe,
                       fill=C_EARTH, anchor="e", font=("Segoe UI", 8))
        cv.create_text(wx - pqs - 4, ty + 12, text="+surch %.1f" % qs,
                       fill=C_SURCH, anchor="e", font=("Segoe UI", 8))
        cv.create_text(wx - 8, ty - 2, text="EARTH + SURCHARGE (in)", anchor="e",
                       fill=C_EARTH, font=("Segoe UI", 8, "italic"))
        sy = ty + (d["fb"] / a) * pph
        pql = ql * pxk
        cv.create_polygon(wx, sy, wx, by, wx + pql, by, fill=C_LIQP, outline=C_LINE)
        for ff in (0.4, 0.7, 0.95):
            yy = sy + ff * (by - sy)
            frac = (yy - sy) / max(by - sy, 1)
            cv.create_line(wx, yy, wx + ql * frac * pxk, yy, fill=C_LIQP, arrow="last")
        cv.create_line(wx - 10, sy, wx + pql + 10, sy, fill=C_LIQP, dash=(3, 2))
        cv.create_text(wx + 12, sy - 8, text="liquid surface", anchor="w", fill=C_LIQP, font=("Segoe UI", 8))
        cv.create_text(wx + pql + 4, by + 14, text="liquid %.1f kPa" % ql,
                       fill=C_LIQP, anchor="w", font=("Segoe UI", 8))
        cv.create_text(wx + 8, ty - 2, text="LIQUID (out)", anchor="w", fill=C_LIQP, font=("Segoe UI", 8, "italic"))

    # ---------- text panels ----------
    def write_loadtxt(self, d, r):
        t = self.loadtxt; t.delete("1.0", "end")
        if "error" in r:
            t.insert("1.0", r["error"]); return
        ba = "   ".join("%s: %s" % (n, v) for n, v in r["ba"].items())
        t.insert("1.0",
            "Wall height a = H_L + fb = %.2f m\n"
            "Ka=%.3f  K0=%.3f  ->  using %s = %.3f\n"
            "q_earth = k*gs*a = %.2f kPa (triangular)     q_surch = k*q_s = %.2f kPa (uniform)\n"
            "q_liquid = gw*H_L = %.2f kPa (triangular)\n"
            "Panel b/a: %s\nGoverning b/a = %s"
            % (r["a"], r["Ka"], r["K0"], self.kopt.get(),
               r["k"], r["q_earth"], r["q_surch"], r["q_liquid"], ba, r["gov"]))

    def write_wall(self, d, r, tri, uni):
        t = self.walltxt; t.delete("1.0", "end")
        if "error" in r:
            t.insert("1.0", r["error"]); return
        shear = "OK - concrete alone, no stirrups" if r["shear_ok"] else "EXCEEDS phiVc - stirrups needed"
        t.insert("1.0",
            "WALL DESIGN  (Case %d triangular + Case %d uniform,  b/a = %s)\n"
            "%s\n\n"
            "MOMENTS (Moment = coef x q x a^2 / 1000)\n"
            "  Condition 2  earth+surcharge (governing point)  = %.3f kN-m/m\n"
            "  Condition 1  liquid, no backfill                = %.3f kN-m/m\n"
            "  Governing service moment M                      = %.3f kN-m/m\n"
            "  Mu = FF x M            (FF = 1.7)               = %.3f kN-m/m\n"
            "  M_req = Sd x Mu        (Sd = 1.3)               = %.3f kN-m/m\n\n"
            "FLEXURAL STEEL\n"
            "  Effective depth d                = %.1f mm\n"
            "  As (flexure)                     = %.0f mm2/m\n"
            "  As,min (shrinkage & temperature) = %.0f mm2/m\n"
            "  As DESIGN  (governed by %s)      = %.0f mm2/m\n\n"
            "BAR SPACING (%d mm bars, Ab = %.0f mm2)\n"
            "  Crack-control limit bw           = %.0f mm\n"
            "  SPACING TO PROVIDE (gov: %s)     = %d mm\n\n"
            "SHEAR (no Sd on concrete shear per PCA p.1-6)\n"
            "  Vu = FF x V                      = %.2f kN/m\n"
            "  phiVc = phi x 0.17 sqrt(f'c) b d = %.2f kN/m\n"
            "  CHECK: %s\n\n"
            "REINFORCEMENT LAYOUT (auto recommendation)\n"
            "  Recommended: %s  (%s)\n"
            "  Moment-reversal ratio = %.2f\n\n"
            "  >>> PROVIDE:  %s\n"
            % (tri, uni, r["gov"],
               ("edge conditions match" if CASE_EDGES[tri][1:] == CASE_EDGES[uni][1:]
                else "WARNING: edge conditions differ - superposition not valid"),
               r["M_cond2"], r["M_cond1"], r["M"], r["Mu"], r["M_req"],
               r["d_eff"], r["As_flex"], r["As_min"], r["gov_by"], r["As_design"],
               int(d["db"]), r["Ab"], r["bw"], r["sp_gov"], r["spacing"],
               r["Vu"], r["phiVc"], shear,
               r["layout"], r["layout_why"], r["reversal"], r["provide"]))

    def write_summary(self, d, r):
        for w in self.sumframe.winfo_children():
            w.destroy()
        if "error" in r:
            self.sumtxt.delete("1.0", "end"); self.sumtxt.insert("1.0", r["error"]); return

        def chip(text, ok):
            tk.Label(self.sumframe, text=text, bg=(C_OK if ok else C_BAD), fg="white",
                     font=("Segoe UI", 10, "bold"), padx=10, pady=6).pack(side="left", padx=4)
        chip("BEARING  " + ("OK" if r["bearing_ok"] else "FAIL"), r["bearing_ok"])
        chip("SHEAR  " + ("OK" if r["shear_ok"] else "CHECK"), r["shear_ok"])
        chip("FLOTATION  " + ("OK" if r["float_ok"] else "FAIL"), r["float_ok"])

        fs = "n/a (above GWT)" if r["FS_float"] is None else "%.2f (min 1.2)" % r["FS_float"]
        t = self.sumtxt; t.delete("1.0", "end")
        t.insert("1.0",
            "PROJECT: %s   -   %s\n"
            "==================================================================\n\n"
            "WALL\n"
            "  Governing moment M_req            = %.2f kN-m/m\n"
            "  As design                         = %.0f mm2/m\n"
            "  PROVIDE                           = %s\n"
            "  Layout                            = %s\n"
            "  Shear                             = %s\n\n"
            "BASE SLAB\n"
            "  External footprint                = %.2f x %.2f m  (area %.2f m2)\n"
            "  Bearing pressure                  = %.1f kPa   (allow %.0f)  -> %s\n"
            "  Net panel pressure (governing)    = %.1f kPa\n"
            "  Slab M_req (short span, fixed)    = %.2f kN-m/m\n"
            "  As slab design                    = %.0f mm2/m\n"
            "  PROVIDE                           = %s\n\n"
            "STABILITY\n"
            "  Base underside below EGL          = %.2f m\n"
            "  Water head on base hw             = %.2f m\n"
            "  Flotation FS                      = %s  -> %s\n\n"
            "Coefficients: PCA IS003.06D Ch.2 (embedded).  Load factors/Sd per ACI 350.\n"
            "Base-slab & flotation are quick checks (one-way short span, empty-tank uplift)."
            % (d["project"], d["location"],
               r["M_req"], r["As_design"], r["provide"], r["layout"],
               ("OK" if r["shear_ok"] else "CHECK stirrups"),
               r["ext_len"], r["ext_wid"], r["base_area"],
               r["bearing"], r["q_all"], ("OK" if r["bearing_ok"] else "FAIL"),
               r["net_press"], r["M_slab_req"], r["As_slab"], r["slab_provide"],
               r["base_under"], r["hw"], fs, ("OK" if r["float_ok"] else "FAIL")))


def main():
    if not HAVE_TK:
        print("tkinter is not available in this Python. On Windows use the standard "
              "python.org installer (tkinter is included).")
        return
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()