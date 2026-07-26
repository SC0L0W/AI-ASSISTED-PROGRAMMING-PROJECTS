import tkinter as tk
from tkinter import ttk, messagebox
import math

# Steel bar areas (mm²)
bar_areas = {
    "10": 78.5,
    "12": 113.1,
    "16": 201.1,
    "20": 314.2,
    "25": 490.9,
    "28": 615.8,
    "32": 804.2
}

def calculate():
    try:
        width = float(entry_width.get())      # mm
        cover = float(entry_cover.get())      # mm
        thickness = float(entry_thickness.get())  # mm
        fy = float(entry_fy.get())            # MPa
        moment = float(entry_moment.get())    # kN-m

        bar_size = combo_bar.get()
        area_bar = bar_areas[bar_size]

        phi = 0.90

        # Effective depth
        d = thickness - cover - (float(bar_size) / 2)

        # Approximate Required Steel Area (Simplified)
        Mu = moment * 1e6  # convert kN-m to N-mm

        As = Mu / (phi * fy * 0.9 * d)

        nbars = math.ceil(As / area_bar)

        spacing = (width - 2 * cover) / (nbars - 1) if nbars > 1 else 0

        result.set(
            f"Effective Depth (d): {d:.1f} mm\n\n"
            f"Required Steel Area (As): {As:.1f} mm²\n\n"
            f"Bar Size: {bar_size} mm\n"
            f"Area per Bar: {area_bar:.1f} mm²\n\n"
            f"Required No. of Bars: {nbars}\n\n"
            f"Approximate Spacing: {spacing:.1f} mm"
        )

    except Exception:
        messagebox.showerror("Error", "Please enter valid numbers.")

root = tk.Tk()
root.title("Simple Isolated Footing Reinforcement Calculator")
root.geometry("500x600")

title = tk.Label(root,
                 text="Isolated Footing Reinforcement Calculator",
                 font=("Arial", 15, "bold"))
title.pack(pady=10)

frame = tk.Frame(root)
frame.pack()

def add_row(label):
    row = tk.Frame(frame)
    row.pack(fill="x", pady=4)
    tk.Label(row, text=label, width=20, anchor="w").pack(side="left")
    entry = tk.Entry(row)
    entry.pack(side="right")
    return entry

entry_width = add_row("Footing Width (mm)")
entry_thickness = add_row("Thickness (mm)")
entry_cover = add_row("Concrete Cover (mm)")
entry_fy = add_row("Steel fy (MPa)")
entry_moment = add_row("Moment Mu (kN-m)")

row = tk.Frame(frame)
row.pack(fill="x", pady=5)

tk.Label(row, text="Bar Size", width=20, anchor="w").pack(side="left")

combo_bar = ttk.Combobox(
    row,
    values=list(bar_areas.keys()),
    state="readonly"
)
combo_bar.current(3)
combo_bar.pack(side="right")

tk.Button(root,
          text="Calculate",
          bg="green",
          fg="white",
          command=calculate).pack(pady=10)

result = tk.StringVar()

tk.Label(root,
         textvariable=result,
         justify="left",
         font=("Arial", 11),
         bg="white",
         relief="sunken",
         width=55,
         height=15).pack(pady=10)

root.mainloop()
