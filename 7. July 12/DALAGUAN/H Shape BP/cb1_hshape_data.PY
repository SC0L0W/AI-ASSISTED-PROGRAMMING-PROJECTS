"""
cb1_hshape_data.py

Source data for the CB1 (H-shape) standard column base lookup tool.

Data transcribed from: RG6_Standard Drawings.pdf, physical PDF page 59,
drawing RG6-D-00-1330-005 Rev B, "Standard Drawing - Column Base CB1 (1/2)
(H-Shape)". The next PDF sheet (C- and L-shapes) is outside this app's scope.

This module holds ONLY data and small pure-Python lookup/validation helpers.
No UI code and no plotting code belongs here.
"""

from __future__ import annotations
from typing import Optional, List, Dict, Any

SOURCE_METADATA: Dict[str, str] = {
    "source_file": "RG6_Standard Drawings.pdf",
    "source_page": "59",
    "drawing_number": "RG6-D-00-1330-005",
    "drawing_revision": "B",
    "drawing_title": "Standard Drawing - Column Base CB1 (1/2) (H-Shape)",
}

DISCLAIMER = (
    "Reference aid only - verify against the latest approved drawing and "
    "project requirements before fabrication or construction."
)

NOT_FOUND_MESSAGE = (
    "No standard CB1 H-shape entry found. Refer to the approved drawings / "
    "structural engineer."
)

