"""
AISC Shear Connection (Single-Plate / Shear Tab) Designer
Based on AISC 360-16, Chapter J and AISC Steel Construction Manual Part 10.

Run:  python shear_connection_designer.py
Requires only the Python standard library (tkinter).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math

# ---------------------------------------------------------------------------
# Bolt shear strength table (Fnv, ksi) - AISC Table J3.2 (bearing-type, LRFD)
# ---------------------------------------------------------------------------
BOLT_FNV = {
    "A325-N (threads included)": 54.0,
    "A325-X (threads excluded)": 68.0,
    "A490-N (threads included)": 68.0,
    "A490-X (threads excluded)": 84.0,
}

PHI_BOLT_SHEAR = 0.75
PHI_BEARING = 0.75
PHI_SHEAR_YIELD = 1.00
PHI_SHEAR_RUPTURE = 0.75
PHI_BLOCK_SHEAR = 0.75
PHI_WELD = 0.75


def bolt_hole_dia(db):
    """Standard hole diameter per AISC Table J3.3 (approx, for db <= 1 in)."""
    return db + 1.0 / 16.0 + 1.0 / 16.0  # nominal std hole clearance ~1/8" over db (simplified)


class ShearTabResults:
    def __init__(self):
        self.rows = []  # (label, capacity_kips, demand_kips, ratio, status)

    def add(self, label, capacity, demand):
        ratio = demand / capacity if capacity > 0 else float("inf")
        status = "OK" if ratio <= 1.0 else "NG"
        self.rows.append((label, capacity, demand, ratio, status))


def design_shear_tab(inputs):
    """
    inputs: dict with keys
        Vu (kips), n, db (in), bolt_grade (str), s (in), Lev (in), Leh (in),
        tp (in), L (in), Fy (ksi), Fu (ksi), weld_size (in), FEXX (ksi),
        weld_len (in), e (in, eccentricity), tw_beam (in), Fu_beam (ksi)
    """
    Vu = inputs["Vu"]
    n = inputs["n"]
    db = inputs["db"]
    Fnv = BOLT_FNV[inputs["bolt_grade"]]
    s = inputs["s"]
    Lev = inputs["Lev"]
    Leh = inputs["Leh"]
    tp = inputs["tp"]
    L = inputs["L"]
    Fy = inputs["Fy"]
    Fu = inputs["Fu"]
    weld_size = inputs["weld_size"]
    FEXX = inputs["FEXX"]
    weld_len = inputs["weld_len"]
    e = inputs["e"]
    tw_beam = inputs["tw_beam"]
    Fu_beam = inputs["Fu_beam"]

    res = ShearTabResults()
    dh = bolt_hole_dia(db)
    Ab = math.pi / 4.0 * db ** 2

    # --- 1. Bolt shear (group, single shear plane) ---
    Rn_bolt = Fnv * Ab * n
    phiRn_bolt = PHI_BOLT_SHEAR * Rn_bolt
    res.add("Bolt shear (group)", phiRn_bolt, Vu)

    # --- 2. Bolt bearing / tearout - plate, edge bolt (governs at edge) ---
    Lc_edge = Lev - dh / 2.0
    Rn_edge_plate = min(1.2 * Lc_edge * tp * Fu, 2.4 * db * tp * Fu)
    # interior bolts (spacing controlled)
    Lc_int = s - dh
    Rn_int_plate = min(1.2 * Lc_int * tp * Fu, 2.4 * db * tp * Fu)
    Rn_bearing_plate = Rn_edge_plate + (n - 1) * Rn_int_plate if n > 1 else Rn_edge_plate
    phiRn_bearing_plate = PHI_BEARING * Rn_bearing_plate
    res.add("Bolt bearing/tearout - plate", phiRn_bearing_plate, Vu)

    # --- 3. Bolt bearing / tearout - beam web ---
    Rn_edge_web = min(1.2 * Lc_edge * tw_beam * Fu_beam, 2.4 * db * tw_beam * Fu_beam)
    Rn_int_web = min(1.2 * Lc_int * tw_beam * Fu_beam, 2.4 * db * tw_beam * Fu_beam)
    Rn_bearing_web = Rn_edge_web + (n - 1) * Rn_int_web if n > 1 else Rn_edge_web
    phiRn_bearing_web = PHI_BEARING * Rn_bearing_web
    res.add("Bolt bearing/tearout - beam web", phiRn_bearing_web, Vu)

    # --- 4. Plate shear yield (gross section) ---
    Ag = L * tp
    Rn_yield = 0.60 * Fy * Ag
    phiRn_yield = PHI_SHEAR_YIELD * Rn_yield
    res.add("Plate shear yield (gross)", phiRn_yield, Vu)

    # --- 5. Plate shear rupture (net section) ---
    Anv = (L - n * dh) * tp
    Rn_rupture = 0.60 * Fu * Anv
    phiRn_rupture = PHI_SHEAR_RUPTURE * Rn_rupture
    res.add("Plate shear rupture (net)", phiRn_rupture, Vu)

    # --- 6. Block shear rupture - plate ---
    # Simplified typical path: Agv = (L - Lev) * tp ; Ant = (Leh - dh/2) * tp
    Agv_p = (L - Lev) * tp
    Anv_p = (L - Lev - (n - 0.5) * dh) * tp if n > 1 else (L - Lev - 0.5 * dh) * tp
    Ant_p = (Leh - dh / 2.0) * tp
    Ubs = 1.0
    Rn_bs_p = min(0.60 * Fu * Anv_p + Ubs * Fu * Ant_p, 0.60 * Fy * Agv_p + Ubs * Fu * Ant_p)
    phiRn_bs_p = PHI_BLOCK_SHEAR * Rn_bs_p
    res.add("Block shear rupture - plate", phiRn_bs_p, Vu)

    # --- 7. Weld strength (fillet weld, both sides of plate to support) ---
    Rn_weld_per_in = 0.60 * FEXX * (0.707 * weld_size)
    Rn_weld = 2 * Rn_weld_per_in * weld_len  # two weld lines
    phiRn_weld = PHI_WELD * Rn_weld
    res.add("Weld strength (fillet, 2 sides)", phiRn_weld, Vu)

    # --- 8. Eccentric bolt group demand (elastic vector method, simplified) ---
    Mu = Vu * e
    if n > 1:
        y_vals = [(i - (n - 1) / 2.0) * s for i in range(n)]
        Ip = sum(y ** 2 for y in y_vals)
        r_max = max(abs(y) for y in y_vals)
        f_v_direct = Vu / n
        f_v_moment = (Mu * r_max) / Ip if Ip > 0 else 0
        f_resultant = math.sqrt(f_v_direct ** 2 + f_v_moment ** 2)
        bolt_cap = PHI_BOLT_SHEAR * Fnv * Ab
        res.add("Eccentric bolt (max resultant force vs 1 bolt shear cap.)", bolt_cap, f_resultant)
    else:
        res.rows.append(("Eccentric bolt group check", 0, 0, 0, "N/A (single bolt)"))

    return res


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AISC Shear Tab Connection Designer")
        self.geometry("760x720")
        self.resizable(False, False)
        self.configure(bg="#f4f4f6")

        self._build_input_frame()
        self._build_output_frame()

    def _labeled_entry(self, parent, label, default, row, col=0):
        tk.Label(parent, text=label, bg="#f4f4f6", anchor="w", width=28)\
            .grid(row=row, column=col, sticky="w", padx=6, pady=3)
        var = tk.StringVar(value=str(default))
        entry = tk.Entry(parent, textvariable=var, width=12)
        entry.grid(row=row, column=col + 1, sticky="w", padx=6, pady=3)
        return var

    def _build_input_frame(self):
        frame = tk.LabelFrame(self, text="Inputs", bg="#f4f4f6", padx=10, pady=10)
        frame.pack(fill="x", padx=12, pady=10)

        self.v_Vu = self._labeled_entry(frame, "Required shear, Vu (kips)", 40.0, 0)
        self.v_n = self._labeled_entry(frame, "Number of bolts, n", 3, 1)
        self.v_db = self._labeled_entry(frame, "Bolt diameter, db (in)", 0.75, 2)

        self.v_grade = tk.StringVar(value=list(BOLT_FNV.keys())[1])
        tk.Label(frame, text="Bolt grade / thread condition", bg="#f4f4f6", width=28, anchor="w")\
            .grid(row=3, column=0, sticky="w", padx=6, pady=3)
        ttk.Combobox(frame, textvariable=self.v_grade, values=list(BOLT_FNV.keys()),
                     width=26, state="readonly").grid(row=3, column=1, columnspan=2, sticky="w", padx=6)

        self.v_s = self._labeled_entry(frame, "Bolt spacing, s (in)", 3.0, 4)
        self.v_Lev = self._labeled_entry(frame, "Vertical edge distance, Lev (in)", 1.5, 5)
        self.v_Leh = self._labeled_entry(frame, "Horizontal edge distance, Leh (in)", 1.5, 6)
        self.v_tp = self._labeled_entry(frame, "Plate thickness, tp (in)", 0.375, 7)
        self.v_L = self._labeled_entry(frame, "Plate depth, L (in)", 9.0, 8)
        self.v_Fy = self._labeled_entry(frame, "Plate Fy (ksi)", 36.0, 9)
        self.v_Fu = self._labeled_entry(frame, "Plate Fu (ksi)", 58.0, 10)

        self.v_weld = self._labeled_entry(frame, "Weld size, w (in)", 0.25, 0, col=3)
        self.v_FEXX = self._labeled_entry(frame, "Weld electrode, FEXX (ksi)", 70.0, 1, col=3)
        self.v_weldlen = self._labeled_entry(frame, "Weld length per side (in)", 9.0, 2, col=3)
        self.v_e = self._labeled_entry(frame, "Eccentricity, e (in)", 3.0, 3, col=3)
        self.v_tw = self._labeled_entry(frame, "Beam web thickness, tw (in)", 0.30, 4, col=3)
        self.v_Fu_beam = self._labeled_entry(frame, "Beam web Fu (ksi)", 65.0, 5, col=3)

        btn = tk.Button(self, text="Calculate", command=self.on_calculate,
                         bg="#2b6cb0", fg="white", font=("Segoe UI", 11, "bold"),
                         padx=14, pady=6)
        btn.pack(pady=8)

    def _build_output_frame(self):
        frame = tk.LabelFrame(self, text="Results (LRFD)", bg="#f4f4f6", padx=10, pady=10)
        frame.pack(fill="both", expand=True, padx=12, pady=6)

        columns = ("limit_state", "phiRn", "demand", "ratio", "status")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=10)
        headers = {
            "limit_state": "Limit State",
            "phiRn": "\u03c6Rn (kips)",
            "demand": "Vu (kips)",
            "ratio": "Demand/Capacity",
            "status": "Status",
        }
        widths = {"limit_state": 300, "phiRn": 100, "demand": 90, "ratio": 120, "status": 70}
        for c in columns:
            self.tree.heading(c, text=headers[c])
            self.tree.column(c, width=widths[c], anchor="center" if c != "limit_state" else "w")
        self.tree.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Treeview", rowheight=26)

        self.summary_var = tk.StringVar(value="Enter inputs and click Calculate.")
        tk.Label(self, textvariable=self.summary_var, bg="#f4f4f6",
                 font=("Segoe UI", 10, "bold"), fg="#1a202c", wraplength=720, justify="left")\
            .pack(pady=8, padx=12, anchor="w")

    def on_calculate(self):
        try:
            inputs = {
                "Vu": float(self.v_Vu.get()),
                "n": int(self.v_n.get()),
                "db": float(self.v_db.get()),
                "bolt_grade": self.v_grade.get(),
                "s": float(self.v_s.get()),
                "Lev": float(self.v_Lev.get()),
                "Leh": float(self.v_Leh.get()),
                "tp": float(self.v_tp.get()),
                "L": float(self.v_L.get()),
                "Fy": float(self.v_Fy.get()),
                "Fu": float(self.v_Fu.get()),
                "weld_size": float(self.v_weld.get()),
                "FEXX": float(self.v_FEXX.get()),
                "weld_len": float(self.v_weldlen.get()),
                "e": float(self.v_e.get()),
                "tw_beam": float(self.v_tw.get()),
                "Fu_beam": float(self.v_Fu_beam.get()),
            }
        except ValueError:
            messagebox.showerror("Input error", "Please make sure all fields contain valid numbers.")
            return

        results = design_shear_tab(inputs)

        for row in self.tree.get_children():
            self.tree.delete(row)

        worst_ratio = 0.0
        worst_label = ""
        any_ng = False
        for label, cap, demand, ratio, status in results.rows:
            if status == "NG":
                any_ng = True
            display_ratio = f"{ratio:.2f}" if isinstance(ratio, float) and ratio != float("inf") else "-"
            self.tree.insert("", "end", values=(
                label,
                f"{cap:,.1f}" if cap else "-",
                f"{demand:,.1f}" if demand else "-",
                display_ratio,
                status,
            ), tags=(status,))
            if isinstance(ratio, float) and ratio > worst_ratio and ratio != float("inf"):
                worst_ratio = ratio
                worst_label = label

        self.tree.tag_configure("OK", background="#e6ffed")
        self.tree.tag_configure("NG", background="#ffe6e6")

        if any_ng:
            self.summary_var.set(
                f"⚠ Connection FAILS one or more limit states. Governing (highest utilization): "
                f"{worst_label} (D/C = {worst_ratio:.2f})."
            )
        else:
            self.summary_var.set(
                f"✓ Connection is adequate for all checked limit states. Governing (highest utilization): "
                f"{worst_label} (D/C = {worst_ratio:.2f})."
            )


if __name__ == "__main__":
    app = App()
    app.mainloop()

