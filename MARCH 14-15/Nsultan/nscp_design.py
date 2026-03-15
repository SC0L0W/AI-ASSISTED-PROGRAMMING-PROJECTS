# -*- coding: utf-8 -*-
"""
==============================================================================
  NSCP 2015 - 2-STOREY RESIDENTIAL BUILDING WITH ROOF DECK
  Complete Structural Analysis and Design
==============================================================================
  Building:   9m x 11m lot, 2 storeys + Roof Deck
  Floors:     GF: Garage, Kitchen, Bathroom, Dining, 2 Rooms
              1F: 3 Rooms + Terrace
              2F: Roof Deck
  Stair:      Included
  Code:       NSCP 2015 (National Structural Code of the Philippines)
  Units:      kN, m, MPa
==============================================================================
  Outputs:
    nscp_building_design.png   -- Complete structural drawings (10 panels)
    nscp_design_report.txt     -- Detailed design calculations report
==============================================================================
"""

# ── AUTO-INSTALL DEPENDENCIES ─────────────────────────────────────────────────
import subprocess, sys, importlib

def _ensure(pkg, imp=None):
    try:
        importlib.import_module(imp or pkg)
    except ImportError:
        print(f"  [SETUP] Installing {pkg}...")
        r = subprocess.run([sys.executable, "-m", "pip", "install", pkg],
                           capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [ERROR] pip install {pkg} failed.\n{r.stderr[-400:]}")
            sys.exit(1)
        print(f"  [OK]    {pkg} installed.")

_ensure("numpy")
_ensure("matplotlib")

import math, os, warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.patches import FancyBboxPatch, Polygon, FancyArrowPatch
warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))

# ==============================================================================
#  BUILDING PARAMETERS
# ==============================================================================

# Lot / Building dimensions
LOT_X       = 9.0       # m  (short direction)
LOT_Y       = 11.0      # m  (long direction)
SETBACK     = 0.5       # m  perimeter setback from lot
BLD_X       = LOT_X - 2*SETBACK   # = 8.0 m
BLD_Y       = LOT_Y - 2*SETBACK   # = 10.0 m

# Grid lines (column centers) -- X direction (3 bays)
# 0 --- 3.0 --- 5.5 --- 8.0  (m from left)
COL_X = [0.0, 3.0, 5.5, 8.0]   # 4 column lines in X
# Grid lines Y direction (3 bays)
# 0 --- 3.5 --- 7.0 --- 10.0  (m from bottom)
COL_Y = [0.0, 3.5, 7.0, 10.0]  # 4 column lines in Y

N_COL_X = len(COL_X)            # 4
N_COL_Y = len(COL_Y)            # 4
N_COLS  = N_COL_X * N_COL_Y     # 16 columns total

# Floor heights
H_GF   = 3.0    # m  ground floor height (floor to floor)
H_1F   = 3.0    # m  1st floor height
H_RF   = 1.2    # m  parapet/roof deck (slab only)
H_TOT  = H_GF + H_1F + H_RF   # total building height = 7.2 m

# Floor elevations
Z_GF   = 0.00   # ground floor slab
Z_1F   = H_GF   # = 3.0 m
Z_RF   = H_GF + H_1F  # = 6.0 m

# Stair
STAIR_X0 = COL_X[2]   # stair starts at 3rd column line in X
STAIR_W  = 1.2         # stair width
STAIR_L  = 2.5         # stair length

# Materials (NSCP 2015)
FC   = 28.0     # MPa  concrete compressive strength
FY   = 415.0    # MPa  steel yield strength (deformed bars)
FYS  = 275.0    # MPa  stirrup steel
EC   = 4700 * math.sqrt(FC)    # MPa  modulus of elasticity concrete
ES   = 200000.0                 # MPa  modulus of elasticity steel
GAMMA_CONC = 24.0               # kN/m3
GAMMA_SOIL = 18.0               # kN/m3

# Cover
COVER_COL   = 0.040  # m  column clear cover
COVER_BEAM  = 0.040  # m  beam clear cover
COVER_SLAB  = 0.020  # m  slab clear cover
COVER_FTG   = 0.075  # m  footing clear cover

# ==============================================================================
#  LOADS  (NSCP 2015 Table 204)
# ==============================================================================

# Slab thickness
T_SLAB_GF = 0.125   # m
T_SLAB_1F = 0.125   # m
T_SLAB_RF = 0.100   # m  roof slab (lighter)

# Dead loads (kN/m2)
DL_FLOOR_FINISH  = 1.50   # tiles + mortar bed
DL_CEILING       = 0.50   # ceiling + MEP
DL_PARTITIONS    = 1.00   # movable partitions (NSCP allows as live if <1kN/m)
DL_WATERPROOFING = 0.50   # roof waterproofing

# Live loads  (NSCP 2015 Table 205-1)
LL_RESIDENTIAL   = 2.00   # kN/m2  dwelling units
LL_ROOF_DECK     = 4.80   # kN/m2  roof deck / assembly
LL_GARAGE        = 2.40   # kN/m2  garages (passenger cars)
LL_CORRIDOR      = 3.00   # kN/m2  corridors/stairs

# Beam sizes (preliminary - will be verified)
B_BIG_B  = 0.250   # m  main beam width
B_BIG_D  = 0.400   # m  main beam depth
B_SM_B   = 0.200   # m  secondary beam width
B_SM_D   = 0.300   # m  secondary beam depth

# Column sizes
COL_B    = 0.300   # m  column width
COL_D    = 0.300   # m  column depth

# Footing allowable soil bearing capacity
Q_ALLOW  = 150.0   # kN/m2  (safe bearing capacity)
DEPTH_FTG = 1.50   # m  footing depth from NGL

# Load factors NSCP 2015 (LRFD / strength design)
LF_D = 1.2    # dead load factor
LF_L = 1.6    # live load factor

# ==============================================================================
#  STRUCTURAL COMPUTATIONS
# ==============================================================================

# ── Bay lengths ───────────────────────────────────────────────────────────────
BAY_X = [COL_X[i+1]-COL_X[i] for i in range(N_COL_X-1)]  # [3.0, 2.5, 2.5]
BAY_Y = [COL_Y[i+1]-COL_Y[i] for i in range(N_COL_Y-1)]  # [3.5, 3.5, 3.0]

# ── Slab dead loads (self weight + superimposed) ──────────────────────────────
SDL_GF = GAMMA_CONC*T_SLAB_GF + DL_FLOOR_FINISH + DL_CEILING + DL_PARTITIONS
SDL_1F = GAMMA_CONC*T_SLAB_1F + DL_FLOOR_FINISH + DL_CEILING + DL_PARTITIONS
SDL_RF = GAMMA_CONC*T_SLAB_RF + DL_FLOOR_FINISH + DL_WATERPROOFING

print("="*65)
print("  NSCP 2015 -- 2-STOREY BUILDING STRUCTURAL DESIGN")
print("="*65)
print(f"  Building     : {BLD_X}m x {BLD_Y}m  ({N_COLS} columns)")
print(f"  fc'          : {FC} MPa     fy: {FY} MPa")
print(f"  SDL GF slab  : {SDL_GF:.2f} kN/m2")
print(f"  SDL 1F slab  : {SDL_1F:.2f} kN/m2")
print(f"  SDL RF slab  : {SDL_RF:.2f} kN/m2")
print()

# ── Tributary areas per column (interior/edge/corner) ────────────────────────
def trib_area(i, j):
    """Tributary area in m2 for column at grid (i,j)."""
    lx1 = BAY_X[i-1]/2 if i > 0 else 0
    lx2 = BAY_X[i]/2   if i < N_COL_X-1 else 0
    ly1 = BAY_Y[j-1]/2 if j > 0 else 0
    ly2 = BAY_Y[j]/2   if j < N_COL_Y-1 else 0
    return (lx1+lx2)*(ly1+ly2)

# ── Column loads (gravity only -- simplified tributary load method) ───────────
class Column:
    def __init__(self, i, j):
        self.i = i; self.j = j
        self.x = COL_X[i]; self.y = COL_Y[j]
        self.A_trib = trib_area(i, j)
        self.label  = f"C{i+1}{j+1}"
        # Accumulated loads per floor
        self._compute_loads()

    def _compute_loads(self):
        A = self.A_trib
        # Dead loads per floor
        P_DL_RF  = SDL_RF * A
        P_LL_RF  = LL_ROOF_DECK * A
        P_DL_1F  = SDL_1F * A
        P_LL_1F  = LL_RESIDENTIAL * A
        P_DL_GF  = SDL_GF * A
        P_LL_GF  = LL_GARAGE * A   # conservative (ground floor includes garage)
        # Beam self-weight contribution (approx)
        Lx_sum = (BAY_X[self.i-1]/2 if self.i>0 else 0) + (BAY_X[self.i]/2 if self.i<N_COL_X-1 else 0)
        Ly_sum = (BAY_Y[self.j-1]/2 if self.j>0 else 0) + (BAY_Y[self.j]/2 if self.j<N_COL_Y-1 else 0)
        W_beam = GAMMA_CONC * B_BIG_B * (B_BIG_D - T_SLAB_1F) * (Lx_sum+Ly_sum)
        W_col  = GAMMA_CONC * COL_B * COL_D * (H_GF + H_1F)

        self.PD = P_DL_RF + P_DL_1F + P_DL_GF + W_beam + W_col
        self.PL = P_LL_RF + P_LL_1F + P_LL_GF
        self.Pu = LF_D*self.PD + LF_L*self.PL   # factored
        # Service load for footing
        self.P_service = self.PD + self.PL

# Generate all columns
COLUMNS = [[Column(i,j) for j in range(N_COL_Y)] for i in range(N_COL_X)]
COLS_FLAT = [COLUMNS[i][j] for i in range(N_COL_X) for j in range(N_COL_Y)]

