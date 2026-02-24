import tkinter as tk
from tkinter import ttk, messagebox
from openstaadpy import os_analytical

# ============================
# MAIN GENERATOR FUNCTION
# ============================

def generate_model():

    try:
        # -------- Inputs --------
        floors = int(entry_floors.get())
        floor_height = float(entry_height.get())

        grid_x = int(entry_gridx.get())
        grid_y = int(entry_gridy.get())

        spacing_x = float(entry_spx.get())
        spacing_y = float(entry_spy.get())

        beam_section = combo_beam.get()
        col_section = combo_col.get()

        slab_load_psf = float(entry_slab.get())

        # -------- Connect STAAD --------
        staad = os_analytical.connect()
        geo = staad.Geometry
        prop = staad.Property
        sup = staad.Support
        load = staad.Load

        staad.SetInputUnits(1,0)  # FEET-KIP

        node_id = 1
        member_id = 1
        node_map = {}

        # -------- NODE GENERATION --------
        for floor in range(floors + 1):

            z = floor * floor_height

            for i in range(grid_x + 1):
                for j in range(grid_y + 1):

                    x = i * spacing_x
                    y = j * spacing_y

                    geo.CreateNode(node_id, x, y, z)
                    node_map[(i,j,floor)] = node_id
                    node_id += 1

        # -------- COLUMNS --------
        column_members = []

        for floor in range(floors):
            for i in range(grid_x + 1):
                for j in range(grid_y + 1):

                    n1 = node_map[(i,j,floor)]
                    n2 = node_map[(i,j,floor+1)]

                    geo.CreateBeam(member_id, n1, n2)
                    column_members.append(member_id)
                    member_id += 1

        # -------- BEAMS --------
        beam_members = []

        for floor in range(1, floors + 1):

            # X direction beams
            for j in range(grid_y + 1):
                for i in range(grid_x):

                    n1 = node_map[(i,j,floor)]
                    n2 = node_map[(i+1,j,floor)]

                    geo.CreateBeam(member_id, n1, n2)
                    beam_members.append(member_id)
                    member_id += 1

            # Y direction beams
            for i in range(grid_x + 1):
                for j in range(grid_y):

                    n1 = node_map[(i,j,floor)]
                    n2 = node_map[(i,j+1,floor)]

                    geo.CreateBeam(member_id, n1, n2)
                    beam_members.append(member_id)
                    member_id += 1

        total_members = member_id - 1

        # -------- PROPERTIES --------
        cc = 1
        col_prop = prop.CreateBeamPropertyFromTable(cc,col_section,0,0,0)
        beam_prop = prop.CreateBeamPropertyFromTable(cc,beam_section,0,0,0)

        prop.AssignBeamProperty(column_members, col_prop)
        prop.AssignBeamProperty(beam_members, beam_prop)
        prop.AssignMaterialToMember("STEEL", list(range(1,total_members+1)))

        # -------- SUPPORTS --------
        fixed_id = sup.CreateSupportFixed()

        for i in range(grid_x + 1):
            for j in range(grid_y + 1):
                base_node = node_map[(i,j,0)]
                sup.AssignSupportToNode([base_node], fixed_id)

        # -------- LOAD CASE --------
        case1 = load.CreateNewPrimaryLoadEx2("DEAD + LIVE LOAD",0,1)
        load.SetLoadActive(case1)

        load.AddSelfWeightInXYZ(2,-1.0)

        slab_load_ksf = slab_load_psf / 1000.0

        for floor in range(1, floors + 1):
            z1 = floor * floor_height - 0.1
            z2 = floor * floor_height + 0.1
            load.AddFloorLoad(2, -slab_load_ksf, z1, z2)

        staad.SaveModel(True)
        staad.Command.PerformAnalysis(0)

        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END,
            f"Model Generated Successfully!\n\n"
            f"Floors: {floors}\n"
            f"Grid: {grid_x} x {grid_y}\n"
            f"Total Members: {total_members}\n"
            f"Beam Section: {beam_section}\n"
            f"Column Section: {col_section}\n"
        )

        messagebox.showinfo("Success","Building Generated and Analyzed Successfully!")

    except Exception as e:
        messagebox.showerror("Error", str(e))


# ============================
# GUI DESIGN
# ============================

root = tk.Tk()
root.title("Professional Multistory Building Generator - STAAD")
root.geometry("650x600")

frame = ttk.Frame(root, padding=15)
frame.pack(fill="both", expand=True)

# Inputs
labels = [
    "Number of Floors",
    "Floor Height (ft)",
    "Grid X Bays",
    "Grid Y Bays",
    "Spacing X (ft)",
    "Spacing Y (ft)",
    "Slab Load (psf)"
]

entries = []

for i, text in enumerate(labels):
    ttk.Label(frame, text=text).grid(row=i, column=0, sticky="w", pady=4)
    entry = ttk.Entry(frame)
    entry.grid(row=i, column=1)
    entries.append(entry)

entry_floors, entry_height, entry_gridx, entry_gridy, entry_spx, entry_spy, entry_slab = entries

# Default values
entry_floors.insert(0,"5")
entry_height.insert(0,"12")
entry_gridx.insert(0,"4")
entry_gridy.insert(0,"3")
entry_spx.insert(0,"20")
entry_spy.insert(0,"25")
entry_slab.insert(0,"80")

# Section dropdowns
ttk.Label(frame,text="Beam Section").grid(row=7,column=0,sticky="w")
combo_beam = ttk.Combobox(frame, values=["W16X26","W18X35","W21X44","W24X55"])
combo_beam.grid(row=7,column=1)
combo_beam.set("W18X35")

ttk.Label(frame,text="Column Section").grid(row=8,column=0,sticky="w")
combo_col = ttk.Combobox(frame, values=["W12X65","W14X90","W14X120","W16X100"])
combo_col.grid(row=8,column=1)
combo_col.set("W14X90")

# Generate Button
ttk.Button(frame, text="Generate Building", command=generate_model).grid(row=9,column=0,columnspan=2,pady=15)

# Output box
ttk.Label(frame,text="Model Summary").grid(row=10,column=0,sticky="w")
output_text = tk.Text(frame, height=10)
output_text.grid(row=11,column=0,columnspan=2,sticky="nsew")

frame.columnconfigure(1, weight=1)

root.mainloop()