# section_mm      = [depth, flange_width, web_thickness, flange_thickness]
# plate_xy_mm     = [X, Y]  (X = horizontal dimension at top of plan, Y = vertical plan dimension)
# pedestal_xy_mm  = [X, Y]  minimum plan dimensions (NOT a designed footing/pedestal height)
# bolt_grid_mm    = four bolt-centre locations from the plate edges and their pitches
CB1_H_SHAPE: List[Dict[str, Any]] = [
    {"mark": "H153", "member": "UC152x152x30", "section_mm": [157.6, 152.9, 6.5, 9.4], "plate_xy_mm": [310, 310], "plate_thickness_mm": 20, "weld_size_mm": 6, "pedestal_xy_mm": [520, 520], "bolt_count": 4, "bolt_size": "3/4 in", "hole_diameter_mm": 28, "pj_mm": 80, "bolt_grid_mm": {"edge_x": 45, "pitch_x": 220, "edge_y": 45, "pitch_y": 220}},
    {"mark": "H253", "member": "UB254x146x37", "section_mm": [256.0, 146.4, 6.3, 10.9], "plate_xy_mm": [240, 300], "plate_thickness_mm": 25, "weld_size_mm": 6, "pedestal_xy_mm": [440, 440], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 100, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 140, "edge_y": 80, "pitch_y": 140}},
    {"mark": "H304", "member": "UC305x305x97", "section_mm": [307.9, 305.3, 9.9, 15.4], "plate_xy_mm": [350, 350], "plate_thickness_mm": 40, "weld_size_mm": 9, "pedestal_xy_mm": [440, 440], "bolt_count": 4, "bolt_size": "1-1/4 in", "hole_diameter_mm": 44, "pj_mm": 135, "bolt_grid_mm": {"edge_x": 105, "pitch_x": 140, "edge_y": 105, "pitch_y": 140}},
    {"mark": "H356", "member": "UC356x368x153", "section_mm": [362.0, 370.5, 12.3, 20.7], "plate_xy_mm": [400, 400], "plate_thickness_mm": 50, "weld_size_mm": 12, "pedestal_xy_mm": [460, 460], "bolt_count": 4, "bolt_size": "1-1/4 in", "hole_diameter_mm": 44, "pj_mm": 145, "bolt_grid_mm": {"edge_x": 120, "pitch_x": 160, "edge_y": 120, "pitch_y": 160}},
    {"mark": "H405", "member": "UC356x406x340", "section_mm": [406.4, 403.0, 26.6, 42.9], "plate_xy_mm": [450, 450], "plate_thickness_mm": 50, "weld_size_mm": 12, "pedestal_xy_mm": [500, 500], "bolt_count": 4, "bolt_size": "1-1/2 in", "hole_diameter_mm": 50, "pj_mm": 160, "bolt_grid_mm": {"edge_x": 145, "pitch_x": 160, "edge_y": 145, "pitch_y": 160}},

    {"mark": "H202", "member": "UB203x133x30", "section_mm": [206.8, 133.9, 6.4, 9.6], "plate_xy_mm": [220, 250], "plate_thickness_mm": 20, "weld_size_mm": 6, "pedestal_xy_mm": [400, 400], "bolt_count": 4, "bolt_size": "3/4 in", "hole_diameter_mm": 28, "pj_mm": 80, "bolt_grid_mm": {"edge_x": 60, "pitch_x": 100, "edge_y": 75, "pitch_y": 100}},
    {"mark": "H254", "member": "UC254x254x73", "section_mm": [254.1, 254.6, 8.6, 14.2], "plate_xy_mm": [300, 300], "plate_thickness_mm": 35, "weld_size_mm": 8, "pedestal_xy_mm": [420, 420], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 110, "bolt_grid_mm": {"edge_x": 90, "pitch_x": 120, "edge_y": 90, "pitch_y": 120}},
    {"mark": "H305", "member": "UC305x305x118", "section_mm": [314.5, 307.4, 12.0, 18.7], "plate_xy_mm": [350, 350], "plate_thickness_mm": 50, "weld_size_mm": 11, "pedestal_xy_mm": [440, 440], "bolt_count": 4, "bolt_size": "1-1/4 in", "hole_diameter_mm": 44, "pj_mm": 145, "bolt_grid_mm": {"edge_x": 105, "pitch_x": 140, "edge_y": 105, "pitch_y": 140}},
    {"mark": "H357", "member": "UC356x368x202", "section_mm": [374.6, 374.7, 16.5, 27.0], "plate_xy_mm": [400, 400], "plate_thickness_mm": 50, "weld_size_mm": 12, "pedestal_xy_mm": [500, 500], "bolt_count": 4, "bolt_size": "1-1/2 in", "hole_diameter_mm": 50, "pj_mm": 160, "bolt_grid_mm": {"edge_x": 120, "pitch_x": 160, "edge_y": 120, "pitch_y": 160}},
    {"mark": "H452", "member": "UB457x191x74", "section_mm": [457.0, 190.4, 9.0, 14.5], "plate_xy_mm": [280, 500], "plate_thickness_mm": 35, "weld_size_mm": 9, "pedestal_xy_mm": [480, 600], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 110, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 180, "edge_y": 160, "pitch_y": 180}},

    {"mark": "H203", "member": "UC203x203x46", "section_mm": [203.2, 203.6, 7.2, 11.0], "plate_xy_mm": [250, 250], "plate_thickness_mm": 20, "weld_size_mm": 7, "pedestal_xy_mm": [400, 400], "bolt_count": 4, "bolt_size": "3/4 in", "hole_diameter_mm": 28, "pj_mm": 80, "bolt_grid_mm": {"edge_x": 75, "pitch_x": 100, "edge_y": 75, "pitch_y": 100}},
    {"mark": "H255", "member": "UC254x254x89", "section_mm": [260.3, 256.3, 10.3, 17.3], "plate_xy_mm": [300, 300], "plate_thickness_mm": 45, "weld_size_mm": 10, "pedestal_xy_mm": [420, 420], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 120, "bolt_grid_mm": {"edge_x": 90, "pitch_x": 120, "edge_y": 90, "pitch_y": 120}},
    {"mark": "H352", "member": "UB356x171x51", "section_mm": [355.0, 171.5, 7.4, 11.5], "plate_xy_mm": [260, 400], "plate_thickness_mm": 30, "weld_size_mm": 7, "pedestal_xy_mm": [460, 460], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 105, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 160, "edge_y": 120, "pitch_y": 160}},
    {"mark": "H402", "member": "UB406x178x67", "section_mm": [409.4, 178.8, 8.8, 14.3], "plate_xy_mm": [260, 450], "plate_thickness_mm": 35, "weld_size_mm": 8, "pedestal_xy_mm": [460, 460], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 110, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 160, "edge_y": 145, "pitch_y": 160}},
    {"mark": "H552", "member": "UB533x210x92", "section_mm": [533.1, 209.3, 10.1, 15.6], "plate_xy_mm": [280, 580], "plate_thickness_mm": 35, "weld_size_mm": 10, "pedestal_xy_mm": [480, 680], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 110, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 180, "edge_y": 200, "pitch_y": 180}},

    {"mark": "H205", "member": "UC203x203x60", "section_mm": [209.6, 205.8, 9.4, 14.2], "plate_xy_mm": [250, 250], "plate_thickness_mm": 25, "weld_size_mm": 9, "pedestal_xy_mm": [400, 400], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 100, "bolt_grid_mm": {"edge_x": 75, "pitch_x": 100, "edge_y": 75, "pitch_y": 100}},
    {"mark": "H302", "member": "UB305x165x40", "section_mm": [303.4, 165.0, 6.0, 10.2], "plate_xy_mm": [260, 350], "plate_thickness_mm": 25, "weld_size_mm": 6, "pedestal_xy_mm": [460, 460], "bolt_count": 4, "bolt_size": "1 in", "hole_diameter_mm": 34, "pj_mm": 100, "bolt_grid_mm": {"edge_x": 50, "pitch_x": 160, "edge_y": 95, "pitch_y": 160}},
    {"mark": "H355", "member": "UC356x368x129", "section_mm": [355.6, 368.6, 10.4, 17.5], "plate_xy_mm": [400, 400], "plate_thickness_mm": 35, "weld_size_mm": 10, "pedestal_xy_mm": [460, 460], "bolt_count": 4, "bolt_size": "1-1/4 in", "hole_diameter_mm": 44, "pj_mm": 130, "bolt_grid_mm": {"edge_x": 120, "pitch_x": 160, "edge_y": 120, "pitch_y": 160}},
    {"mark": "H404", "member": "UC356x406x235", "section_mm": [381.0, 394.8, 18.4, 30.2], "plate_xy_mm": [450, 450], "plate_thickness_mm": 50, "weld_size_mm": 12, "pedestal_xy_mm": [500, 500], "bolt_count": 4, "bolt_size": "1-1/2 in", "hole_diameter_mm": 50, "pj_mm": 160, "bolt_grid_mm": {"edge_x": 145, "pitch_x": 160, "edge_y": 145, "pitch_y": 160}},
    {"mark": "H602", "member": "UB610x305x149", "section_mm": [612.4, 304.8, 11.8, 19.7], "plate_xy_mm": [350, 660], "plate_thickness_mm": 45, "weld_size_mm": 11, "pedestal_xy_mm": [480, 760], "bolt_count": 4, "bolt_size": "1-1/4 in", "hole_diameter_mm": 44, "pj_mm": 140, "bolt_grid_mm": {"edge_x": 85, "pitch_x": 180, "edge_y": 240, "pitch_y": 180}},
]