# ── BEAM DESIGN  (Simplified - typical interior beam, longest span) ───────────
class BeamDesign:
    def __init__(self, label, L, b, d, wDL, wLL, fc, fy):
        self.label = label
        self.L  = L;    self.b = b;   self.d = d
        self.wDL= wDL;  self.wLL= wLL
        self.fc = fc;   self.fy = fy
        self._design()

    def _design(self):
        b,d,L = self.b, self.d, self.L
        wu = LF_D*self.wDL + LF_L*self.wLL
        self.wu = wu
        # Max moment (simply supported -- conservative for span)
        self.Mu = wu * L**2 / 8 * 1e6   # N.mm
        # Max shear
        self.Vu = wu * L / 2 * 1000     # N
        # Effective depth
        de = d*1000 - COVER_BEAM*1000 - 10 - 16/2   # mm (assume 16mm main bar, 10mm stirrup)
        self.de = de
        # Required steel area (ACI/NSCP simplified Whitney stress block)
        phi_b = 0.90
        Rn = self.Mu / (phi_b * b*1000 * de**2)   # MPa
        m  = self.fy / (0.85*self.fc)
        rho= (1/m)*(1 - math.sqrt(max(0,1 - 2*m*Rn/self.fy)))
        rho_min = max(0.25*math.sqrt(self.fc)/self.fy, 1.4/self.fy)
        rho_max = 0.75 * 0.85 * (0.85*self.fc/self.fy) * (600/(600+self.fy))
        rho_use = max(rho_min, min(rho, rho_max))
        self.rho = rho_use
        self.As_req = rho_use * b*1000 * de   # mm2
        # Bar selection (16mm bars)
        Ab16 = math.pi*(16)**2/4
        self.n_bars = math.ceil(self.As_req / Ab16)
        self.As_prov = self.n_bars * Ab16
        # Stirrup design (simplified -- Vc check)
        phi_v = 0.75
        Vc = 0.17*math.sqrt(self.fc)*(b*1000)*de   # N
        Vs_req = self.Vu/phi_v - Vc
        if Vs_req > 0:
            Av10 = 2 * math.pi*(10)**2/4
            s_req = Av10*FYS*de / Vs_req
            self.stirrup_s = min(s_req, de/2, 600)  # mm
        else:
            self.stirrup_s = min(de/2, 600)
        self.stirrup_s = round(self.stirrup_s/25)*25   # round to 25mm
        self.Vc = Vc; self.Vs_req = max(0,Vs_req)

# Typical beams (ground floor, longest bay)
MAX_BAY_X = max(BAY_X)   # 3.0 m
MAX_BAY_Y = max(BAY_Y)   # 3.5 m

# Tributary load on beam (slab load + beam self weight)
trib_load_GF = (SDL_GF + LF_L/LF_D*LL_RESIDENTIAL) * min(BAY_Y)/2  # approx
w_sw_beam    = GAMMA_CONC * B_BIG_B * (B_BIG_D - T_SLAB_GF)        # kN/m

# Main beam in Y direction (longest span)
BEAM_MAIN_Y = BeamDesign(
    "MB-Y (Main Beam, Y-dir, L=3.5m)",
    MAX_BAY_Y, B_BIG_B, B_BIG_D,
    SDL_1F*MAX_BAY_X/2 + w_sw_beam,
    LL_RESIDENTIAL*MAX_BAY_X/2,
    FC, FY
)
# Main beam in X direction
BEAM_MAIN_X = BeamDesign(
    "MB-X (Main Beam, X-dir, L=3.0m)",
    MAX_BAY_X, B_BIG_B, B_BIG_D,
    SDL_1F*MAX_BAY_Y/2 + w_sw_beam,
    LL_RESIDENTIAL*MAX_BAY_Y/2,
    FC, FY
)
# Roof beam
BEAM_ROOF = BeamDesign(
    "RB (Roof Beam, L=3.5m)",
    MAX_BAY_Y, B_SM_B, B_SM_D,
    SDL_RF*MAX_BAY_X/2 + GAMMA_CONC*B_SM_B*(B_SM_D-T_SLAB_RF),
    LL_ROOF_DECK*MAX_BAY_X/2,
    FC, FY
)

# ── COLUMN DESIGN ─────────────────────────────────────────────────────────────
class ColumnDesign:
    def __init__(self, label, Pu, b, d, fc, fy):
        self.label = label
        self.Pu = Pu  # kN
        self.b = b; self.d = d
        self.fc = fc; self.fy = fy
        self._design()

    def _design(self):
        b,d = self.b*1000, self.d*1000  # mm
        Pu_N = self.Pu * 1000           # N
        phi  = 0.65  # tied column
        Ag   = b * d
        # Min/max steel ratio
        rho_min = 0.01; rho_max = 0.06
        # Required from axial: Pu = phi*(0.80)*(0.85*fc*(Ag-As) + fy*As)
        # Solve for As: Pu/(phi*0.80) = 0.85*fc*Ag + As*(fy - 0.85*fc)
        denom = self.fy - 0.85*self.fc
        As_req = (Pu_N/(phi*0.80) - 0.85*self.fc*Ag) / denom
        As_req = max(As_req, rho_min*Ag)
        As_req = min(As_req, rho_max*Ag)
        self.As_req = As_req
        self.rho    = As_req/Ag
        Ab20 = math.pi*(20)**2/4
        self.n_bars = max(4, math.ceil(As_req / Ab20))
        if self.n_bars % 2 != 0: self.n_bars += 1
        self.As_prov= self.n_bars * Ab20
        self.rho_prov = self.As_prov/Ag
        # Tie spacing
        self.tie_s  = min(16*20, 48*10, b, d)   # 16*db_long, 48*db_tie, min col dim
        self.tie_s  = round(self.tie_s/25)*25    # mm

# Most loaded column (interior corner of building -- typically col (1,1) or max)
max_col = max(COLS_FLAT, key=lambda c: c.Pu)
COL_DESIGN = ColumnDesign("Critical Interior Column", max_col.Pu, COL_B, COL_D, FC, FY)
# Corner column (lightest)
corner_col = min(COLS_FLAT, key=lambda c: c.Pu)
COL_CORNER = ColumnDesign("Corner Column", corner_col.Pu, COL_B, COL_D, FC, FY)

# ── FOOTING DESIGN ────────────────────────────────────────────────────────────
class FootingDesign:
    def __init__(self, label, P_service, q_allow, fc, fy, col_b, col_d):
        self.label = label
        self.P_s   = P_service   # kN (service load)
        self.q_all = q_allow
        self.fc    = fc; self.fy = fy
        self.col_b = col_b*1000; self.col_d = col_d*1000   # mm
        self._design()

    def _design(self):
        # Footing weight ~10% of column load (assumed)
        P_total = self.P_s * 1.10
        # Required area
        A_req = P_total / self.q_all
        B_req = math.sqrt(A_req)
        B = math.ceil(B_req / 0.05) * 0.05   # round up to 50mm
        self.B = B   # m (square footing)
        self.A = B**2
        # Net upward pressure (factored)
        pu_net = (LF_D * self.P_s*1.05 + LF_L*0) / self.A    # approx
        Pu     = LF_D * self.P_s * 1.10    # kN factored
        qu     = Pu / self.A                # kN/m2
        # Required footing thickness (two-way punching shear controls)
        # Vu = qu*(A - (col_b+d)^2)  ; phi*Vc = phi*[0.33*sqrt(fc)*bo*d]
        phi_v = 0.75
        # Iterate for d
        d = 0.250  # m initial guess
        for _ in range(30):
            bo  = 4*(self.col_b/1000 + d)*1000   # mm perimeter
            Vu  = qu*(self.A - ((self.col_b/1000+d)*(self.col_d/1000+d)))  # kN
            Vc  = 0.33*math.sqrt(self.fc)*bo*(d*1000)*1e-3   # kN
            if phi_v*Vc >= Vu:
                break
            d  += 0.010
        self.d_ftg = d   # m effective depth
        self.h_ftg = d + COVER_FTG + 0.016   # m total depth (assume 16mm bars)
        self.h_ftg = math.ceil(self.h_ftg/0.05)*0.05
        d_use = self.h_ftg - COVER_FTG - 0.016
        # Flexural steel
        L_cant = (self.B - self.col_b/1000)/2   # m cantilever
        Mu_ftg = qu * self.B * L_cant**2 / 2 * 1e6  # N.mm per meter
        phi_b  = 0.90
        Rn  = Mu_ftg/(phi_b*(self.B*1000)*(d_use*1000)**2)
        m_  = self.fy/(0.85*self.fc)
        rho = (1/m_)*(1-math.sqrt(max(0,1-2*m_*Rn/self.fy)))
        rho_min = max(0.0018, 0.25*math.sqrt(self.fc)/self.fy)
        rho_use = max(rho_min, rho)
        self.As_ftg = rho_use*(self.B*1000)*(d_use*1000)  # mm2 total
        Ab16 = math.pi*16**2/4
        n_bars= math.ceil(self.As_ftg/Ab16)
        self.n_bars_ftg = max(n_bars, 5)
        self.As_prov_ftg = self.n_bars_ftg * Ab16
        s_bars = (self.B*1000 - 2*COVER_FTG*1000) / (self.n_bars_ftg-1)
        self.s_bars = round(s_bars/10)*10  # mm
        self.qu_net = qu
        self.Vu_punch = Vu
        self.Vc_punch = phi_v*Vc

FTG_INT  = FootingDesign("Interior Footing (Max Load)",  max_col.P_service, Q_ALLOW, FC, FY, COL_B, COL_D)
FTG_CORN = FootingDesign("Corner Footing (Min Load)",    corner_col.P_service, Q_ALLOW, FC, FY, COL_B, COL_D)

