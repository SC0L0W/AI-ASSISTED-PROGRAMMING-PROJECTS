import tkinter as tk
from tkinter import messagebox
from openstaadpy import os_analytical
import math

# ===============================
# MAIN GENERATOR FUNCTION
# ===============================

def generate_warehouse():

    try:
        span = float(entry_span.get())
        eave_height = float(entry_eave.get())
        roof_pitch = float(entry_pitch.get())
        bay_spacing = float(entry_spacing.get())
        num_bays = int(entry_bays.get())
        col_section = entry_col.get()
        raf_section = entry_raf.get()

        staad = os_analytical.connect()
        geo = staad.Geometry
        prop = staad.Property
        sup = staad.Support
        load = staad.Load

        staad.SetInputUnits(1,0)  # FEET-KIP

        node_id = 1
        member_id = 1
        frames = []

        # -------------------------
        # NODE GENERATION
        # -------------------------
        for bay in range(num_bays + 1):

            z = bay * bay_spacing

            lb = node_id; geo.CreateNode(node_id, 0, 0, z); node_id+=1
            rb = node_id; geo.CreateNode(node_id, span, 0, z); node_id+=1
            le = node_id; geo.CreateNode(node_id, 0, eave_height, z); node_id+=1
            re = node_id; geo.CreateNode(node_id, span, eave_height, z); node_id+=1
            ridge = node_id; geo.CreateNode(node_id, span/2, eave_height + roof_pitch, z); node_id+=1

            frames.append((lb, rb, le, re, ridge))

        # -------------------------
        # MEMBER GENERATION
        # -------------------------
        for frame in frames:

            lb, rb, le, re, ridge = frame

            geo.CreateBeam(member_id, lb, le); member_id+=1
            geo.CreateBeam(member_id, rb, re); member_id+=1
            geo.CreateBeam(member_id, le, ridge); member_id+=1
            geo.CreateBeam(member_id, ridge, re); member_id+=1

        # Longitudinal beams
        for i in range(len(frames)-1):

            curr = frames[i]
            nextf = frames[i+1]

            geo.CreateBeam(member_id, curr[2], nextf[2]); member_id+=1
            geo.CreateBeam(member_id, curr[3], nextf[3]); member_id+=1
            geo.CreateBeam(member_id, curr[4], nextf[4]); member_id+=1

        total_members = member_id - 1

        # -------------------------
        # PROPERTIES
        # -------------------------
        cc = 1  # American table

        col_prop = prop.CreateBeamPropertyFromTable(cc,col_section,0,0,0)
        raf_prop = prop.CreateBeamPropertyFromTable(cc,raf_section,0,0,0)

        col_count = 2*(num_bays+1)

        prop.AssignBeamProperty(list(range(1,col_count+1)), col_prop)
        prop.AssignBeamProperty(list(range(col_count+1,total_members+1)), raf_prop)
        prop.AssignMaterialToMember("STEEL", list(range(1,total_members+1)))

        # -------------------------
        # SUPPORTS
        # -------------------------
        fixed_id = sup.CreateSupportFixed()

        for frame in frames:
            sup.AssignSupportToNode([frame[0]], fixed_id)
            sup.AssignSupportToNode([frame[1]], fixed_id)

        # -------------------------
        # LOAD
        # -------------------------
        case1 = load.CreateNewPrimaryLoadEx2("DEAD LOAD",0,1)
        load.SetLoadActive(case1)
        load.AddSelfWeightInXYZ(2,-1.0)

        staad.SaveModel(True)
        staad.Command.PerformAnalysis(0)

        messagebox.showinfo("Success", "Warehouse Model Generated Successfully!")

    except Exception as e:
        messagebox.showerror("Error", str(e))


# ===============================
# GUI
# ===============================

root = tk.Tk()
root.title("Parametric Warehouse Generator - STAAD")

tk.Label(root, text="Span (ft)").grid(row=0, column=0)
entry_span = tk.Entry(root); entry_span.insert(0,"60")
entry_span.grid(row=0,column=1)

tk.Label(root, text="Eave Height (ft)").grid(row=1, column=0)
entry_eave = tk.Entry(root); entry_eave.insert(0,"20")
entry_eave.grid(row=1,column=1)

tk.Label(root, text="Roof Rise (ft)").grid(row=2, column=0)
entry_pitch = tk.Entry(root); entry_pitch.insert(0,"5")
entry_pitch.grid(row=2,column=1)

tk.Label(root, text="Bay Spacing (ft)").grid(row=3, column=0)
entry_spacing = tk.Entry(root); entry_spacing.insert(0,"20")
entry_spacing.grid(row=3,column=1)

tk.Label(root, text="Number of Bays").grid(row=4, column=0)
entry_bays = tk.Entry(root); entry_bays.insert(0,"4")
entry_bays.grid(row=4,column=1)

tk.Label(root, text="Column Section (e.g. W14X90)").grid(row=5, column=0)
entry_col = tk.Entry(root); entry_col.insert(0,"W14X90")
entry_col.grid(row=5,column=1)

tk.Label(root, text="Rafter Section (e.g. W18X35)").grid(row=6, column=0)
entry_raf = tk.Entry(root); entry_raf.insert(0,"W18X35")
entry_raf.grid(row=6,column=1)

tk.Button(root, text="Generate Warehouse", command=generate_warehouse, bg="lightblue").grid(row=7,column=0,columnspan=2,pady=10)

root.mainloop()