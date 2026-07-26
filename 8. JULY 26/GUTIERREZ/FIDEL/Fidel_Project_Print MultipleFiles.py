#!/usr/bin/env python3
"""
PDF Print Manager
==================
A desktop GUI (Tkinter) for queuing multiple PDF files and printing them
with configurable printer settings: printer selection, copies, duplex,
color mode, paper size, orientation, page range, and sheets-per-page (N-up).

Cross-platform backend:
  - Windows  : uses SumatraPDF (if installed) for full option support,
               falling back to the default Windows "print" shell verb.
  - Linux/Mac: uses CUPS `lp` command line.

No third-party packages are required to RUN the GUI itself.
Optional: `pywin32` improves Windows printer listing accuracy.

Author: Generated for user
"""

import os
import sys
import shutil
import subprocess
import platform
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "PDF Print Manager"

PAPER_SIZES = ["A4", "Letter", "Legal", "A3", "A5"]
ORIENTATIONS = ["Portrait", "Landscape"]
DUPLEX_MODES = ["One-sided", "Two-sided (long edge)", "Two-sided (short edge)"]
COLOR_MODES = ["Color", "Grayscale"]
SHEETS_PER_PAGE = ["1", "2", "4", "6", "9", "16"]


def get_system_printers():
    """Return a list of installed printer names for the current OS."""
    system = platform.system()
    printers = []

    if system == "Windows":
        try:
            import win32print  # optional dependency
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            printers = [p[2] for p in win32print.EnumPrinters(flags)]
        except ImportError:
            # Fallback: use wmic
            try:
                out = subprocess.run(
                    ["wmic", "printer", "get", "name"],
                    capture_output=True, text=True, timeout=10
                )
                lines = [l.strip() for l in out.stdout.splitlines() if l.strip()]
                printers = [l for l in lines if l.lower() != "name"]
            except Exception:
                printers = []
    else:
        # Linux / macOS via CUPS
        try:
            out = subprocess.run(["lpstat", "-p"], capture_output=True, text=True, timeout=10)
            for line in out.stdout.splitlines():
                if line.startswith("printer "):
                    printers.append(line.split()[1])
        except Exception:
            printers = []

    return printers


def get_default_printer():
    system = platform.system()
    if system == "Windows":
        try:
            import win32print
            return win32print.GetDefaultPrinter()
        except Exception:
            return None
    else:
        try:
            out = subprocess.run(["lpstat", "-d"], capture_output=True, text=True, timeout=10)
            line = out.stdout.strip()
            if ":" in line:
                return line.split(":", 1)[1].strip()
        except Exception:
            return None
    return None


class PDFPrintManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x600")
        self.minsize(700, 560)

        self.files = []  # list of file paths

        self._build_ui()
        self._refresh_printers()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        # --- File queue section -----------------------------------------
        files_frame = ttk.LabelFrame(root, text="PDF Files Queue", padding=10)
        files_frame.pack(fill="both", expand=True, side="top")

        list_container = ttk.Frame(files_frame)
        list_container.pack(fill="both", expand=True, side="left")

        self.file_listbox = tk.Listbox(list_container, selectmode="extended", height=10)
        self.file_listbox.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.file_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_listbox.configure(yscrollcommand=scrollbar.set)

        btns = ttk.Frame(files_frame)
        btns.pack(side="left", fill="y", padx=(10, 0))

        ttk.Button(btns, text="Add File(s)...", command=self.add_files).pack(fill="x", pady=2)
        ttk.Button(btns, text="Add Folder...", command=self.add_folder).pack(fill="x", pady=2)
        ttk.Button(btns, text="Remove Selected", command=self.remove_selected).pack(fill="x", pady=2)
        ttk.Button(btns, text="Move Up", command=lambda: self.move_selected(-1)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Move Down", command=lambda: self.move_selected(1)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Clear All", command=self.clear_files).pack(fill="x", pady=2)

        # --- Printer settings section -------------------------------------
        settings_frame = ttk.LabelFrame(root, text="Printer Settings", padding=10)
        settings_frame.pack(fill="x", side="top", pady=(10, 0))

        settings_frame.columnconfigure(1, weight=1)
        settings_frame.columnconfigure(3, weight=1)

        # Printer selection
        ttk.Label(settings_frame, text="Printer:").grid(row=0, column=0, sticky="w", pady=4)
        self.printer_var = tk.StringVar()
        self.printer_combo = ttk.Combobox(settings_frame, textvariable=self.printer_var, state="readonly")
        self.printer_combo.grid(row=0, column=1, sticky="ew", padx=(6, 6), pady=4)
        ttk.Button(settings_frame, text="Refresh", command=self._refresh_printers).grid(row=0, column=2, sticky="w")

        # Copies
        ttk.Label(settings_frame, text="Copies:").grid(row=0, column=3, sticky="w", padx=(20, 0))
        self.copies_var = tk.IntVar(value=1)
        ttk.Spinbox(settings_frame, from_=1, to=999, textvariable=self.copies_var, width=6).grid(
            row=0, column=4, sticky="w", padx=(6, 0)
        )

        # Paper size
        ttk.Label(settings_frame, text="Paper size:").grid(row=1, column=0, sticky="w", pady=4)
        self.paper_var = tk.StringVar(value=PAPER_SIZES[0])
        ttk.Combobox(settings_frame, textvariable=self.paper_var, values=PAPER_SIZES, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(6, 6), pady=4
        )

        # Orientation
        ttk.Label(settings_frame, text="Orientation:").grid(row=1, column=3, sticky="w", padx=(20, 0))
        self.orientation_var = tk.StringVar(value=ORIENTATIONS[0])
        ttk.Combobox(
            settings_frame, textvariable=self.orientation_var, values=ORIENTATIONS, state="readonly", width=15
        ).grid(row=1, column=4, sticky="w", padx=(6, 0))

        # Duplex
        ttk.Label(settings_frame, text="Duplex:").grid(row=2, column=0, sticky="w", pady=4)
        self.duplex_var = tk.StringVar(value=DUPLEX_MODES[0])
        ttk.Combobox(settings_frame, textvariable=self.duplex_var, values=DUPLEX_MODES, state="readonly").grid(
            row=2, column=1, sticky="ew", padx=(6, 6), pady=4
        )

        # Color mode
        ttk.Label(settings_frame, text="Color mode:").grid(row=2, column=3, sticky="w", padx=(20, 0))
        self.color_var = tk.StringVar(value=COLOR_MODES[0])
        ttk.Combobox(
            settings_frame, textvariable=self.color_var, values=COLOR_MODES, state="readonly", width=15
        ).grid(row=2, column=4, sticky="w", padx=(6, 0))

        # Sheets per page (N-up)
        ttk.Label(settings_frame, text="Sheets per page:").grid(row=3, column=0, sticky="w", pady=4)
        self.nup_var = tk.StringVar(value=SHEETS_PER_PAGE[0])
        ttk.Combobox(
            settings_frame, textvariable=self.nup_var, values=SHEETS_PER_PAGE, state="readonly"
        ).grid(row=3, column=1, sticky="ew", padx=(6, 6), pady=4)

        # Page range
        ttk.Label(settings_frame, text="Page range:").grid(row=3, column=3, sticky="w", padx=(20, 0))
        self.range_var = tk.StringVar(value="")
        range_entry = ttk.Entry(settings_frame, textvariable=self.range_var, width=17)
        range_entry.grid(row=3, column=4, sticky="w", padx=(6, 0))
        ttk.Label(
            settings_frame, text="e.g. 1-3,5  (applies to each file; leave blank for all pages)",
            foreground="#666"
        ).grid(row=4, column=1, columnspan=4, sticky="w", pady=(0, 4))

        # Collate
        self.collate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, text="Collate copies", variable=self.collate_var).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )

        # --- Action buttons -------------------------------------------------
        action_frame = ttk.Frame(root)
        action_frame.pack(fill="x", side="top", pady=(12, 0))

        ttk.Button(action_frame, text="Preview Settings Summary", command=self.show_summary).pack(
            side="left"
        )
        self.print_btn = ttk.Button(action_frame, text="Print Queue", command=self.print_queue)
        self.print_btn.pack(side="right")

        # --- Status/log box --------------------------------------------------
        log_frame = ttk.LabelFrame(root, text="Status Log", padding=6)
        log_frame.pack(fill="both", expand=False, side="top", pady=(10, 0))
        self.log_text = tk.Text(log_frame, height=7, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # File queue operations
    # ------------------------------------------------------------------
    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF files", filetypes=[("PDF files", "*.pdf")]
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
        self._refresh_file_listbox()

    def add_folder(self):
        folder = filedialog.askdirectory(title="Select a folder containing PDFs")
        if not folder:
            return
        added = 0
        for name in sorted(os.listdir(folder)):
            if name.lower().endswith(".pdf"):
                full = os.path.join(folder, name)
                if full not in self.files:
                    self.files.append(full)
                    added += 1
        self._refresh_file_listbox()
        self._log(f"Added {added} PDF(s) from folder: {folder}")

    def remove_selected(self):
        selected = list(self.file_listbox.curselection())
        for idx in reversed(selected):
            del self.files[idx]
        self._refresh_file_listbox()

    def move_selected(self, direction):
        selected = list(self.file_listbox.curselection())
        if not selected:
            return
        indices = selected if direction < 0 else reversed(selected)
        for idx in indices:
            new_idx = idx + direction
            if 0 <= new_idx < len(self.files):
                self.files[idx], self.files[new_idx] = self.files[new_idx], self.files[idx]
        self._refresh_file_listbox()
        new_selection = [i + direction for i in selected if 0 <= i + direction < len(self.files)]
        for i in new_selection:
            self.file_listbox.selection_set(i)

    def clear_files(self):
        self.files = []
        self._refresh_file_listbox()

    def _refresh_file_listbox(self):
        self.file_listbox.delete(0, "end")
        for f in self.files:
            self.file_listbox.insert("end", os.path.basename(f))

    # ------------------------------------------------------------------
    # Printer discovery
    # ------------------------------------------------------------------
    def _refresh_printers(self):
        printers = get_system_printers()
        default = get_default_printer()
        self.printer_combo["values"] = printers
        if printers:
            if default in printers:
                self.printer_var.set(default)
            else:
                self.printer_var.set(printers[0])
        else:
            self.printer_var.set("")
            self._log("No printers detected automatically. You can still type a printer name manually.")
        self.printer_combo["state"] = "normal"  # allow manual entry too

    # ------------------------------------------------------------------
    # Settings summary / validation
    # ------------------------------------------------------------------
    def _settings_dict(self):
        return {
            "printer": self.printer_var.get().strip(),
            "copies": self.copies_var.get(),
            "paper_size": self.paper_var.get(),
            "orientation": self.orientation_var.get(),
            "duplex": self.duplex_var.get(),
            "color_mode": self.color_var.get(),
            "sheets_per_page": self.nup_var.get(),
            "page_range": self.range_var.get().strip(),
            "collate": self.collate_var.get(),
        }

    def show_summary(self):
        s = self._settings_dict()
        lines = [
            f"Files queued: {len(self.files)}",
            f"Printer: {s['printer'] or '(none selected)'}",
            f"Copies: {s['copies']}  (collate: {'yes' if s['collate'] else 'no'})",
            f"Paper size: {s['paper_size']}   Orientation: {s['orientation']}",
            f"Duplex: {s['duplex']}",
            f"Color mode: {s['color_mode']}",
            f"Sheets per page (N-up): {s['sheets_per_page']}",
            f"Page range per file: {s['page_range'] or 'All pages'}",
        ]
        messagebox.showinfo("Settings Summary", "\n".join(lines))

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------
    def print_queue(self):
        if not self.files:
            messagebox.showwarning(APP_TITLE, "Add at least one PDF file to the queue first.")
            return

        s = self._settings_dict()
        if not s["printer"]:
            messagebox.showwarning(APP_TITLE, "Please select or enter a printer name.")
            return

        confirm = messagebox.askyesno(
            APP_TITLE,
            f"Send {len(self.files)} file(s) to printer '{s['printer']}' with the current settings?"
        )
        if not confirm:
            return

        system = platform.system()
        self._log(f"Starting print job on {system}: {len(self.files)} file(s) -> {s['printer']}")

        try:
            if system == "Windows":
                self._print_windows(s)
            else:
                self._print_unix(s)
            self._log("Print job(s) submitted successfully.")
            messagebox.showinfo(APP_TITLE, "Print job(s) submitted. Check your printer queue for status.")
        except Exception as exc:
            self._log(f"ERROR: {exc}")
            messagebox.showerror(APP_TITLE, f"Printing failed:\n{exc}")

    # -- Linux / macOS via CUPS `lp` -----------------------------------
    def _print_unix(self, s):
        options = []

        # Copies
        options += ["-n", str(s["copies"])]

        # Media / paper size (CUPS option names)
        media_map = {"A4": "A4", "Letter": "Letter", "Legal": "Legal", "A3": "A3", "A5": "A5"}
        options += ["-o", f"media={media_map.get(s['paper_size'], 'A4')}"]

        # Orientation
        if s["orientation"] == "Landscape":
            options += ["-o", "landscape"]

        # Duplex
        duplex_map = {
            "One-sided": "one-sided",
            "Two-sided (long edge)": "two-sided-long-edge",
            "Two-sided (short edge)": "two-sided-short-edge",
        }
        options += ["-o", f"sides={duplex_map[s['duplex']]}"]

        # Color mode
        if s["color_mode"] == "Grayscale":
            options += ["-o", "print-color-mode=monochrome"]
        else:
            options += ["-o", "print-color-mode=color"]

        # Sheets per page (N-up)
        if s["sheets_per_page"] != "1":
            options += ["-o", f"number-up={s['sheets_per_page']}"]

        # Collate
        options += ["-o", f"collate={'true' if s['collate'] else 'false'}"]

        # Page range
        if s["page_range"]:
            options += ["-o", f"page-ranges={s['page_range']}"]

        for f in self.files:
            cmd = ["lp", "-d", s["printer"]] + options + [f]
            self._log("Running: " + " ".join(cmd))
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"lp failed for {f}: {result.stderr.strip()}")

    # -- Windows: SumatraPDF if available, else default shell print ----
    def _print_windows(self, s):
        sumatra = shutil.which("SumatraPDF.exe") or shutil.which("SumatraPDF")

        if sumatra:
            for f in self.files:
                settings_parts = []
                # SumatraPDF -print-settings supports: paper, duplex/simplex,
                # color/monochrome, N-up via "N" shortcut, collate, page ranges.
                settings_parts.append(s["paper_size"].lower())
                if s["duplex"] == "One-sided":
                    settings_parts.append("simplex")
                elif s["duplex"] == "Two-sided (long edge)":
                    settings_parts.append("duplex")
                else:
                    settings_parts.append("duplexshort")
                settings_parts.append("color" if s["color_mode"] == "Color" else "monochrome")
                settings_parts.append(f"{s['sheets_per_page']}x")
                if s["page_range"]:
                    settings_parts.append(s["page_range"])

                cmd = [
                    sumatra,
                    "-print-to", s["printer"],
                    "-print-settings", ",".join(settings_parts),
                    "-silent",
                    f,
                ]
                self._log("Running: " + " ".join(cmd))
                for _ in range(s["copies"]):
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        raise RuntimeError(f"SumatraPDF failed for {f}: {result.stderr.strip()}")
        else:
            self._log(
                "SumatraPDF not found on PATH — falling back to the default Windows print "
                "verb (advanced options like N-up/duplex depend on the printer driver's own "
                "defaults in this mode)."
            )
            import win32api  # requires pywin32
            for f in self.files:
                for _ in range(s["copies"]):
                    win32api.ShellExecute(0, "print", f, f'"{s["printer"]}"', ".", 0)


def main():
    app = PDFPrintManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