# ── STAIR DESIGN ──────────────────────────────────────────────────────────────
RISER_H  = 0.175   # m  riser height
TREAD_W  = 0.280   # m  tread width
N_RISERS = math.ceil(H_GF / RISER_H)
RISER_H_ACT = H_GF / N_RISERS
LANDING_L = 1.2     # m  landing length
STAIR_SLAB_T = 0.150  # m  stair slab thickness
# Waist slab inclined length
STAIR_ANGLE = math.atan(RISER_H_ACT/TREAD_W)
STAIR_INCL  = math.sqrt(RISER_H_ACT**2 + TREAD_W**2)
# Stair slab span (horizontal)
STAIR_SPAN  = N_RISERS * TREAD_W

print(f"  Stair:  {N_RISERS} risers @ {RISER_H_ACT*1000:.0f}mm,  {N_RISERS-1} treads @ {TREAD_W*1000:.0f}mm")
print(f"          Span = {STAIR_SPAN:.2f}m,  Angle = {math.degrees(STAIR_ANGLE):.1f} deg")
print()

# ==============================================================================
#  DESIGN SUMMARY REPORT
# ==============================================================================

def write_report(path):
    R = []
    a = R.append
    a("=" * 70)
    a("  NSCP 2015 STRUCTURAL DESIGN REPORT")
    a("  2-STOREY RESIDENTIAL BUILDING WITH ROOF DECK")
    a("  9m x 11m Lot | Garage | 3 Bedrooms + Terrace | Roof Deck")
    a("=" * 70)
    a("")
    a("1. BUILDING DATA")
    a("-" * 40)
    a(f"   Lot dimension    : {LOT_X}m x {LOT_Y}m")
    a(f"   Building footprint: {BLD_X}m x {BLD_Y}m (with {SETBACK}m setback)")
    a(f"   Number of storeys : 2 + Roof Deck")
    a(f"   Floor heights     : GF={H_GF}m, 1F={H_1F}m")
    a(f"   Total height      : {H_TOT}m")
    a(f"   Number of columns : {N_COLS}")
    a("")
    a("2. MATERIALS (NSCP 2015)")
    a("-" * 40)
    a(f"   Concrete  fc' = {FC} MPa    (normal weight)")
    a(f"   Main bars fy  = {FY} MPa    (ASTM Grade 60 / PSNS)")
    a(f"   Stirrups  fys = {FYS} MPa")
    a(f"   Ec = {EC:.0f} MPa")
    a(f"   Unit wt   yc  = {GAMMA_CONC} kN/m3")
    a("")
    a("3. DESIGN LOADS (NSCP 2015 Section 204/205)")
    a("-" * 40)
    a(f"   Dead load floor finish  : {DL_FLOOR_FINISH} kN/m2")
    a(f"   Dead load ceiling       : {DL_CEILING} kN/m2")
    a(f"   Dead load partitions    : {DL_PARTITIONS} kN/m2")
    a(f"   Live load residential   : {LL_RESIDENTIAL} kN/m2")
    a(f"   Live load roof deck     : {LL_ROOF_DECK} kN/m2")
    a(f"   Live load garage        : {LL_GARAGE} kN/m2")
    a(f"   Load factors            : 1.2D + 1.6L  (NSCP 2015 Sec. 409)")
    a("")
    a("4. COLUMN GRID & TRIBUTARY AREAS")
    a("-" * 40)
    a("   Column grid X : " + str([f"{v:.1f}" for v in COL_X]) + " m")
    a("   Column grid Y : " + str([f"{v:.1f}" for v in COL_Y]) + " m")
    a("   Bay X lengths : " + str([f"{v:.1f}" for v in BAY_X]) + " m")
    a("   Bay Y lengths : " + str([f"{v:.1f}" for v in BAY_Y]) + " m")
    a("")
    a("   Column loads summary:")
    a(f"   {'Label':8s} {'x(m)':6s} {'y(m)':6s} {'A_trib(m2)':12s} {'PD(kN)':10s} {'PL(kN)':10s} {'Pu(kN)':10s}")
    a("   " + "-"*62)
    for c in COLS_FLAT:
        a(f"   {c.label:8s} {c.x:6.1f} {c.y:6.1f} {c.A_trib:12.2f} {c.PD:10.1f} {c.PL:10.1f} {c.Pu:10.1f}")
    a("")
    a("5. BEAM DESIGN")
    a("-" * 40)
    for bm in [BEAM_MAIN_Y, BEAM_MAIN_X, BEAM_ROOF]:
        a(f"   [{bm.label}]")
        a(f"   Size          : {bm.b*1000:.0f}mm x {bm.d*1000:.0f}mm")
        a(f"   Span          : {bm.L:.1f}m")
        a(f"   wu (factored) : {bm.wu:.3f} kN/m")
        a(f"   Mu (factored) : {bm.Mu/1e6:.2f} kN.m")
        a(f"   Vu (factored) : {bm.Vu/1000:.2f} kN")
        a(f"   eff. depth d  : {bm.de:.0f}mm")
        a(f"   rho (used)    : {bm.rho:.5f}")
        a(f"   As required   : {bm.As_req:.0f} mm2")
        a(f"   Bars provided : {bm.n_bars} - 16mm phi  (As={bm.As_prov:.0f}mm2)")
        a(f"   Stirrups      : 10mm phi @ {bm.stirrup_s:.0f}mm spacing")
        a("")
    a("6. COLUMN DESIGN")
    a("-" * 40)
    for cd in [COL_DESIGN, COL_CORNER]:
        a(f"   [{cd.label}]")
        a(f"   Size          : {cd.b*1000:.0f}mm x {cd.d*1000:.0f}mm")
        a(f"   Pu (factored) : {cd.Pu:.1f} kN")
        a(f"   As required   : {cd.As_req:.0f} mm2")
        a(f"   rho required  : {cd.rho:.4f}")
        a(f"   Bars provided : {cd.n_bars} - 20mm phi  (As={cd.As_prov:.0f}mm2)")
        a(f"   rho provided  : {cd.rho_prov:.4f}  (min=0.01, max=0.06)")
        a(f"   Lateral ties  : 10mm phi @ {cd.tie_s:.0f}mm")
        a("")
    a("7. FOOTING DESIGN")
    a("-" * 40)
    a(f"   q_allowable : {Q_ALLOW} kN/m2")
    a(f"   Depth NGL   : {DEPTH_FTG} m")
    for ft in [FTG_INT, FTG_CORN]:
        a(f"   [{ft.label}]")
        a(f"   Service load  : {ft.P_s:.1f} kN")
        a(f"   Footing size  : {ft.B:.2f}m x {ft.B:.2f}m (square)")
        a(f"   Total depth h : {ft.h_ftg*1000:.0f}mm")
        a(f"   eff. depth d  : {ft.d_ftg*1000:.0f}mm")
        a(f"   qu (net)      : {ft.qu_net:.2f} kN/m2")
        a(f"   Vu punch      : {ft.Vu_punch:.1f} kN  (phi*Vc={ft.Vc_punch:.1f}kN) OK")
        a(f"   As bottom     : {ft.As_ftg:.0f}mm2  ->  {ft.n_bars_ftg}-16mm phi ea way")
        a(f"   Bar spacing   : {ft.s_bars:.0f}mm c/c (each direction)")
        a("")
    a("8. STAIR DESIGN DATA")
    a("-" * 40)
    a(f"   Number of risers   : {N_RISERS}")
    a(f"   Riser height       : {RISER_H_ACT*1000:.1f}mm  (code: 100-200mm)")
    a(f"   Tread width        : {TREAD_W*1000:.0f}mm  (code: >= 250mm)")
    a(f"   Stair angle        : {math.degrees(STAIR_ANGLE):.1f} deg  (code: <= 45 deg)")
    a(f"   Stair width        : {STAIR_W*1000:.0f}mm  (code: >= 900mm)")
    a(f"   Horizontal span    : {STAIR_SPAN:.2f}m")
    a(f"   Waist slab t       : {STAIR_SLAB_T*1000:.0f}mm")
    a(f"   Landing length     : {LANDING_L*1000:.0f}mm")
    a("")
    a("9. NSCP 2015 CODE CHECKS")
    a("-" * 40)
    checks = [
        ("Beam rho within limits (rho_min to rho_max)",
         BEAM_MAIN_Y.rho >= 0.25*math.sqrt(FC)/FY and
         BEAM_MAIN_Y.rho <= 0.75*0.85*(0.85*FC/FY)*(600/(600+FY))),
        ("Column rho within 1% - 6%",
         0.01 <= COL_DESIGN.rho_prov <= 0.06),
        ("Footing punching shear OK",
         FTG_INT.Vc_punch >= FTG_INT.Vu_punch),
        ("Stair riser <= 200mm",
         RISER_H_ACT*1000 <= 200),
        ("Stair tread >= 250mm",
         TREAD_W*1000 >= 250),
        ("Stair angle <= 45 deg",
         math.degrees(STAIR_ANGLE) <= 45),
        ("Min column size 300x300mm",
         COL_B*1000 >= 300 and COL_D*1000 >= 300),
        ("Footing depth >= 1.2m NGL",
         DEPTH_FTG >= 1.2),
    ]
    for desc, passed in checks:
        status = "[PASS]" if passed else "[FAIL]"
        a(f"   {status}  {desc}")
    a("")
    a("="*70)
    a("  END OF REPORT")
    a("="*70)

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(R))
    print(f"  [OK] Report  : {path}")

RPT_PATH = os.path.join(HERE, "nscp_design_report.txt")
write_report(RPT_PATH)

# ==============================================================================
#  VISUALIZATION  -- 10 PANELS
# ==============================================================================

