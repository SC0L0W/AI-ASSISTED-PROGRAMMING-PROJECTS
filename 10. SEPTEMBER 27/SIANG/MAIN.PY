import tkinter as tk
from tkinter import ttk, messagebox
import math

class ConcreteEstimatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Concrete Construction Estimator")
        self.root.geometry("850x700")
        self.root.resizable(True, True)

        # Style configurations
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TFrame", background="#f4f5f7")
        self.style.configure("TLabel", background="#f4f5f7", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#1a202c")
        self.style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), foreground="#2b6cb0")
        self.style.configure("TButton", font=("Segoe UI", 10, "bold"), background="#3182ce", foreground="white")
        self.style.map("TButton", background=[("active", "#2b6cb0")])

        self.create_widgets()

    def create_widgets(self):
        # Title Banner
        title_frame = ttk.Frame(self.root, padding=10)
        title_frame.pack(fill=tk.X)
        ttk.Label(title_frame, text="Concrete Construction Estimator", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(title_frame, text="Calculate volume, concrete mix materials, rebar, and cost estimates.", font=("Segoe UI", 9, "italic")).pack(anchor=tk.W)

        # Main Layout: Two Notebook/Tabs area or side-by-side
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        # Left Column: Inputs
        left_frame = ttk.Frame(main_container, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Right Column: Results & Summary
        right_frame = ttk.Frame(main_container, padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # --- 1. Element Type & Dimensions ---
        dim_group = ttk.LabelFrame(left_frame, text=" 1. Element & Dimensions ", padding=10)
        dim_group.pack(fill=tk.X, pady=5)

        ttk.Label(dim_group, text="Structure Type:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.struct_type = ttk.Combobox(dim_group, values=["Slab / Pavement", "Rectangular Column / Beam", "Round Column", "Footing Pad"], state="readonly")
        self.struct_type.current(0)
        self.struct_type.grid(row=0, column=1, sticky=tk.EW, pady=2)
        self.struct_type.bind("<<ComboboxSelected>>", self.toggle_dimension_inputs)

        ttk.Label(dim_group, text="Quantity (Pcs/Slabs):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.qty_entry = ttk.Entry(dim_group)
        self.qty_entry.insert(0, "1")
        self.qty_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)

        # Dynamic Dimension Fields
        self.lbl_dim1 = ttk.Label(dim_group, text="Length (m):")
        self.lbl_dim1.grid(row=2, column=0, sticky=tk.W, pady=2)
        self.ent_dim1 = ttk.Entry(dim_group)
        self.ent_dim1.insert(0, "5.0")
        self.ent_dim1.grid(row=2, column=1, sticky=tk.EW, pady=2)

        self.lbl_dim2 = ttk.Label(dim_group, text="Width (m):")
        self.lbl_dim2.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.ent_dim2 = ttk.Entry(dim_group)
        self.ent_dim2.insert(0, "4.0")
        self.ent_dim2.grid(row=3, column=1, sticky=tk.EW, pady=2)

        self.lbl_dim3 = ttk.Label(dim_group, text="Thickness / Height (m):")
        self.lbl_dim3.grid(row=4, column=0, sticky=tk.W, pady=2)
        self.ent_dim3 = ttk.Entry(dim_group)
        self.ent_dim3.insert(0, "0.15")
        self.ent_dim3.grid(row=4, column=1, sticky=tk.EW, pady=2)

        # --- 2. Concrete Mix Parameters ---
        mix_group = ttk.LabelFrame(left_frame, text=" 2. Concrete Mix Specification ", padding=10)
        mix_group.pack(fill=tk.X, pady=5)

        ttk.Label(mix_group, text="Mix Ratio / Class:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.mix_ratio = ttk.Combobox(mix_group, values=[
            "Class A (1:2:4) - 3000 PSI",
            "Class B (1:2.5:5) - 2500 PSI",
            "Class C (1:3:6) - 2000 PSI",
            "Class AA (1:1.5:3) - 4000 PSI"
        ], state="readonly")
        self.mix_ratio.current(0)
        self.mix_ratio.grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(mix_group, text="Cement Bag Size:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.bag_size = ttk.Combobox(mix_group, values=["40 kg", "50 kg"], state="readonly")
        self.bag_size.current(0)
        self.bag_size.grid(row=1, column=1, sticky=tk.EW, pady=2)

        ttk.Label(mix_group, text="Wastage Margin (%):").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.wastage_entry = ttk.Entry(mix_group)
        self.wastage_entry.insert(0, "5")
        self.wastage_entry.grid(row=2, column=1, sticky=tk.EW, pady=2)

        # --- 3. Material Unit Costs ---
        cost_group = ttk.LabelFrame(left_frame, text=" 3. Material Costs ($ / Local Currency) ", padding=10)
        cost_group.pack(fill=tk.X, pady=5)

        ttk.Label(cost_group, text="Cement Cost / Bag:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.cost_cement = ttk.Entry(cost_group)
        self.cost_cement.insert(0, "9.50")
        self.cost_cement.grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(cost_group, text="Sand Cost / cu.m:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.cost_sand = ttk.Entry(cost_group)
        self.cost_sand.insert(0, "25.00")
        self.cost_sand.grid(row=1, column=1, sticky=tk.EW, pady=2)

        ttk.Label(cost_group, text="Gravel Cost / cu.m:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.cost_gravel = ttk.Entry(cost_group)
        self.cost_gravel.insert(0, "30.00")
        self.cost_gravel.grid(row=2, column=1, sticky=tk.EW, pady=2)

        # Calculate Button
        btn_calc = ttk.Button(left_frame, text="CALCULATE ESTIMATE", command=self.calculate_estimate)
        btn_calc.pack(fill=tk.X, pady=10)

        # --- Output Display ---
        out_group = ttk.LabelFrame(right_frame, text=" Estimation Summary ", padding=10)
        out_group.pack(fill=tk.BOTH, expand=True)

        self.txt_results = tk.Text(out_group, font=("Consolas", 10), wrap=tk.WORD, bg="#ffffff", fg="#2d3748", relief=tk.FLAT)
        self.txt_results.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        scrollbar = ttk.Scrollbar(out_group, command=self.txt_results.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_results.config(yscrollcommand=scrollbar.set)

    def toggle_dimension_inputs(self, event=None):
        selected = self.struct_type.get()
        if selected == "Round Column":
            self.lbl_dim1.config(text="Diameter (m):")
            self.lbl_dim2.grid_remove()
            self.ent_dim2.grid_remove()
            self.lbl_dim3.config(text="Height (m):")
        else:
            self.lbl_dim1.config(text="Length (m):")
            self.lbl_dim2.grid()
            self.ent_dim2.grid()
            self.lbl_dim2.config(text="Width (m):")
            self.lbl_dim3.config(text="Thickness / Depth (m):")

    def calculate_estimate(self):
        try:
            qty = float(self.qty_entry.get())
            dim1 = float(self.ent_dim1.get())
            dim3 = float(self.ent_dim3.get())
            wastage_pct = float(self.wastage_entry.get()) / 100.0

            cost_cem = float(self.cost_cement.get())
            cost_snd = float(self.cost_sand.get())
            cost_grv = float(self.cost_gravel.get())

            stype = self.struct_type.get()
            
            # 1. Calculate Net Volume
            if stype == "Round Column":
                radius = dim1 / 2.0
                unit_vol = math.pi * (radius ** 2) * dim3
            else:
                dim2 = float(self.ent_dim2.get())
                unit_vol = dim1 * dim2 * dim3

            net_volume = unit_vol * qty
            total_volume = net_volume * (1 + wastage_pct)

            # 2. Material Multipliers per cu.m of concrete based on mix (Standard Volumetric Method)
            # Class A (1:2:4), Class B (1:2.5:5), Class C (1:3:6), Class AA (1:1.5:3)
            mix_selected = self.mix_ratio.get()
            is_40kg = "40 kg" in self.bag_size.get()

            if "Class AA" in mix_selected:
                bags_per_m3 = 12.0 if is_40kg else 9.5
                sand_m3 = 0.50
                gravel_m3 = 1.00
            elif "Class A" in mix_selected:
                bags_per_m3 = 9.0 if is_40kg else 7.2
                sand_m3 = 0.50
                gravel_m3 = 1.00
            elif "Class B" in mix_selected:
                bags_per_m3 = 7.5 if is_40kg else 6.0
                sand_m3 = 0.50
                gravel_m3 = 1.00
            else: # Class C
                bags_per_m3 = 6.0 if is_40kg else 5.0
                sand_m3 = 0.50
                gravel_m3 = 1.00

            # 3. Quantities Required
            total_cement_bags = math.ceil(total_volume * bags_per_m3)
            total_sand = round(total_volume * sand_m3, 2)
            total_gravel = round(total_volume * gravel_m3, 2)

            # 4. Costs
            cement_total_cost = total_cement_bags * cost_cem
            sand_total_cost = total_sand * cost_snd
            gravel_total_cost = total_gravel * cost_grv
            grand_total_cost = cement_total_cost + sand_total_cost + gravel_total_cost

            # 5. Output Display Formatting
            res = "===========================================\n"
            res += "       CONCRETE ESTIMATE REPORT           \n"
            res += "===========================================\n\n"
            res += f"Element Type:      {stype}\n"
            res += f"Quantity:          {int(qty)} unit(s)\n"
            res += f"Net Volume:        {net_volume:.3f} m³\n"
            res += f"Wastage Factor:    {wastage_pct * 100:.1f}%\n"
            res += f"Total Volume Req:  {total_volume:.3f} m³\n\n"
            
            res += "-------------------------------------------\n"
            res += " MATERIAL BREAKDOWN                        \n"
            res += "-------------------------------------------\n"
            res += f"Mix Specification: {mix_selected}\n"
            res += f"Bag Weight:        {self.bag_size.get()}\n\n"
            
            res += f"• Cement:  {total_cement_bags:>6} Bags  @ ${cost_cem:.2f}/bag = ${cement_total_cost:.2f}\n"
            res += f"• Sand:    {total_sand:>6.2f} m³    @ ${cost_snd:.2f}/m³  = ${sand_total_cost:.2f}\n"
            res += f"• Gravel:  {total_gravel:>6.2f} m³    @ ${cost_grv:.2f}/m³  = ${gravel_total_cost:.2f}\n\n"

            res += "-------------------------------------------\n"
            res += f" TOTAL ESTIMATED MATERIAL COST: ${grand_total_cost:,.2f}\n"
            res += "-------------------------------------------\n"

            self.txt_results.delete(1.0, tk.END)
            self.txt_results.insert(tk.END, res)

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numerical values for all dimension and cost fields.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ConcreteEstimatorApp(root)
    root.mainloop()