def normalize(text: str) -> str:
    """Uppercase and strip all whitespace so lookups are case- and space-insensitive."""
    if text is None:
        return ""
    return "".join(text.split()).upper()


def get_marks() -> List[str]:
    """Sorted list of all member marks, for populating a dropdown."""
    return sorted(rec["mark"] for rec in CB1_H_SHAPE)


def find_record(query: str) -> Optional[Dict[str, Any]]:
    """
    Exact-match lookup by member mark OR member name, case-insensitive and
    with spaces ignored. Returns None if there is no exact match. This
    function never interpolates or returns a "closest" record.
    """
    q = normalize(query)
    if not q:
        return None
    for rec in CB1_H_SHAPE:
        if normalize(rec["mark"]) == q or normalize(rec["member"]) == q:
            return rec
    return None


def get_record_by_mark(mark: str) -> Optional[Dict[str, Any]]:
    """Exact-match lookup by mark only (used by the dropdown, which already lists valid marks)."""
    for rec in CB1_H_SHAPE:
        if rec["mark"] == mark:
            return rec
    return None


def bolt_offsets_mm(rec: Dict[str, Any]) -> Dict[str, float]:
    """
    Half-spacing of the four bolt centres from plate centre, in X and Y,
    derived from edge distance + pitch (edge*2 + pitch == plate dimension
    for this drawing standard).
    """
    plate_x, plate_y = rec["plate_xy_mm"]
    grid = rec["bolt_grid_mm"]
    dx = plate_x / 2.0 - grid["edge_x"]
    dy = plate_y / 2.0 - grid["edge_y"]
    return {"dx": dx, "dy": dy}


def validate_records(tolerance_mm: float = 0.51) -> List[str]:
    """
    Validate every record. Returns a list of human-readable error strings;
    an empty list means all records are valid. Checks:
      - exactly 4 bolts
      - all key dimensions are positive
      - bolt centres fall within the plate (edge*2 + pitch <= plate dimension)
      - mark and member are each unique across the table
    """
    errors: List[str] = []
    seen_marks = set()
    seen_members = set()

    for rec in CB1_H_SHAPE:
        mark = rec.get("mark", "<unknown>")

        if rec.get("bolt_count") != 4:
            errors.append(f"{mark}: bolt_count must be 4, got {rec.get('bolt_count')!r}")

        for key in ("plate_thickness_mm", "weld_size_mm", "hole_diameter_mm", "pj_mm"):
            val = rec.get(key)
            if not isinstance(val, (int, float)) or val <= 0:
                errors.append(f"{mark}: {key} must be a positive number, got {val!r}")

        for key in ("section_mm", "plate_xy_mm", "pedestal_xy_mm"):
            vals = rec.get(key) or []
            if len(vals) < 2 or any((not isinstance(v, (int, float)) or v <= 0) for v in vals):
                errors.append(f"{mark}: {key} must contain only positive numbers, got {vals!r}")

        plate_x, plate_y = rec["plate_xy_mm"]
        grid = rec["bolt_grid_mm"]
        span_x = grid["edge_x"] * 2 + grid["pitch_x"]
        span_y = grid["edge_y"] * 2 + grid["pitch_y"]
        if span_x > plate_x + tolerance_mm:
            errors.append(f"{mark}: bolt X span ({span_x} mm) exceeds plate X ({plate_x} mm)")
        if span_y > plate_y + tolerance_mm:
            errors.append(f"{mark}: bolt Y span ({span_y} mm) exceeds plate Y ({plate_y} mm)")

        if mark in seen_marks:
            errors.append(f"Duplicate mark: {mark}")
        seen_marks.add(mark)

        member = rec.get("member")
        if member in seen_members:
            errors.append(f"Duplicate member name: {member} ({mark})")
        seen_members.add(member)

    return errors