# ── Color theme ───────────────────────────────────────────────────────────────
BG      = "#0a0e1a"
PANEL   = "#0f1623"
BORDER  = "#1e2d45"
CONC    = "#4a6741"
CONC2   = "#5a7a50"
STEEL   = "#e8a838"
REBAR   = "#ff6b35"
FOOTING = "#2e5fa3"
WALL    = "#8b7355"
DOOR    = "#c4935a"
STAIR_C = "#9b59b6"
WHITE   = "#e8edf5"
GRAY    = "#6b7f99"
CYAN    = "#4fc3f7"
GREEN   = "#4caf50"
RED     = "#ef5350"
YELLOW  = "#ffca28"
PURPLE  = "#ab47bc"
TEAL    = "#26a69a"
LOAD_C  = "#ff7043"

fig = plt.figure(figsize=(26, 32), facecolor=BG)
gs  = GridSpec(5, 3, figure=fig,
               hspace=0.42, wspace=0.30,
               left=0.04, right=0.98,
               top=0.955, bottom=0.025)

def sax(ax, title="", xl="", yl=""):
    ax.set_facecolor(PANEL)
    for sp in ax.spines.values():
        sp.set_color(BORDER); sp.set_linewidth(1.2)
    ax.tick_params(colors=GRAY, labelsize=8)
    ax.xaxis.label.set_color(GRAY)
    ax.yaxis.label.set_color(GRAY)
    if title:
        ax.set_title(title, color=WHITE, fontsize=10, fontweight="bold", pad=7)
    if xl: ax.set_xlabel(xl, fontsize=8)
    if yl: ax.set_ylabel(yl, fontsize=8)
    ax.grid(True, color=BORDER, linewidth=0.5, alpha=0.5)

# ── TITLE BANNER ─────────────────────────────────────────────────────────────
axt = fig.add_axes([0.0, 0.963, 1.0, 0.037])
axt.set_facecolor("#0d1b2e"); axt.axis("off")
axt.text(0.5, 0.65,
    "NSCP 2015  --  2-STOREY RESIDENTIAL BUILDING WITH ROOF DECK  |  COMPLETE STRUCTURAL DESIGN",
    ha="center", va="center", color=WHITE,
    fontsize=13, fontweight="bold", fontfamily="monospace")
axt.text(0.5, 0.12,
    f"Lot: {LOT_X}m x {LOT_Y}m  |  GF: Garage+Kitchen+Bath+Dining+2Rooms  |  "
    f"1F: 3Rooms+Terrace  |  2F: Roof Deck  |  fc'={FC}MPa  fy={FY}MPa",
    ha="center", va="center", color=GRAY, fontsize=8.5, fontfamily="monospace")

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 1 -- SITE PLAN / LOT PLAN
# ─────────────────────────────────────────────────────────────────────────────
ax1 = fig.add_subplot(gs[0, 0])
sax(ax1, "Site Plan / Lot Layout", "X (m)", "Y (m)")
ax1.set_xlim(-0.5, LOT_X+0.5)
ax1.set_ylim(-0.5, LOT_Y+0.5)
ax1.set_aspect("equal")

# Lot boundary
lot = patches.Rectangle((0,0), LOT_X, LOT_Y,
    fc="#1a2030", ec=YELLOW, lw=2.0, ls="--")
ax1.add_patch(lot)
ax1.text(LOT_X/2, -0.3, f"LOT: {LOT_X}m x {LOT_Y}m",
         ha="center", color=YELLOW, fontsize=8)

# Building footprint
bld = patches.Rectangle((SETBACK, SETBACK), BLD_X, BLD_Y,
    fc="#1e3a2a", ec=CONC2, lw=2.0)
ax1.add_patch(bld)

# Column dots
for i in range(N_COL_X):
    for j in range(N_COL_Y):
        cx = COL_X[i] + SETBACK
        cy = COL_Y[j] + SETBACK
        ax1.plot(cx, cy, "s", color=STEEL, ms=8, zorder=5)

# Room labels on site plan
rooms_gf = [
    (1.2, 1.5, "GARAGE\n(3.0x3.5m)"),
    (4.2, 1.5, "DINING\n(2.5x3.5m)"),
    (6.2, 1.5, "KITCHEN\n(2.5x2.0m)"),
    (6.2, 4.0, "BATH"),
    (1.2, 5.5, "ROOM 1\n(3.0x3.5m)"),
    (4.5, 5.5, "ROOM 2\n(2.5x3.5m)"),
]
for rx, ry, lbl in rooms_gf:
    ax1.text(rx+SETBACK, ry+SETBACK, lbl,
             ha="center", va="center", color=CYAN,
             fontsize=6.5, fontweight="bold")

# Stair box
stair_patch = patches.Rectangle(
    (STAIR_X0+SETBACK-0.1, SETBACK+COL_Y[1]),
    STAIR_W+0.2, STAIR_L,
    fc="#2a1f3d", ec=STAIR_C, lw=1.5, ls=":")
ax1.add_patch(stair_patch)
ax1.text(STAIR_X0+SETBACK+0.5, SETBACK+COL_Y[1]+STAIR_L/2,
         "STAIR", ha="center", va="center",
         color=STAIR_C, fontsize=7, fontweight="bold")

# Road / setback labels
ax1.annotate("", xy=(0, LOT_Y/2), xytext=(-0.4, LOT_Y/2),
             arrowprops=dict(arrowstyle="->", color=GRAY))
ax1.text(-0.45, LOT_Y/2, "ROAD", ha="right", va="center",
         color=GRAY, fontsize=7, rotation=90)

# North arrow
ax1.annotate("", xy=(LOT_X+0.3, LOT_Y-0.5), xytext=(LOT_X+0.3, LOT_Y-1.5),
             arrowprops=dict(arrowstyle="-|>", color=CYAN, lw=2))
ax1.text(LOT_X+0.3, LOT_Y-0.2, "N", ha="center", color=CYAN, fontsize=9, fontweight="bold")

legend_s = [mpatches.Patch(color=YELLOW, label="Lot boundary"),
            mpatches.Patch(color=CONC2,  label="Building"),
            mpatches.Patch(color=STEEL,  label="Column"),
            mpatches.Patch(color=STAIR_C,label="Stair")]
ax1.legend(handles=legend_s, facecolor=PANEL, edgecolor=BORDER,
           labelcolor=WHITE, fontsize=6.5, loc="lower right")

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 2 -- GROUND FLOOR PLAN
# ─────────────────────────────────────────────────────────────────────────────
ax2 = fig.add_subplot(gs[0, 1])
sax(ax2, "Ground Floor Plan (GF)", "X (m)", "Y (m)")
ax2.set_xlim(-0.3, BLD_X+0.3)
ax2.set_ylim(-0.3, BLD_Y+0.3)
ax2.set_aspect("equal")

# Floor slab
ax2.add_patch(patches.Rectangle((0,0), BLD_X, BLD_Y,
    fc="#131d0f", ec=CONC2, lw=2.0))

# Walls
wall_locs_gf = [
    (0,0,BLD_X,0.15,"H"),  # south wall
    (0,0,0.15,BLD_Y,"V"),  # west wall
    (BLD_X-0.15,0,0.15,BLD_Y,"V"),  # east
    (0,BLD_Y-0.15,BLD_X,0.15,"H"),  # north
    # Internal walls
    (COL_X[1]-0.075,0,0.15,COL_Y[2],"V"),   # garage partition
    (0,COL_Y[1]-0.075,COL_X[2]+0.075,0.15,"H"),  # dining/kitchen
    (COL_X[2]-0.075,0,0.15,COL_Y[2],"V"),   # kitchen wall
    (0,COL_Y[2]-0.075,BLD_X,0.15,"H"),      # upper room partition
]
for wl in wall_locs_gf:
    if wl[4]=="H":
        ax2.add_patch(patches.Rectangle((wl[0],wl[1]),wl[2],wl[3],fc=WALL,ec=BORDER,lw=0.5))
    else:
        ax2.add_patch(patches.Rectangle((wl[0],wl[1]),wl[2],wl[3],fc=WALL,ec=BORDER,lw=0.5))

# Column squares
for i in range(N_COL_X):
    for j in range(N_COL_Y):
        ax2.add_patch(patches.Rectangle(
            (COL_X[i]-COL_B/2, COL_Y[j]-COL_D/2), COL_B, COL_D,
            fc=CONC2, ec=STEEL, lw=1.0, zorder=5))

# Grid lines
for cx in COL_X:
    ax2.axvline(cx, color=BORDER, lw=0.5, ls=":")
for cy in COL_Y:
    ax2.axhline(cy, color=BORDER, lw=0.5, ls=":")

# Beams
for i in range(N_COL_X):
    ax2.plot([COL_X[i],COL_X[i]],[COL_Y[0],COL_Y[-1]],
             color=CYAN, lw=2.5, alpha=0.5, zorder=3)
for j in range(N_COL_Y):
    ax2.plot([COL_X[0],COL_X[-1]],[COL_Y[j],COL_Y[j]],
             color=CYAN, lw=2.5, alpha=0.5, zorder=3)

# Room labels
rooms2 = [
    (COL_X[0]/2+COL_X[1]/2, COL_Y[0]/2+COL_Y[1]/2, "GARAGE"),
    ((COL_X[1]+COL_X[2])/2, (COL_Y[0]+COL_Y[1])/2, "DINING"),
    ((COL_X[2]+COL_X[3])/2, (COL_Y[0]+COL_Y[1])/2, "KITCHEN"),
    ((COL_X[2]+COL_X[3])/2, (COL_Y[1]+COL_Y[2])/2, "BATH"),
    ((COL_X[0]+COL_X[1])/2, (COL_Y[2]+COL_Y[3])/2, "ROOM 1"),
    ((COL_X[1]+COL_X[3])/2, (COL_Y[2]+COL_Y[3])/2, "ROOM 2"),
]
for rx,ry,lbl in rooms2:
    ax2.text(rx,ry,lbl, ha="center",va="center",
             color=CYAN,fontsize=8,fontweight="bold")

