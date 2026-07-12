# CB1 Column Base Lookup - H-Shape

A local, offline **lookup and visualization tool** for the standard CB1
column base (H-shape) records transcribed from `RG6_Standard Drawings.pdf`,
page 59, drawing **RG6-D-00-1330-005 Rev B**.

> **Reference aid only** - verify against the latest approved drawing and
> project requirements before fabrication or construction. This tool does
> not perform structural design, interpolation, or "closest match"
> selection; it only returns exact matches from the 20-record table.

## Files

| File                  | Purpose                                              |
|------------------------|-------------------------------------------------------|
| `app.py`               | Streamlit UI and Plotly 2D/3D visualization           |
| `cb1_hshape_data.py`   | The 20-record lookup table and lookup/validation logic |
| `requirements.txt`     | Pinned minimum dependency versions                     |
| `test_data.py`         | Unit tests for lookup normalization and all 20 records |

## Installation

Requires Python 3.9+.

```bash
# from the project folder
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## Run

```bash
streamlit run app.py
```

This opens the app in your browser (typically `http://localhost:8501`).
No internet connection or cloud API is required.

## Test

```bash
python -m unittest test_data.py -v
```

All 23 tests should pass. These tests cover:
- case-insensitive, space-insensitive lookup normalization
- exact-match-only behavior (no partial or "closest" matches)
- presence and uniqueness of all 20 marks and member names
- bolt count, positive dimensions, and bolt-centres-within-plate checks for every record

## Using the app

1. Use the **dropdown** (grouped by mark) or the **search box** to find a
   record. Search accepts either a member mark (`H253`) or a member name
   (`UB254x146x37`), case-insensitively and with spaces ignored.
2. If no exact match exists, the app shows:
   *"No standard CB1 H-shape entry found. Refer to the approved drawings / structural engineer."*
3. The **result card** shows section dimensions, base plate size, anchor
   bolt details (including `PJ` exactly as labelled), bolt edge
   distances/pitches, fillet weld size ("as called out on the drawing"),
   and the minimum pedestal plan size.
4. Download the selected record as **JSON or CSV**, including source-drawing
   metadata.
5. Use **Compare up to three marks** for a side-by-side reference table.
6. The **3D view** shows the pedestal, base plate, H-section column, anchor
   bolts, and a weld outline at the column-to-plate connection. The
   **pedestal height** and **exposed column height** sliders are explicitly
   illustrative only - those heights are not part of the lookup data.
7. Two **2D diagrams** (plan and elevation) show plate/pedestal/bolt
   layout and the plate-thickness/weld callout.
8. Expand **Drawing notes** for the pedestal-minimum and washer-detail notes.

## Data source

```
Source file:      RG6_Standard Drawings.pdf
Source page:       59
Drawing number:    RG6-D-00-1330-005
Drawing revision:  B
Drawing title:     Standard Drawing - Column Base CB1 (1/2) (H-Shape)
```

The next sheet in that PDF (C- and L-shapes) is outside this app's scope.