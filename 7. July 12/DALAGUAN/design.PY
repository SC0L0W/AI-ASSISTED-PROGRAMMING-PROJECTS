"""
design.py
=========
Engineering calculation engine for isolated reinforced concrete pad footings.

Code basis:
    - NBCC 2020            : Load combinations (simplified representative set)
    - CSA A23.3-19          : Reinforced concrete design (flexure, one-way shear,
                              two-way/punching shear, minimum reinforcement)

IMPORTANT ENGINEERING NOTE
---------------------------
The load combinations implemented here are the simplified set requested for this
tool (1.25D+1.5L, 1.25D+1.5L+0.5W, 1.25D+1.5L+0.5E, 0.9D+/-1.5W, 0.9D+/-1.5E).
For final permit-ready designs, cross-check against the full NBCC 2020 Table
4.1.3.2 combinations (including companion loads S, and the 1.4D case) as
required by the governing jurisdiction.

The one-way shear resistance uses the CSA A23.3 Cl.11.3.4 *simplified* method
(Vc = 0.2 * lambda * phi_c * sqrt(f'c) * bw * dv). Where a more refined General
Method (Cl. 11.3.6, sectional beta/theta) is required by the reviewing engineer
of record, this should be substituted.

Units convention used throughout:
    Force       : kN
    Length      : mm  (except footing plan dimensions L, B which are tracked in
                       mm internally but displayed in mm; areas in mm^2 or m^2
                       as noted)
    Stress      : MPa (N/mm^2)
    Moments     : kN.m
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------

@dataclass
class Loads:
    D: float = 0.0      # Dead load, kN
    L: float = 0.0      # Live load, kN
    W: float = 0.0      # Wind load, kN
    E: float = 0.0      # Seismic load, kN
    Mx: float = 0.0     # Moment about x-axis, kN.m
    My: float = 0.0     # Moment about y-axis, kN.m


@dataclass
class SoilProps:
    q_allow: float = 150.0   # Allowable bearing capacity, kPa


@dataclass
class Materials:
    fc: float = 25.0     # f'c, MPa
    fy: float = 400.0    # fy, MPa
    phi_c: float = 0.65  # CSA A23.3 concrete resistance factor
    phi_s: float = 0.85  # CSA A23.3 reinforcing steel resistance factor
    lam: float = 1.0     # lambda, normal density concrete


@dataclass
class Geometry:
    col_width: float = 400.0   # column width (c1), mm
    col_depth: float = 400.0   # column depth (c2), mm
    thickness: float = 500.0  # footing thickness, mm
    L: float = 2000.0          # footing plan dimension (long side), mm
    B: float = 2000.0          # footing plan dimension (short side), mm
    cover: float = 75.0        # clear cover to reinforcement, mm (soil-cast)


@dataclass
class LoadCombinationResult:
    name: str
    P: float            # kN
    Mx: float            # kN.m
    My: float            # kN.m
    is_service: bool = False  # True if this combo is used for size/pressure only


@dataclass
class DesignResult:
    governing_combo: str = ""
    geometry: Geometry = None
    q_max: float = 0.0
    q_min: float = 0.0
    e_x: float = 0.0
    e_y: float = 0.0
    within_kern: bool = True
    As_req_L: float = 0.0     # mm^2 per m width, long direction
    As_req_B: float = 0.0     # mm^2 per m width, short direction
    bar_L: str = ""
    bar_B: str = ""
    one_way_status: Dict[str, bool] = field(default_factory=dict)
    punching_status: bool = True
    utilization: Dict[str, float] = field(default_factory=dict)
    log: List[str] = field(default_factory=list)
    ok: bool = False


# ---------------------------------------------------------------------------
# 1. Load combinations  (NBCC 2020 - simplified representative set)
# ---------------------------------------------------------------------------

def load_combinations(loads: Loads) -> List[LoadCombinationResult]:
    """
    Build the set of factored (ULS) and service (SLS) load combinations.

    Factored combinations (for strength design - flexure/shear/punching):
        1) 1.25D + 1.5L
        2) 1.25D + 1.5L + 0.5W
        3) 1.25D + 1.5L + 0.5E
        4) 0.9D + 1.5W
        5) 0.9D - 1.5W
        6) 0.9D + 1.5E
        7) 0.9D - 1.5E

    Service combination (for soil bearing / sizing):
        S1) 1.0D + 1.0L   (used for footing area sizing)
        S2) 1.0D + 1.0L + 1.0W  (checked for eccentricity / overturning trend)
        S3) 1.0D + 1.0L + 1.0E
    """
    combos = []

    combos.append(LoadCombinationResult("1.25D+1.5L",
                                         1.25 * loads.D + 1.5 * loads.L,
                                         1.25 * loads.Mx + 1.5 * 0,  # live load moment excluded unless supplied
                                         1.25 * loads.My))
    combos.append(LoadCombinationResult("1.25D+1.5L+0.5W",
                                         1.25 * loads.D + 1.5 * loads.L + 0.5 * loads.W,
                                         1.25 * loads.Mx,
                                         1.25 * loads.My))
    combos.append(LoadCombinationResult("1.25D+1.5L+0.5E",
                                         1.25 * loads.D + 1.5 * loads.L + 0.5 * loads.E,
                                         1.25 * loads.Mx,
                                         1.25 * loads.My))
    combos.append(LoadCombinationResult("0.9D+1.5W",
                                         0.9 * loads.D + 1.5 * loads.W,
                                         0.9 * loads.Mx,
                                         0.9 * loads.My))
    combos.append(LoadCombinationResult("0.9D-1.5W",
                                         0.9 * loads.D - 1.5 * loads.W,
                                         0.9 * loads.Mx,
                                         0.9 * loads.My))
    combos.append(LoadCombinationResult("0.9D+1.5E",
                                         0.9 * loads.D + 1.5 * loads.E,
                                         0.9 * loads.Mx,
                                         0.9 * loads.My))
    combos.append(LoadCombinationResult("0.9D-1.5E",
                                         0.9 * loads.D - 1.5 * loads.E,
                                         0.9 * loads.Mx,
                                         0.9 * loads.My))

    # Service (unfactored) combinations, used for sizing / bearing pressure
    combos.append(LoadCombinationResult("Service D+L",
                                         loads.D + loads.L,
                                         loads.Mx, loads.My, is_service=True))
    combos.append(LoadCombinationResult("Service D+L+W",
                                         loads.D + loads.L + loads.W,
                                         loads.Mx, loads.My, is_service=True))
    combos.append(LoadCombinationResult("Service D+L+E",
                                         loads.D + loads.L + loads.E,
                                         loads.Mx, loads.My, is_service=True))

    return combos


def governing_ultimate_combo(combos: List[LoadCombinationResult]) -> LoadCombinationResult:
    """Return the factored combination producing the largest axial load P."""
    factored = [c for c in combos if not c.is_service]
    return max(factored, key=lambda c: abs(c.P))


def governing_service_combo(combos: List[LoadCombinationResult]) -> LoadCombinationResult:
    """Return the service combination producing the largest axial load P (for sizing)."""
    service = [c for c in combos if c.is_service]
    return max(service, key=lambda c: abs(c.P))


# ---------------------------------------------------------------------------
# 2. Soil pressure / sizing
# ---------------------------------------------------------------------------

def soil_pressure(P_kN: float, Mx_kNm: float, My_kNm: float,
                   L_mm: float, B_mm: float) -> Tuple[float, float, float, float, bool]:
    """
    Compute maximum/minimum soil bearing pressure under a rectangular footing
    subjected to concentric load P plus biaxial moments Mx, My.

    L is the plan dimension in the direction resisting My (i.e. length),
    B is the plan dimension resisting Mx (i.e. width).

    e_L = M / P    (eccentricity in the L direction, uses My)
    e_B = M / P    (eccentricity in the B direction, uses Mx)

    Middle-third (kern) rule: e <= L/6 (and B/6) => no uplift, pressure
    varies linearly:
        q = P/A +/- M*c/I

    Returns: (q_max kPa, q_min kPa, e_L mm, e_B mm, within_kern)
    """
    L = L_mm / 1000.0   # m
    B = B_mm / 1000.0   # m
    A = L * B           # m^2

    if abs(P_kN) < 1e-6:
        return 0.0, 0.0, 0.0, 0.0, True

    e_L = (My_kNm / P_kN) * 1000.0  # mm
    e_B = (Mx_kNm / P_kN) * 1000.0  # mm

    within_kern = (abs(e_L) <= L_mm / 6.0) and (abs(e_B) <= B_mm / 6.0)

    # Section moduli about each axis (m^3), using consistent m units, then P in kN
    # q = P/A +/- 6*M / (dimension * other_dimension^2)
    q0 = P_kN / A  # kPa (kN/m^2)

    q_from_My = 6.0 * My_kNm / (B * L ** 2) if L > 0 else 0.0
    q_from_Mx = 6.0 * Mx_kNm / (L * B ** 2) if B > 0 else 0.0

    q_max = q0 + abs(q_from_My) + abs(q_from_Mx)
    q_min = q0 - abs(q_from_My) - abs(q_from_Mx)

    return q_max, q_min, e_L, e_B, within_kern


def required_area(P_kN: float, q_allow_kPa: float) -> float:
    """Required plan area (m^2) for concentric service load."""
    if q_allow_kPa <= 0:
        return 0.0
    return P_kN / q_allow_kPa


# ---------------------------------------------------------------------------
# 3. Flexural design (CSA A23.3-19)
# ---------------------------------------------------------------------------

def alpha1_beta1(fc: float) -> Tuple[float, float]:
    """CSA A23.3-19 Cl. 10.1.7 stress block parameters."""
    a1 = max(0.85 - 0.0015 * fc, 0.67)
    b1 = max(0.97 - 0.0025 * fc, 0.67)
    return a1, b1


def flexural_design(Mu_kNm: float, b_mm: float, d_mm: float,
                     fc: float, fy: float, phi_c: float, phi_s: float) -> Dict:
    """
    Design flexural reinforcement for a rectangular strip of width b (mm) and
    effective depth d (mm) subjected to factored moment Mu (kN.m), per CSA
    A23.3-19 Cl. 10.

    Mr = phi_s * As * fy * (d - a/2)
    a  = (phi_s * As * fy) / (alpha1 * phi_c * f'c * b)

    Solved via the standard quadratic (Rn method):
        Rn = Mu / (phi_s * b * d^2)   [Mu converted to N.mm]
        rho = (alpha1 * phi_c * f'c / (phi_s * fy)) *
              (1 - sqrt(1 - 2*Rn / (alpha1 * phi_c * f'c)))
        As = rho * b * d
    """
    a1, b1 = alpha1_beta1(fc)
    Mu_Nmm = Mu_kNm * 1e6  # kN.m -> N.mm

    if Mu_Nmm <= 0 or b_mm <= 0 or d_mm <= 0:
        return {"As_req": 0.0, "a1": a1, "b1": b1, "Rn": 0.0, "note": "No moment demand"}

    Rn = Mu_Nmm / (phi_s * b_mm * d_mm ** 2)
    term = 1 - (2 * Rn) / (a1 * phi_c * fc)

    if term < 0:
        # Section is too shallow for singly-reinforced design at this b,d
        return {"As_req": None, "a1": a1, "b1": b1, "Rn": Rn,
                "note": "Section inadequate - increase thickness (d)"}

    rho = (a1 * phi_c * fc / (phi_s * fy)) * (1 - math.sqrt(term))
    As_req = rho * b_mm * d_mm  # mm^2 over width b

    return {"As_req": As_req, "rho": rho, "a1": a1, "b1": b1, "Rn": Rn, "note": "OK"}


def minimum_steel(b_mm: float, h_mm: float) -> float:
    """
    CSA A23.3-19 Cl. 7.8.1 shrinkage & temperature reinforcement, applied as
    the minimum flexural steel for footings (slab-like member):
        As_min = 0.002 * b * h
    """
    return 0.002 * b_mm * h_mm


# Standard Canadian metric reinforcing bar areas (mm^2)
BAR_AREAS = {
    "10M": 100, "15M": 200, "20M": 300, "25M": 500,
    "30M": 700, "35M": 1000, "45M": 1500, "55M": 2500,
}


def select_bar_spacing(As_req_mm2_per_m: float, max_spacing_mm: float = 450) -> Tuple[str, float]:
    """
    Select the smallest practical bar size / spacing combination (per metre
    width) that satisfies As_req. Returns (bar designation, spacing mm).
    """
    best = None
    for bar, area in sorted(BAR_AREAS.items(), key=lambda x: x[1]):
        if As_req_mm2_per_m <= 0:
            spacing = max_spacing_mm
        else:
            spacing = (area * 1000.0) / As_req_mm2_per_m  # mm, per 1000mm width
        spacing = min(spacing, max_spacing_mm)
        # round down to nearest practical 25mm increment
        spacing = math.floor(spacing / 25.0) * 25.0
        if spacing < 75:
            continue  # too congested, try next larger bar
        provided_As = (area * 1000.0) / spacing
        if provided_As >= As_req_mm2_per_m:
            best = (bar, spacing, provided_As)
            break
    if best is None:
        # fall back to largest bar at minimum spacing
        bar = "35M"
        spacing = 100
        provided_As = (BAR_AREAS[bar] * 1000.0) / spacing
        best = (bar, spacing, provided_As)
    return best[0], best[1]


# ---------------------------------------------------------------------------
# 4. One-way shear (CSA A23.3-19 Cl. 11.3 - simplified method)
# ---------------------------------------------------------------------------

def one_way_shear(qu_kPa: float, b_mm: float, cantilever_mm: float,
                   d_mm: float, fc: float, phi_c: float, lam: float = 1.0) -> Dict:
    """
    Check one-way (beam) shear at a critical section located distance d from
    the face of the column, per CSA A23.3-19 Cl. 11.3.2.

    Vf  = qu * b * (cantilever - d)      [factored shear at critical section]
    Vc  = 0.2 * lambda * phi_c * sqrt(f'c) * b * d   [simplified Cl. 11.3.4]
    """
    x_crit = max(cantilever_mm - d_mm, 0.0)
    # qu in kPa (kN/m^2); convert b, x to metres for force in kN then keep kN
    Vf = qu_kPa * (b_mm / 1000.0) * (x_crit / 1000.0)  # kN

    Vc = 0.2 * lam * phi_c * math.sqrt(fc) * b_mm * d_mm / 1000.0  # kN
    # (sqrt(fc) in MPa=N/mm^2, b*d in mm^2 -> N, /1000 -> kN)

    utilization = Vf / Vc if Vc > 0 else float('inf')
    status = Vf <= Vc

    return {"Vf": Vf, "Vc": Vc, "status": status, "utilization": utilization, "x_crit": x_crit}


# ---------------------------------------------------------------------------
# 5. Punching (two-way) shear (CSA A23.3-19 Cl. 13.3.4)
# ---------------------------------------------------------------------------

def punching_shear(qu_kPa: float, L_mm: float, B_mm: float,
                    c1_mm: float, c2_mm: float, d_mm: float,
                    fc: float, phi_c: float, lam: float = 1.0,
                    col_location: str = "interior") -> Dict:
    """
    Two-way (punching) shear check at critical perimeter b0, located d/2 from
    the column face, per CSA A23.3-19 Cl. 13.3.

    b0 = 2*(c1+d) + 2*(c2+d)   [interior column]

    vc = min(vc1, vc2, vc3):
        vc1 = 0.19 * (1 + 2/beta_c) * lambda * phi_c * sqrt(f'c)
        vc2 = 0.19 * (alpha_s*d/b0 + 1) * lambda * phi_c * sqrt(f'c)
        vc3 = 0.38 * lambda * phi_c * sqrt(f'c)

    beta_c = ratio of long side to short side of column (c_long/c_short)
    alpha_s = 4 (interior), 3 (edge), 2 (corner)
    """
    beta_c = max(c1_mm, c2_mm) / min(c1_mm, c2_mm) if min(c1_mm, c2_mm) > 0 else 1.0
    alpha_s = {"interior": 4, "edge": 3, "corner": 2}.get(col_location, 4)

    b0 = 2 * (c1_mm + d_mm) + 2 * (c2_mm + d_mm)

    vc1 = 0.19 * (1 + 2.0 / beta_c) * lam * phi_c * math.sqrt(fc)
    vc2 = 0.19 * (alpha_s * d_mm / b0 + 1) * lam * phi_c * math.sqrt(fc)
    vc3 = 0.38 * lam * phi_c * math.sqrt(fc)
    vc = min(vc1, vc2, vc3)  # MPa

    Vc = vc * b0 * d_mm / 1000.0  # kN

    # Factored shear force = total load minus bearing within critical perimeter
    A_footing = (L_mm / 1000.0) * (B_mm / 1000.0)  # m^2
    A_crit = ((c1_mm + d_mm) / 1000.0) * ((c2_mm + d_mm) / 1000.0)  # m^2
    Vf = qu_kPa * (A_footing - A_crit)  # kN

    utilization = Vf / Vc if Vc > 0 else float('inf')
    status = Vf <= Vc

    return {"Vf": Vf, "Vc": Vc, "b0": b0, "beta_c": beta_c, "vc": vc,
            "status": status, "utilization": utilization}


# ---------------------------------------------------------------------------
# 6. Auto iteration / auto-sizing
# ---------------------------------------------------------------------------

def auto_design(loads: Loads, soil: SoilProps, mat: Materials, geo: Geometry,
                 max_iter: int = 60) -> DesignResult:
    """
    Iteratively resize the footing (plan dimensions L, B and thickness t)
    until soil pressure, flexure, one-way shear, and punching shear are all
    satisfied.

    Strategy:
        1. Size plan area from governing service load (P/q_allow), apply a
           small allowance if eccentricity is present.
        2. Check the middle-third rule; if violated, enlarge the footing.
        3. Design flexural steel using the governing ULS combo.
        4. Check one-way and punching shear; if NG, increase thickness and
           re-check flexure/steel, then re-check shear. Repeat.
    """
    log = []
    combos = load_combinations(loads)
    svc = governing_service_combo(combos)
    ult = governing_ultimate_combo(combos)

    log.append(f"Governing service combo: {svc.name}  P={svc.P:.1f} kN, "
               f"Mx={svc.Mx:.1f} kN.m, My={svc.My:.1f} kN.m")
    log.append(f"Governing ULS combo: {ult.name}  P={ult.P:.1f} kN, "
               f"Mx={ult.Mx:.1f} kN.m, My={ult.My:.1f} kN.m")

    # --- Step 1: initial plan size from required area ---
    A_req = required_area(svc.P, soil.q_allow)
    side = max(math.sqrt(A_req), (geo.col_width + 400) / 1000.0)  # m, minimum practical
    L_mm = max(geo.L, side * 1000.0)
    B_mm = max(geo.B, side * 1000.0)
    t_mm = geo.thickness

    result = DesignResult()

    for it in range(max_iter):
        # Round plan dims up to nearest 50 mm for buildability
        L_mm = math.ceil(L_mm / 50.0) * 50.0
        B_mm = math.ceil(B_mm / 50.0) * 50.0
        t_mm = math.ceil(t_mm / 25.0) * 25.0

        q_max, q_min, e_L, e_B, within_kern = soil_pressure(svc.P, svc.Mx, svc.My, L_mm, B_mm)

        # If uplift (q_min < 0) or bearing exceeded, or e outside kern -> enlarge
        if q_min < 0 or not within_kern or q_max > soil.q_allow:
            L_mm *= 1.05
            B_mm *= 1.05
            log.append(f"Iter {it}: bearing/kern NG (qmax={q_max:.1f}, qmin={q_min:.1f}) "
                        f"-> enlarging plan to {L_mm:.0f}x{B_mm:.0f} mm")
            continue

        # Effective depth (mm) - single layer, bars each way, average
        bar_dia_assumed = 20  # mm, initial assumption (20M)
        d_mm = t_mm - geo.cover - bar_dia_assumed  # to centroid of outer layer, approx

        # --- Flexure: cantilever from face of column, both directions ---
        cant_L = (L_mm - geo.col_width) / 2.0   # cantilever governing bending about B-B axis
        cant_B = (B_mm - geo.col_depth) / 2.0

        qu_avg = ult.P / ((L_mm / 1000.0) * (B_mm / 1000.0))  # kPa, uniform approx (conservative,
                                                                # ignores ULS moment redistribution)

        # Moment per metre width, at column face, cantilever cant_L (governs steel in L direction)
        Mu_L = qu_avg * (B_mm / 1000.0) * (cant_L / 1000.0) ** 2 / 2.0  # kN.m over width B -> convert to per-m
        Mu_L_per_m = Mu_L / (B_mm / 1000.0)
        Mu_B = qu_avg * (L_mm / 1000.0) * (cant_B / 1000.0) ** 2 / 2.0
        Mu_B_per_m = Mu_B / (L_mm / 1000.0)

        fl_L = flexural_design(Mu_L_per_m, 1000.0, d_mm, mat.fc, mat.fy, mat.phi_c, mat.phi_s)
        fl_B = flexural_design(Mu_B_per_m, 1000.0, d_mm, mat.fc, mat.fy, mat.phi_c, mat.phi_s)

        if fl_L["As_req"] is None or fl_B["As_req"] is None:
            t_mm += 50
            log.append(f"Iter {it}: flexure section inadequate -> increasing thickness to {t_mm:.0f} mm")
            continue

        As_min = minimum_steel(1000.0, t_mm)
        As_L = max(fl_L["As_req"], As_min)
        As_B = max(fl_B["As_req"], As_min)

        # --- One-way shear check (governing = larger cantilever direction) ---
        ow_L = one_way_shear(qu_avg, B_mm, cant_L, d_mm, mat.fc, mat.phi_c, mat.lam)
        ow_B = one_way_shear(qu_avg, L_mm, cant_B, d_mm, mat.fc, mat.phi_c, mat.lam)

        # --- Punching shear check ---
        pu = punching_shear(qu_avg, L_mm, B_mm, geo.col_width, geo.col_depth, d_mm,
                             mat.fc, mat.phi_c, mat.lam, col_location="interior")

        shear_ok = ow_L["status"] and ow_B["status"] and pu["status"]

        if not shear_ok:
            t_mm += 50
            log.append(f"Iter {it}: shear NG (1-way L util={ow_L['utilization']:.2f}, "
                        f"1-way B util={ow_B['utilization']:.2f}, punching util={pu['utilization']:.2f}) "
                        f"-> increasing thickness to {t_mm:.0f} mm")
            continue

        # All checks pass
        bar_L, sp_L = select_bar_spacing(As_L)
        bar_B, sp_B = select_bar_spacing(As_B)

        result.governing_combo = ult.name
        result.geometry = Geometry(col_width=geo.col_width, col_depth=geo.col_depth,
                                    thickness=t_mm, L=L_mm, B=B_mm, cover=geo.cover)
        result.q_max, result.q_min = q_max, q_min
        result.e_x, result.e_y = e_B, e_L
        result.within_kern = within_kern
        result.As_req_L, result.As_req_B = As_L, As_B
        result.bar_L = f"{bar_L} @ {sp_L:.0f} mm o.c. (long dir.)"
        result.bar_B = f"{bar_B} @ {sp_B:.0f} mm o.c. (short dir.)"
        result.one_way_status = {"long_dir": ow_L["status"], "short_dir": ow_B["status"]}
        result.punching_status = pu["status"]
        result.utilization = {
            "bearing": q_max / soil.q_allow if soil.q_allow > 0 else 0,
            "one_way_long": ow_L["utilization"],
            "one_way_short": ow_B["utilization"],
            "punching": pu["utilization"],
        }
        result.log = log + [f"Converged after {it+1} iteration(s)."]
        result.ok = True
        return result

    # Did not converge
    result.log = log + ["Auto-design did NOT converge within iteration limit. "
                         "Review inputs (loads may be excessive for soil capacity)."]
    result.ok = False
    return result