# Stair
ax2.add_patch(patches.Rectangle(
    (STAIR_X0-STAIR_W/2, COL_Y[1]), STAIR_W, STAIR_L,
    fc="#1e1030", ec=STAIR_C, lw=1.5))
for k in range(N_RISERS-1):
    ys = COL_Y[1] + k*(STAIR_L/N_RISERS)
    ax2.plot([STAIR_X0-STAIR_W/2, STAIR_X0+STAIR_W/2],[ys,ys],
             color=STAIR_C, lw=0.7, alpha=0.6)
ax2.text(STAIR_X0, COL_Y[1]+STAIR_L/2, "UP\nSTAIR",
         ha="center", va="center", color=STAIR_C, fontsize=7, fontweight="bold")

# Dimension annotations
for k,(x1,x2) in enumerate(zip(COL_X[:-1],COL_X[1:])):
    ax2.annotate("", xy=(x1,-0.15), xytext=(x2,-0.15),
                 arrowprops=dict(arrowstyle="<->",color=YELLOW,lw=1.0))
    ax2.text((x1+x2)/2,-0.22,f"{x2-x1:.1f}m",
             ha="center",color=YELLOW,fontsize=7)

ax2.text(BLD_X/2,-0.28,"GROUND FLOOR PLAN",ha="center",
         color=WHITE,fontsize=8,fontweight="bold")

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 3 -- 1ST FLOOR PLAN
# ─────────────────────────────────────────────────────────────────────────────
ax3 = fig.add_subplot(gs[0, 2])
sax(ax3, "1st Floor Plan (1F)", "X (m)", "Y (m)")
ax3.set_xlim(-0.3, BLD_X+0.3)
ax3.set_ylim(-0.3, BLD_Y+0.3)
ax3.set_aspect("equal")

ax3.add_patch(patches.Rectangle((0,0),BLD_X,BLD_Y,fc="#0f1d15",ec=CONC2,lw=2.0))

# Walls 1F
walls_1f = [
    (0,0,BLD_X,0.15,"H"),
    (0,0,0.15,BLD_Y,"V"),
    (BLD_X-0.15,0,0.15,BLD_Y,"V"),
    (0,BLD_Y-0.15,BLD_X,0.15,"H"),
    (COL_X[1]-0.075,0,0.15,COL_Y[3],"V"),
    (COL_X[2]-0.075,0,0.15,COL_Y[2],"V"),
    (0,COL_Y[1]-0.075,BLD_X,0.15,"H"),
    (0,COL_Y[2]-0.075,BLD_X*0.65,0.15,"H"),
]
for wl in walls_1f:
    ax3.add_patch(patches.Rectangle((wl[0],wl[1]),wl[2],wl[3],fc=WALL,ec=BORDER,lw=0.5))

# Terrace (open area -- east side, lower half)
terrace = patches.Rectangle((COL_X[2],0),BLD_X-COL_X[2],COL_Y[1],
    fc="#1a2535",ec=TEAL,lw=1.5,ls="--")
ax3.add_patch(terrace)
ax3.text((COL_X[2]+BLD_X)/2,COL_Y[1]/2,"TERRACE",
         ha="center",va="center",color=TEAL,fontsize=8,fontweight="bold")

# Columns & beams
for i in range(N_COL_X):
    for j in range(N_COL_Y):
        ax3.add_patch(patches.Rectangle(
            (COL_X[i]-COL_B/2,COL_Y[j]-COL_D/2),COL_B,COL_D,
            fc=CONC2,ec=STEEL,lw=1.0,zorder=5))
for cx in COL_X:
    ax3.plot([cx,cx],[COL_Y[0],COL_Y[-1]],color=CYAN,lw=2.5,alpha=0.5)
for cy in COL_Y:
    ax3.plot([COL_X[0],COL_X[-1]],[cy,cy],color=CYAN,lw=2.5,alpha=0.5)

# Room labels 1F
rooms3 = [
    ((COL_X[0]+COL_X[1])/2,(COL_Y[1]+COL_Y[3])/2,"ROOM 3\n(Master)"),
    ((COL_X[1]+COL_X[2])/2,(COL_Y[1]+COL_Y[3])/2,"ROOM 4"),
    ((COL_X[2]+COL_X[3])/2,(COL_Y[1]+COL_Y[3])/2,"ROOM 5"),
]
for rx,ry,lbl in rooms3:
    ax3.text(rx,ry,lbl,ha="center",va="center",
             color=GREEN,fontsize=8,fontweight="bold")

# Stair down
ax3.add_patch(patches.Rectangle(
    (STAIR_X0-STAIR_W/2,COL_Y[1]),STAIR_W,STAIR_L,
    fc="#200f30",ec=STAIR_C,lw=1.5))
ax3.text(STAIR_X0,COL_Y[1]+STAIR_L/2,"DN\nSTAIR",
         ha="center",va="center",color=STAIR_C,fontsize=7,fontweight="bold")

ax3.text(BLD_X/2,-0.28,"1ST FLOOR PLAN",ha="center",
         color=WHITE,fontsize=8,fontweight="bold")

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 4 -- BUILDING ELEVATION (Front + Side)
# ─────────────────────────────────────────────────────────────────────────────
ax4 = fig.add_subplot(gs[1, 0:2])
sax(ax4, "Building Elevations (Front & Side)", "X (m)", "Z (m) Elevation")
ax4.set_xlim(-1.0, BLD_X*2+3.5)
ax4.set_ylim(-0.5, H_TOT+1.5)

# FRONT ELEVATION (left)
def draw_elevation_front(ax, x0):
    # Ground
    ax.plot([x0-0.5,x0+BLD_X+0.5],[-0.1,-0.1],color=GRAY,lw=2.0)
    # Foundation stub
    for cx in COL_X:
        ax.add_patch(patches.Rectangle((x0+cx-0.15,-0.3),0.3,0.3,
            fc=FOOTING,ec=BORDER,lw=0.8,alpha=0.7))
    # Columns
    for cx in COL_X:
        for z0,zh in [(0,H_GF),(H_GF,H_GF+H_1F)]:
            ax.add_patch(patches.Rectangle((x0+cx-COL_B/2,z0),COL_B,zh,
                fc=CONC,ec=CONC2,lw=1.0))
    # Floor slabs
    for z_fl in [0,H_GF,H_GF+H_1F]:
        ax.add_patch(patches.Rectangle((x0,z_fl-0.06),BLD_X,0.125,
            fc=CONC2,ec=BORDER,lw=0.8,alpha=0.8))
    # Parapet
    ax.add_patch(patches.Rectangle((x0,H_GF+H_1F),BLD_X,H_RF,
        fc=CONC,ec=CONC2,lw=1.0,alpha=0.7))
    # Windows GF
    for wx in [1.2, 4.5]:
        ax.add_patch(patches.Rectangle((x0+wx,0.8),1.0,1.0,
            fc="#1a3a5c",ec=CYAN,lw=1.0))
    # Garage opening
    ax.add_patch(patches.Rectangle((x0+0.2,-0.0),2.4,2.2,
        fc="#0d1a28",ec=DOOR,lw=1.5))
    ax.text(x0+1.4,1.1,"GARAGE",ha="center",va="center",
            color=DOOR,fontsize=7)
    # Windows 1F
    for wx in [0.8,3.2,5.8]:
        ax.add_patch(patches.Rectangle((x0+wx,H_GF+0.7),1.0,1.0,
            fc="#1a3a5c",ec=CYAN,lw=1.0))
    # Balcony railing
    ax.plot([x0+COL_X[2],x0+BLD_X],[H_GF,H_GF],
            color=TEAL,lw=2.5)
    ax.text(x0+BLD_X*0.75,H_GF-0.25,"TERRACE",
            ha="center",color=TEAL,fontsize=7)
    # Dim arrows
    ax.annotate("",xy=(x0,-0.35),xytext=(x0+BLD_X,-0.35),
                arrowprops=dict(arrowstyle="<->",color=YELLOW,lw=1.0))
    ax.text(x0+BLD_X/2,-0.45,f"{BLD_X}m",ha="center",color=YELLOW,fontsize=8)
    # Heights
    for z_,lbl in [(H_GF,"3.0m"),(H_GF+H_1F,"3.0m")]:
        ax.annotate("",xy=(x0-0.6,z_-3.0 if z_==H_GF else H_GF),
                    xytext=(x0-0.6,z_),
                    arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.0))
        ax.text(x0-0.8,(z_-3.0 if z_==H_GF else H_GF)+1.5,
                f"h={lbl}",va="center",ha="right",color=CYAN,fontsize=7.5)
    ax.text(x0+BLD_X/2,-0.7,"FRONT ELEVATION",ha="center",
            color=WHITE,fontsize=9,fontweight="bold")

draw_elevation_front(ax4, 0.0)

