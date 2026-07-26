import tkinter as tk
from tkinter import messagebox

# -----------------------------
# Steel Tension Member Design
# Eurocode (Simplified)
# -----------------------------

def calculate():

    try:
        fy = float(entry_fy.get())
        width = float(entry_width.get())
        thickness = float(entry_thickness.get())
        load = float(entry_load.get())

        gamma_M0 = 1.0

        area = width * thickness

        resistance = area * fy / gamma_M0 / 1000.0

        utilization = load / resistance

        result = f"""
Steel Tension Member Design

Area               = {area:.1f} mm²
Resistance         = {resistance:.2f} kN
Applied Load       = {load:.2f} kN
Utilization Ratio  = {utilization:.3f}
"""

        if utilization <= 1.0:
            result += "\nSTATUS : PASS ✔"
        else:
            result += "\nSTATUS : FAIL ✖"

        messagebox.showinfo("Design Result", result)

    except:
        messagebox.showerror("Error", "Please enter valid numbers.")


# -----------------------------
# Main Window
# -----------------------------

root = tk.Tk()

root.title("Simple Steel Design")
root.geometry("380x300")
root.resizable(False, False)

# Optional icon (.ico file)
# root.iconbitmap("steel.ico")

title = tk.Label(
    root,
    text="Steel Tension Design\n(Eurocode Simplified)",
    font=("Arial", 14, "bold"),
    fg="navy"
)

title.pack(pady=10)

# -----------------------------
# Inputs
# -----------------------------

frame = tk.Frame(root)
frame.pack()

tk.Label(frame, text="Yield Strength fy (MPa)").grid(row=0, column=0, sticky="w")
entry_fy = tk.Entry(frame)
entry_fy.insert(0, "355")
entry_fy.grid(row=0, column=1)

tk.Label(frame, text="Width (mm)").grid(row=1, column=0, sticky="w")
entry_width = tk.Entry(frame)
entry_width.insert(0, "150")
entry_width.grid(row=1, column=1)

tk.Label(frame, text="Thickness (mm)").grid(row=2, column=0, sticky="w")
entry_thickness = tk.Entry(frame)
entry_thickness.insert(0, "12")
entry_thickness.grid(row=2, column=1)

tk.Label(frame, text="Design Load (kN)").grid(row=3, column=0, sticky="w")
entry_load = tk.Entry(frame)
entry_load.insert(0, "500")
entry_load.grid(row=3, column=1)

# -----------------------------
# Buttons
# -----------------------------

btn = tk.Button(
    root,
    text="Calculate",
    bg="steelblue",
    fg="white",
    font=("Arial", 12, "bold"),
    command=calculate
)

btn.pack(pady=20)

root.mainloop()