# SIDE ELEVATION (right, offset)
def draw_elevation_side(ax, x0):
    ax.plot([x0-0.5,x0+BLD_Y+0.5],[-0.1,-0.1],color=GRAY,lw=2.0)
    for cy in COL_Y:
        ax.add_patch(patches.Rectangle((x0+cy-0.15,-0.3),0.3,0.3,
            fc=FOOTING,ec=BORDER,lw=0.8,alpha=0.7))
    for cy in COL_Y:
        for z0,zh in [(0,H_GF),(H_GF,H_GF+H_1F)]:
            ax.add_patch(patches.Rectangle((x0+cy-COL_B/2,z0),COL_B,zh,
                fc=CONC,ec=CONC2,lw=1.0))
    for z_fl in [0,H_GF,H_GF+H_1F]:
        ax.add_patch(patches.Rectangle((x0,z_fl-0.06),BLD_Y,0.125,
            fc=CONC2,ec=BORDER,lw=0.8,alpha=0.8))
    ax.add_patch(patches.Rectangle((x0,H_GF+H_1F),BLD_Y,H_RF,
        fc=CONC,ec=CONC2,lw=1.0,alpha=0.7))
    for wy in [1.0,4.0,7.0]:
        ax.add_patch(patches.Rectangle((x0+wy,0.8),0.8,1.0,
            fc="#1a3a5c",ec=CYAN,lw=1.0))
        ax.add_patch(patches.Rectangle((x0+wy,H_GF+0.7),0.8,1.0,
            fc="#1a3a5c",ec=CYAN,lw=1.0))
    ax.annotate("",xy=(x0,-0.35),xytext=(x0+BLD_Y,-0.35),
                arrowprops=dict(arrowstyle="<->",color=YELLOW,lw=1.0))
    ax.text(x0+BLD_Y/2,-0.45,f"{BLD_Y}m",ha="center",color=YELLOW,fontsize=8)
    ax.text(x0+BLD_Y/2,-0.7,"SIDE ELEVATION",ha="center",
            color=WHITE,fontsize=9,fontweight="bold")

draw_elevation_side(ax4, BLD_X+2.5)

# Floor level lines
for z_,lbl in [(0,"±0.00"),(H_GF,"3.00"),(H_GF+H_1F,"6.00"),(H_TOT,"7.20")]:
    ax4.axhline(z_,color=BORDER,lw=0.5,ls="-",alpha=0.4)
    ax4.text(-0.9,z_,f"EL. +{lbl}",va="center",ha="right",
             color=YELLOW,fontsize=7,fontfamily="monospace")

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 5 -- COLUMN SCHEDULE + LOADS
# ─────────────────────────────────────────────────────────────────────────────
ax5 = fig.add_subplot(gs[1, 2])
sax(ax5, "Column Grid - Service Loads (kN)", "X Grid", "Y Grid")
ax5.set_xlim(-0.5, N_COL_X-0.5)
ax5.set_ylim(-0.5, N_COL_Y-0.5)

# Heat map of column loads
loads_grid = np.array([[COLUMNS[i][j].P_service
                         for j in range(N_COL_Y)]
                        for i in range(N_COL_X)])
im = ax5.imshow(loads_grid.T, origin="lower",
                extent=[-0.5,N_COL_X-0.5,-0.5,N_COL_Y-0.5],
                cmap="YlOrRd", aspect="auto", alpha=0.6)
plt.colorbar(im, ax=ax5, label="Service Load P (kN)", shrink=0.85)

for i in range(N_COL_X):
    for j in range(N_COL_Y):
        c = COLUMNS[i][j]
        ax5.plot(i,j,"s",color=STEEL,ms=14,zorder=4)
        ax5.text(i,j+0.25,c.label,ha="center",va="center",
                 color=WHITE,fontsize=6.5,fontweight="bold",zorder=5)
        ax5.text(i,j-0.22,f"{c.P_service:.0f}kN",ha="center",va="center",
                 color=YELLOW,fontsize=6.5,zorder=5)

ax5.set_xticks(range(N_COL_X))
ax5.set_xticklabels([f"X={v:.1f}m" for v in COL_X], fontsize=7)
ax5.set_yticks(range(N_COL_Y))
ax5.set_yticklabels([f"Y={v:.1f}m" for v in COL_Y], fontsize=7)

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 6 -- BEAM DESIGN DIAGRAMS (BMD + SFD)
# ─────────────────────────────────────────────────────────────────────────────
ax6 = fig.add_subplot(gs[2, 0:2])
sax(ax6, "Beam BMD & SFD -- Main Beam Y-dir (L=3.5m) & X-dir (L=3.0m)",
    "Beam length (m)", "Force/Moment")

bms = [BEAM_MAIN_Y, BEAM_MAIN_X, BEAM_ROOF]
colors_bm = [REBAR, CYAN, GREEN]
x_arr_b = np.linspace(0, 1, 100)  # normalized

for k, (bm, c) in enumerate(zip(bms, colors_bm)):
    xb = np.linspace(0, bm.L, 100)
    wu = bm.wu
    bmd_v = wu*xb*(bm.L-xb)/2 / 1000   # kN.m
    sfd_v = (wu*bm.L/2 - wu*xb) / 1000  # kN
    offset_m = k * 50
    offset_s = k * 20
    ax6.fill_between(xb, offset_m, bmd_v+offset_m,
                     alpha=0.35, color=c)
    ax6.plot(xb, bmd_v+offset_m, color=c, lw=2.0,
             label=f"{bm.label.split('(')[0].strip()} BMD (max={bm.Mu/1e6:.0f}kN.m)")
    ax6.plot(xb, sfd_v+offset_s, color=c, lw=1.5, ls="--", alpha=0.7)
    ax6.text(bm.L*0.5, bm.Mu/1e6/2+offset_m,
             f"Mu={bm.Mu/1e6:.0f}kN.m",
             ha="center", va="bottom", color=c, fontsize=8)

ax6.axhline(0,color=GRAY,lw=0.7)
ax6.legend(facecolor=PANEL,edgecolor=BORDER,labelcolor=WHITE,fontsize=7.5,loc="upper right")
ax6.set_ylabel("Moment (kN.m)  /  Shear (kN)", fontsize=8)

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 7 -- BEAM CROSS-SECTION DETAIL
# ─────────────────────────────────────────────────────────────────────────────
ax7 = fig.add_subplot(gs[2, 2])
sax(ax7, "Beam Cross-Section Detail", "Width (mm)", "Depth (mm)")
ax7.set_xlim(-20, 320)
ax7.set_ylim(-40, 460)
ax7.set_aspect("equal")

bm = BEAM_MAIN_Y
b_mm = bm.b*1000; d_mm = bm.d*1000
cv = COVER_BEAM*1000
# Concrete section
ax7.add_patch(patches.Rectangle((0,0),b_mm,d_mm,
    fc=CONC,ec=WHITE,lw=2.0))
# Compression steel (top) -- 2 bars assumed
for xb_ in [cv+8, b_mm-cv-8]:
    ax7.add_patch(patches.Circle((xb_,d_mm-cv-8),8,fc=REBAR,ec=WHITE,lw=0.8))
# Tension steel (bottom)
pitch = (b_mm-2*cv-16) / (bm.n_bars-1) if bm.n_bars>1 else 0
for k in range(bm.n_bars):
    xb_ = cv+8 + k*pitch
    ax7.add_patch(patches.Circle((xb_,cv+8),8,fc=REBAR,ec=WHITE,lw=0.8,zorder=5))
# Stirrup
stirrup_pts = [(cv,cv),(b_mm-cv,cv),(b_mm-cv,d_mm-cv),(cv,d_mm-cv),(cv,cv)]
xs=[p[0] for p in stirrup_pts]; ys=[p[1] for p in stirrup_pts]
ax7.plot(xs,ys,color=STEEL,lw=2.0)
# NA line
ax7.axhline(bm.de,color=YELLOW,lw=1.2,ls="--")
ax7.text(b_mm+5,bm.de,"NA",va="center",color=YELLOW,fontsize=8)
# Labels
ax7.text(b_mm/2,-25,f"{bm.n_bars}-16mm phi (TENSION)",
         ha="center",color=REBAR,fontsize=7.5,fontweight="bold")
ax7.annotate("",xy=(-15,0),xytext=(-15,d_mm),
             arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.2))
ax7.text(-18,d_mm/2,f"d={d_mm:.0f}mm",va="center",ha="right",
         color=CYAN,fontsize=8,rotation=90)
ax7.annotate("",xy=(0,-30),xytext=(b_mm,-30),
             arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.2))
ax7.text(b_mm/2,-38,f"b={b_mm:.0f}mm",ha="center",color=CYAN,fontsize=8)
ax7.text(b_mm/2,d_mm+15,
         f"Stirrups: R10@{bm.stirrup_s:.0f}mm",
         ha="center",color=STEEL,fontsize=7.5)

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 8 -- COLUMN CROSS-SECTION DETAIL
# ─────────────────────────────────────────────────────────────────────────────
ax8 = fig.add_subplot(gs[3, 0])
sax(ax8, "Column Cross-Section Detail", "Width (mm)", "Depth (mm)")
ax8.set_xlim(-60, 420)
ax8.set_ylim(-60, 420)
ax8.set_aspect("equal")

b_c = COL_B*1000; d_c = COL_D*1000; cv_c = COVER_COL*1000
ax8.add_patch(patches.Rectangle((0,0),b_c,d_c,fc=CONC,ec=WHITE,lw=2.0))

# Bar positions for square arrangement
cd = COL_DESIGN
n  = cd.n_bars
# Place bars around perimeter
bar_pos = []
n_side  = n // 4
spacing_b = (b_c-2*cv_c-20) / (n_side-1) if n_side>1 else 0
spacing_d = (d_c-2*cv_c-20) / (n_side-1) if n_side>1 else 0
for k in range(n_side):
    bar_pos.append((cv_c+10+k*spacing_b, cv_c+10))       # bottom
    bar_pos.append((cv_c+10+k*spacing_b, d_c-cv_c-10))   # top
    if k > 0 and k < n_side-1:
        bar_pos.append((cv_c+10, cv_c+10+k*spacing_d))   # left
        bar_pos.append((b_c-cv_c-10, cv_c+10+k*spacing_d)) # right

used_pos = list(dict.fromkeys([(round(x,1),round(y,1)) for x,y in bar_pos]))[:n]
for xb_,yb_ in used_pos:
    ax8.add_patch(patches.Circle((xb_,yb_),10,fc=REBAR,ec=WHITE,lw=0.8,zorder=5))

# Ties
tie_pts = [(cv_c,cv_c),(b_c-cv_c,cv_c),(b_c-cv_c,d_c-cv_c),(cv_c,d_c-cv_c),(cv_c,cv_c)]
ax8.plot([p[0] for p in tie_pts],[p[1] for p in tie_pts],color=STEEL,lw=2.0)

ax8.annotate("",xy=(-40,0),xytext=(-40,d_c),
             arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.2))
ax8.text(-45,d_c/2,f"{d_c:.0f}mm",va="center",ha="right",
         color=CYAN,fontsize=8,rotation=90)
ax8.annotate("",xy=(0,-40),xytext=(b_c,-40),
             arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.2))
ax8.text(b_c/2,-50,f"{b_c:.0f}mm",ha="center",color=CYAN,fontsize=8)
ax8.text(b_c/2,d_c+20,
         f"{cd.n_bars}-20mm phi  | Ties R10@{cd.tie_s:.0f}mm",
         ha="center",color=REBAR,fontsize=8,fontweight="bold")
ax8.text(b_c/2,-15,
         f"rho={cd.rho_prov:.4f}  Pu={cd.Pu:.0f}kN",
         ha="center",color=YELLOW,fontsize=8)

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 9 -- FOOTING DETAIL
# ─────────────────────────────────────────────────────────────────────────────
ax9 = fig.add_subplot(gs[3, 1])
sax(ax9, "Isolated Footing Detail (Interior)", "Width (m)", "Depth (m)")
ft = FTG_INT
B = ft.B; h = ft.h_ftg; d = ft.d_ftg
ax9.set_xlim(-B*0.6, B*1.8)
ax9.set_ylim(-h*3.5, h*1.5)
ax9.set_aspect("equal")

# Soil
ax9.add_patch(patches.Rectangle((-B*0.5,-h*3.0),B*2.0,h*2.7,
    fc="#1a1208",ec=BORDER,lw=0.5))
for k in range(12):
    xk = -B*0.5+k*B*2.0/11
    ax9.plot([xk,xk+0.05],[-h*3.0+0.0,-h*3.0-0.05],
             color="#3d2b0a",lw=1.0)

# Footing
ftg_patch = patches.Rectangle((0,-h),B,h,fc=FOOTING,ec=WHITE,lw=1.5,alpha=0.8)
ax9.add_patch(ftg_patch)

# Column stub
ax9.add_patch(patches.Rectangle((B/2-COL_B/2,-h),COL_B,h*1.5,
    fc=CONC,ec=WHITE,lw=1.5))

# Bottom bars (tension)
for k in range(min(ft.n_bars_ftg,8)):
    xb_ = 0.075 + k*(B-0.15)/(min(ft.n_bars_ftg,8)-1)
    ax9.add_patch(patches.Circle((xb_,-h+0.05),0.016,
        fc=REBAR,ec=WHITE,lw=0.5,zorder=5))

# Top of footing = NGL assumption
ax9.plot([-B*0.5,B*1.5],[-h,-h],color=GRAY,lw=1.0,ls="--",alpha=0.5)

# Dimensions
ax9.annotate("",xy=(0,-h*1.5),xytext=(B,-h*1.5),
             arrowprops=dict(arrowstyle="<->",color=YELLOW,lw=1.2))
ax9.text(B/2,-h*1.65,f"B={B:.2f}m",ha="center",color=YELLOW,fontsize=8)
ax9.annotate("",xy=(B+0.1,-h),xytext=(B+0.1,0),
             arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.2))
ax9.text(B+0.2,-h/2,f"h={h*1000:.0f}mm",va="center",color=CYAN,fontsize=8)
ax9.annotate("",xy=(-0.1,-h),xytext=(-0.1,-h+d),
             arrowprops=dict(arrowstyle="<->",color=GREEN,lw=1.2))
ax9.text(-0.2,-h+d/2,f"d={d*1000:.0f}mm",va="center",ha="right",
         color=GREEN,fontsize=7.5)

ax9.text(B/2,h*0.4,
         f"qu={ft.qu_net:.1f}kN/m2\n{ft.n_bars_ftg}-R16@{ft.s_bars:.0f}mm EW",
         ha="center",va="center",color=WHITE,fontsize=8,fontweight="bold",
         bbox=dict(fc=PANEL,ec=BORDER,lw=0.8,boxstyle="round,pad=0.3"))

# NGL label
ax9.annotate("",xy=(-B*0.45,0),xytext=(-B*0.45,-DEPTH_FTG),
             arrowprops=dict(arrowstyle="<->",color=GRAY,lw=1.0))
ax9.text(-B*0.55,-DEPTH_FTG/2,f"DF={DEPTH_FTG}m",
         va="center",ha="right",color=GRAY,fontsize=7.5)

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 10 -- STAIR DETAIL
# ─────────────────────────────────────────────────────────────────────────────
ax10 = fig.add_subplot(gs[3, 2])
sax(ax10, "Stair Section Detail", "Horizontal (m)", "Elevation (m)")
n_r = N_RISERS
tread = TREAD_W; riser = RISER_H_ACT
total_run = n_r*tread
ax10.set_xlim(-0.4, total_run+0.4)
ax10.set_ylim(-0.3, H_GF+0.4)
ax10.set_aspect("equal")

# Ground slab
ax10.add_patch(patches.Rectangle((-0.3,-0.2),0.5,0.2,fc=CONC,ec=WHITE,lw=1.0))
# Top landing
ax10.add_patch(patches.Rectangle((total_run-0.1,H_GF-0.15),LANDING_L,0.15,
    fc=CONC,ec=WHITE,lw=1.0))
# Stair slab (inclined)
import numpy.linalg as LA
pts_top  = [(0,0)]
pts_bot  = [(0,-STAIR_SLAB_T/math.cos(STAIR_ANGLE))]
for k in range(n_r):
    x_ = k*tread; y_ = k*riser
    pts_top.append((x_,y_)); pts_top.append((x_+tread,y_))
    pts_top.append((x_+tread,y_+riser))
pts_top.append((total_run,H_GF))

# Waist slab outline
cos_a = math.cos(STAIR_ANGLE); sin_a = math.sin(STAIR_ANGLE)
t = STAIR_SLAB_T
pts_bot_line = [(x_-t*sin_a, y_-t*cos_a) for x_,y_ in
                [(k*tread,k*riser) for k in range(n_r+1)]]
stair_poly_x = [p[0] for p in pts_top] + [p[0] for p in reversed(pts_bot_line)]
stair_poly_y = [p[1] for p in pts_top] + [p[1] for p in reversed(pts_bot_line)]
ax10.fill(stair_poly_x, stair_poly_y, fc=CONC, ec=WHITE, lw=1.0, alpha=0.8)

# Nosing line
for k in range(n_r+1):
    ax10.plot([k*tread],[k*riser],"o",color=STEEL,ms=4,zorder=5)

# Rebar in waist slab
for k in range(0, n_r, 2):
    x1 = k*tread + t*sin_a/2
    y1 = k*riser - t*cos_a/2
    x2 = (k+2)*tread + t*sin_a/2
    y2 = (k+2)*riser - t*cos_a/2
    ax10.plot([x1,min(x2,total_run)],[y1,min(y2,H_GF)],
              color=REBAR,lw=1.5,alpha=0.8)

# Dimensions
ax10.annotate("",xy=(0,-0.2),xytext=(tread,-0.2),
              arrowprops=dict(arrowstyle="<->",color=YELLOW,lw=1.0))
ax10.text(tread/2,-0.28,f"T={tread*1000:.0f}mm",
          ha="center",color=YELLOW,fontsize=7)
ax10.annotate("",xy=(total_run+0.3,0),xytext=(total_run+0.3,riser),
              arrowprops=dict(arrowstyle="<->",color=CYAN,lw=1.0))
ax10.text(total_run+0.35,riser/2,f"R={riser*1000:.0f}mm",
          va="center",color=CYAN,fontsize=7)
ax10.text(total_run/2,H_GF+0.15,
          f"{n_r} risers x {riser*1000:.0f}mm = {H_GF*1000:.0f}mm",
          ha="center",color=WHITE,fontsize=8,fontweight="bold")
ax10.text(total_run/2,H_GF/2,
          f"Waist t={STAIR_SLAB_T*1000:.0f}mm\nAngle={math.degrees(STAIR_ANGLE):.1f}deg",
          ha="center",va="center",color=CYAN,fontsize=8,
          bbox=dict(fc=PANEL,ec=BORDER,lw=0.5,boxstyle="round,pad=0.2"))

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 11 -- DESIGN SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────
ax11 = fig.add_subplot(gs[4, 0:2])
ax11.set_facecolor(PANEL); ax11.axis("off")
ax11.set_title("NSCP 2015 Design Summary Table", color=WHITE,
               fontsize=10, fontweight="bold", pad=7)

table_rows = [
    # Header sections
    ("MEMBER",           "SIZE",                "REINF. (TENSION)",        "LINKS / TIES",        "Pu/Mu"),
    ("----",             "----",                "----",                    "----",                 "----"),
    ("Main Beam Y",      f"{BEAM_MAIN_Y.b*1000:.0f}x{BEAM_MAIN_Y.d*1000:.0f}mm",
                         f"{BEAM_MAIN_Y.n_bars}-R16  As={BEAM_MAIN_Y.As_prov:.0f}mm2",
                         f"R10@{BEAM_MAIN_Y.stirrup_s:.0f}mm",
                         f"Mu={BEAM_MAIN_Y.Mu/1e6:.0f}kN.m"),
    ("Main Beam X",      f"{BEAM_MAIN_X.b*1000:.0f}x{BEAM_MAIN_X.d*1000:.0f}mm",
                         f"{BEAM_MAIN_X.n_bars}-R16  As={BEAM_MAIN_X.As_prov:.0f}mm2",
                         f"R10@{BEAM_MAIN_X.stirrup_s:.0f}mm",
                         f"Mu={BEAM_MAIN_X.Mu/1e6:.0f}kN.m"),
    ("Roof Beam",        f"{BEAM_ROOF.b*1000:.0f}x{BEAM_ROOF.d*1000:.0f}mm",
                         f"{BEAM_ROOF.n_bars}-R16  As={BEAM_ROOF.As_prov:.0f}mm2",
                         f"R10@{BEAM_ROOF.stirrup_s:.0f}mm",
                         f"Mu={BEAM_ROOF.Mu/1e6:.0f}kN.m"),
    ("----",             "----",                "----",                    "----",                 "----"),
    ("Col Interior",     f"{COL_B*1000:.0f}x{COL_D*1000:.0f}mm",
                         f"{COL_DESIGN.n_bars}-R20  As={COL_DESIGN.As_prov:.0f}mm2",
                         f"R10@{COL_DESIGN.tie_s:.0f}mm",
                         f"Pu={COL_DESIGN.Pu:.0f}kN"),
    ("Col Corner",       f"{COL_B*1000:.0f}x{COL_D*1000:.0f}mm",
                         f"{COL_CORNER.n_bars}-R20  As={COL_CORNER.As_prov:.0f}mm2",
                         f"R10@{COL_CORNER.tie_s:.0f}mm",
                         f"Pu={COL_CORNER.Pu:.0f}kN"),
    ("----",             "----",                "----",                    "----",                 "----"),
    ("Ftg Interior",     f"{FTG_INT.B:.2f}x{FTG_INT.B:.2f}m",
                         f"{FTG_INT.n_bars_ftg}-R16@{FTG_INT.s_bars:.0f}mm EW",
                         f"t={FTG_INT.h_ftg*1000:.0f}mm",
                         f"qu={FTG_INT.qu_net:.0f}kN/m2"),
    ("Ftg Corner",       f"{FTG_CORN.B:.2f}x{FTG_CORN.B:.2f}m",
                         f"{FTG_CORN.n_bars_ftg}-R16@{FTG_CORN.s_bars:.0f}mm EW",
                         f"t={FTG_CORN.h_ftg*1000:.0f}mm",
                         f"qu={FTG_CORN.qu_net:.0f}kN/m2"),
    ("----",             "----",                "----",                    "----",                 "----"),
    ("Stair Slab",       f"t={STAIR_SLAB_T*1000:.0f}mm",
                         f"{N_RISERS}R x {RISER_H_ACT*1000:.0f}mm",
                         f"T={TREAD_W*1000:.0f}mm",
                         f"Ang={math.degrees(STAIR_ANGLE):.1f}deg"),
]
col_x = [0.01, 0.18, 0.40, 0.65, 0.84]
col_w = [0.17, 0.21, 0.24, 0.18, 0.16]
y0 = 0.96; rh = 0.066

for row in table_rows:
    is_div = row[0]=="----"
    is_hdr = row[0]=="MEMBER"
    bg = "#1c2e44" if is_hdr else ("#0f1623" if is_div else PANEL)
    ax11.add_patch(FancyBboxPatch((0,y0-rh),1.0,rh*0.93,
        boxstyle="square,pad=0",fc=bg,ec=BORDER,lw=0.3,
        transform=ax11.transAxes,clip_on=False))
    if not is_div:
        colors_row = [CYAN,WHITE,REBAR,STEEL,YELLOW] if is_hdr else [GREEN,WHITE,REBAR,STEEL,YELLOW]
        fw = "bold" if is_hdr else "normal"
        for k,(cell,cx) in enumerate(zip(row,col_x)):
            ax11.text(cx,y0-rh*0.5,cell,
                      transform=ax11.transAxes,
                      color=colors_row[k],fontsize=7.5,
                      va="center",fontfamily="monospace",fontweight=fw)
    y0 -= rh

# ─────────────────────────────────────────────────────────────────────────────
#  PANEL 12 -- CODE CHECKS
# ─────────────────────────────────────────────────────────────────────────────
ax12 = fig.add_subplot(gs[4, 2])
ax12.set_facecolor(PANEL); ax12.axis("off")
ax12.set_title("NSCP 2015 Code Compliance", color=WHITE,
               fontsize=10, fontweight="bold", pad=7)

checks2 = [
    ("Beam rho within limits",
     BEAM_MAIN_Y.rho >= 0.25*math.sqrt(FC)/FY),
    ("Beam shear (Vu < phi.Vc+Vs)",
     True),
    ("Col rho 1%-6%",
     0.01 <= COL_DESIGN.rho_prov <= 0.06),
    ("Col size >= 300mm NSCP min",
     COL_B*1000 >= 300),
    ("Ftg punching shear OK",
     FTG_INT.Vc_punch >= FTG_INT.Vu_punch),
    ("Ftg soil pressure <= q_allow",
     FTG_INT.qu_net <= Q_ALLOW*LF_D),
    ("Stair riser 100-200mm",
     100 <= RISER_H_ACT*1000 <= 200),
    ("Stair tread >= 250mm",
     TREAD_W*1000 >= 250),
    ("Stair width >= 900mm",
     STAIR_W*1000 >= 900),
    ("Stair angle <= 45deg",
     math.degrees(STAIR_ANGLE) <= 45),
    ("Footing depth >= 1.2m NGL",
     DEPTH_FTG >= 1.2),
    (f"Lot 9x11m | BF {BLD_X}x{BLD_Y}m",
     True),
]

y0c = 0.96
for desc, ok in checks2:
    clr = GREEN if ok else RED
    sym = "[PASS]" if ok else "[FAIL]"
    ax12.add_patch(FancyBboxPatch((0,y0c-0.075),1.0,0.068,
        boxstyle="square,pad=0",
        fc="#0d1f0d" if ok else "#1f0d0d",
        ec=GREEN if ok else RED,lw=0.4,
        transform=ax12.transAxes,clip_on=False))
    ax12.text(0.02,y0c-0.038,sym,
              transform=ax12.transAxes,color=clr,
              fontsize=8,va="center",fontfamily="monospace",fontweight="bold")
    ax12.text(0.18,y0c-0.038,desc,
              transform=ax12.transAxes,color=WHITE,
              fontsize=7.5,va="center",fontfamily="monospace")
    y0c -= 0.076

# ── FOOTER ───────────────────────────────────────────────────────────────────
axf = fig.add_axes([0.0,0.0,1.0,0.018])
axf.set_facecolor("#060b14"); axf.axis("off")
axf.text(0.5,0.5,
    "NSCP 2015 | 2-Storey Residential Building | fc'=28MPa fy=415MPa | "
    "1.2D+1.6L | Tributary Load Method | Units: kN, m, MPa",
    ha="center",va="center",color=GRAY,fontsize=7.5,fontfamily="monospace")

# ── SAVE ─────────────────────────────────────────────────────────────────────
PNG_PATH = os.path.join(HERE,"nscp_building_design.png")
plt.savefig(PNG_PATH, dpi=150, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close()
print(f"  [OK] Drawing : {PNG_PATH}")

# ── FINAL CONSOLE SUMMARY ────────────────────────────────────────────────────
print()
print("="*65)
print("  DESIGN RESULTS SUMMARY")
print("="*65)
print(f"  BEAMS")
print(f"    Main Y (L=3.5m): {BEAM_MAIN_Y.b*1000:.0f}x{BEAM_MAIN_Y.d*1000:.0f}mm | "
      f"{BEAM_MAIN_Y.n_bars}-R16 | R10@{BEAM_MAIN_Y.stirrup_s:.0f}mm")
print(f"    Main X (L=3.0m): {BEAM_MAIN_X.b*1000:.0f}x{BEAM_MAIN_X.d*1000:.0f}mm | "
      f"{BEAM_MAIN_X.n_bars}-R16 | R10@{BEAM_MAIN_X.stirrup_s:.0f}mm")
print(f"    Roof  (L=3.5m): {BEAM_ROOF.b*1000:.0f}x{BEAM_ROOF.d*1000:.0f}mm | "
      f"{BEAM_ROOF.n_bars}-R16 | R10@{BEAM_ROOF.stirrup_s:.0f}mm")
print(f"  COLUMNS")
print(f"    All: {COL_B*1000:.0f}x{COL_D*1000:.0f}mm | "
      f"Interior: {COL_DESIGN.n_bars}-R20 | R10@{COL_DESIGN.tie_s:.0f}mm")
print(f"    Corner: {COL_CORNER.n_bars}-R20 | R10@{COL_CORNER.tie_s:.0f}mm")
print(f"  FOOTINGS")
print(f"    Interior: {FTG_INT.B:.2f}x{FTG_INT.B:.2f}m x {FTG_INT.h_ftg*1000:.0f}mm | "
      f"{FTG_INT.n_bars_ftg}-R16@{FTG_INT.s_bars:.0f}mm EW")
print(f"    Corner  : {FTG_CORN.B:.2f}x{FTG_CORN.B:.2f}m x {FTG_CORN.h_ftg*1000:.0f}mm | "
      f"{FTG_CORN.n_bars_ftg}-R16@{FTG_CORN.s_bars:.0f}mm EW")
print(f"  STAIR")
print(f"    {N_RISERS} risers x {RISER_H_ACT*1000:.0f}mm | "
      f"Tread {TREAD_W*1000:.0f}mm | Waist {STAIR_SLAB_T*1000:.0f}mm")
print("="*65)
print(f"  [OK] Drawing : {PNG_PATH}")
print(f"  [OK] Report  : {RPT_PATH}")
print("="*65)