"""
app.py

CB1 (H-shape) column base lookup and visualization tool.

This is a REFERENCE / LOOKUP AID ONLY. It performs no structural design,
no interpolation, and no "closest match" selection. See DISCLAIMER and
NOT_FOUND_MESSAGE in cb1_hshape_data.py.
"""

import json
import io

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from cb1_hshape_data import (
    CB1_H_SHAPE,
    SOURCE_METADATA,
    DISCLAIMER,
    NOT_FOUND_MESSAGE,
    get_marks,
    get_record_by_mark,
    find_record,
    bolt_offsets_mm,
    validate_records,
)

# Okabe-Ito colour-blind-friendly palette
COLOR_PEDESTAL = "rgb(150,150,150)"
COLOR_PLATE = "#0072B2"
COLOR_COLUMN = "#D55E00"
COLOR_BOLT = "#009E73"
COLOR_WELD = "#CC79A7"

st.set_page_config(page_title="CB1 H-Shape Column Base Lookup", layout="wide")

# ---------------------------------------------------------------------------
# Startup validation
# ---------------------------------------------------------------------------
_errors = validate_records()
if _errors:
    st.error(
        "Data validation failed at startup. The app cannot run until "
        "cb1_hshape_data.py is corrected:\n\n" + "\n".join(f"- {e}" for e in _errors)
    )
    st.stop()

# ---------------------------------------------------------------------------
# Geometry helpers (kept local to the UI/plotting layer, not the data layer)
# ---------------------------------------------------------------------------

def box_mesh(x_range, y_range, z_range, color, name, opacity=1.0, hovertext="", showlegend=True):
    """Axis-aligned rectangular solid as a Plotly Mesh3d, using the standard cube triangulation."""
    x0, x1 = x_range
    y0, y1 = y_range
    z0, z1 = z_range
    xs = [x0, x0, x1, x1, x0, x0, x1, x1]
    ys = [y0, y1, y1, y0, y0, y1, y1, y0]
    zs = [z0, z0, z0, z0, z1, z1, z1, z1]
    i = [7, 0, 0, 0, 4, 4, 6, 6, 4, 0, 3, 2]
    j = [3, 4, 1, 2, 5, 6, 5, 2, 0, 1, 6, 3]
    k = [0, 7, 2, 3, 6, 7, 1, 1, 5, 5, 7, 6]
    return go.Mesh3d(
        x=xs, y=ys, z=zs, i=i, j=j, k=k,
        color=color, opacity=opacity, name=name, showlegend=showlegend,
        hovertext=hovertext, hoverinfo="text", flatshading=True,
    )


def cylinder_mesh(cx, cy, z0, z1, radius, color, name, n=14, hovertext="", showlegend=True):
    """Vertical cylinder (used for anchor bolts) as a Plotly Mesh3d."""
    theta = np.linspace(0, 2 * np.pi, n, endpoint=False)
    xb = cx + radius * np.cos(theta)
    yb = cy + radius * np.sin(theta)

    xs = list(xb) + list(xb) + [cx, cx]
    ys = list(yb) + list(yb) + [cy, cy]
    zs = [z0] * n + [z1] * n + [z0, z1]
    bottom_center = 2 * n
    top_center = 2 * n + 1

    i, j, k = [], [], []
    for idx in range(n):
        nxt = (idx + 1) % n
        # side wall: two triangles
        i += [idx, nxt]
        j += [nxt, nxt + n]
        k += [idx + n, idx + n]
        # bottom cap
        i.append(idx); j.append(nxt); k.append(bottom_center)
        # top cap
        i.append(idx + n); j.append(top_center); k.append(nxt + n)

    return go.Mesh3d(
        x=xs, y=ys, z=zs, i=i, j=j, k=k,
        color=color, opacity=1.0, name=name, showlegend=showlegend,
        hovertext=hovertext, hoverinfo="text", flatshading=True,
    )


def h_outline(depth, bf, tw, tf):
    """12-point outline of the H/I cross-section (X = flange width dir, Y = depth dir)."""
    hd, hb, hw = depth / 2, bf / 2, tw / 2
    return [
        (hb, hd), (hb, hd - tf), (hw, hd - tf), (hw, -(hd - tf)),
        (hb, -(hd - tf)), (hb, -hd), (-hb, -hd), (-hb, -(hd - tf)),
        (-hw, -(hd - tf)), (-hw, hd - tf), (-hb, hd - tf), (-hb, hd), (hb, hd),
    ]


def build_3d_figure(rec, pedestal_height, exposed_height):
    plate_x, plate_y = rec["plate_xy_mm"]
    plate_t = rec["plate_thickness_mm"]
    ped_x, ped_y = rec["pedestal_xy_mm"]
    depth, bf, tw, tf = rec["section_mm"]
    hole_d = rec["hole_diameter_mm"]
    pj = rec["pj_mm"]
    weld = rec["weld_size_mm"]

    z_ped0, z_ped1 = 0.0, float(pedestal_height)
    z_plate0, z_plate1 = z_ped1, z_ped1 + plate_t
    z_col0 = z_plate1
    z_col1 = z_col0 + float(exposed_height)

    fig = go.Figure()

    fig.add_trace(box_mesh(
        (-ped_x / 2, ped_x / 2), (-ped_y / 2, ped_y / 2), (z_ped0, z_ped1),
        COLOR_PEDESTAL, f"Pedestal (min plan) {ped_x} x {ped_y} mm", opacity=0.55,
        hovertext=f"Minimum pedestal plan: {ped_x} x {ped_y} mm<br>(height is illustrative only)",
    ))

    fig.add_trace(box_mesh(
        (-plate_x / 2, plate_x / 2), (-plate_y / 2, plate_y / 2), (z_plate0, z_plate1),
        COLOR_PLATE, f"Base plate {plate_x} x {plate_y} x {plate_t} mm", opacity=0.95,
        hovertext=f"Base plate: {plate_x} x {plate_y} x {plate_t} mm",
    ))

    hd = depth / 2
    hw = tw / 2
    fig.add_trace(box_mesh(
        (-bf / 2, bf / 2), (hd - tf, hd), (z_col0, z_col1),
        COLOR_COLUMN, f"Column {rec['member']}", opacity=1.0,
        hovertext=f"{rec['member']}: {depth} x {bf} x {tw} x {tf} mm (depth x flange width x web t x flange t)",
        showlegend=True,
    ))
    fig.add_trace(box_mesh(
        (-bf / 2, bf / 2), (-hd, -(hd - tf)), (z_col0, z_col1),
        COLOR_COLUMN, "Bottom flange", opacity=1.0, hovertext="Bottom flange", showlegend=False,
    ))
    fig.add_trace(box_mesh(
        (-hw, hw), (-(hd - tf), hd - tf), (z_col0, z_col1),
        COLOR_COLUMN, "Web", opacity=1.0, hovertext="Web", showlegend=False,
    ))

    offs = bolt_offsets_mm(rec)
    dx, dy = offs["dx"], offs["dy"]
    bolt_radius = max(hole_d * 0.32, 4.0)  # visually thinner than the hole
    bolt_z0 = z_ped1 - 150.0  # illustrative embedment only, not from the lookup table
    bolt_z1 = z_ped1 + pj
    first = True
    for sx in (-1, 1):
        for sy in (-1, 1):
            fig.add_trace(cylinder_mesh(
                sx * dx, sy * dy, bolt_z0, bolt_z1, bolt_radius, COLOR_BOLT,
                f"Anchor bolt {rec['bolt_size']} (hole {hole_d} mm, PJ {pj} mm)",
                hovertext=f"Anchor bolt: {rec['bolt_size']}<br>Hole dia: {hole_d} mm<br>PJ: {pj} mm",
                showlegend=first,
            ))
            first = False

    pts = h_outline(depth, bf, tw, tf)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    zs = [z_col0 + 0.5] * len(pts)
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs, mode="lines",
        line=dict(color=COLOR_WELD, width=9),
        name=f"Fillet weld {weld} mm (as called out)",
        hovertext=f"Fillet weld: {weld} mm (as called out on the drawing)",
        hoverinfo="text",
    ))

    fig.update_layout(
        scene=dict(
            xaxis_title="X (mm)", yaxis_title="Y (mm)", zaxis_title="Z (mm, illustrative)",
            aspectmode="data",
        ),
        legend=dict(itemsizing="constant", orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=0, r=0, t=10, b=0),
        height=650,
    )
    return fig


def build_plan_figure(rec):
    plate_x, plate_y = rec["plate_xy_mm"]
    ped_x, ped_y = rec["pedestal_xy_mm"]
    offs = bolt_offsets_mm(rec)
    dx, dy = offs["dx"], offs["dy"]

    fig = go.Figure()
    fig.add_shape(type="rect", x0=-ped_x / 2, x1=ped_x / 2, y0=-ped_y / 2, y1=ped_y / 2,
                  line=dict(color="gray"), fillcolor="rgba(150,150,150,0.25)")
    fig.add_shape(type="rect", x0=-plate_x / 2, x1=plate_x / 2, y0=-plate_y / 2, y1=plate_y / 2,
                  line=dict(color=COLOR_PLATE), fillcolor="rgba(0,114,178,0.25)")

    bxs = [dx, dx, -dx, -dx]
    bys = [dy, -dy, dy, -dy]
    fig.add_trace(go.Scatter(
        x=bxs, y=bys, mode="markers",
        marker=dict(size=14, color=COLOR_BOLT, line=dict(color="black", width=1)),
        name=f"Bolts: {rec['bolt_size']} (hole {rec['hole_diameter_mm']} mm)",
    ))

    fig.update_layout(
        title=f"Plan - Plate {plate_x} x {plate_y} mm | Pedestal (min) {ped_x} x {ped_y} mm",
        xaxis_title="X (mm)", yaxis_title="Y (mm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        height=480, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def build_elevation_figure(rec):
    plate_x, plate_y = rec["plate_xy_mm"]
    t = rec["plate_thickness_mm"]
    depth, bf, tw, tf = rec["section_mm"]
    illustrative_col_height = max(depth * 3, 400)

    fig = go.Figure()
    fig.add_shape(type="rect", x0=-plate_x / 2, x1=plate_x / 2, y0=0, y1=t,
                  line=dict(color=COLOR_PLATE), fillcolor="rgba(0,114,178,0.35)")
    fig.add_shape(type="rect", x0=-bf / 2, x1=bf / 2, y0=t, y1=t + illustrative_col_height,
                  line=dict(color=COLOR_COLUMN), fillcolor="rgba(213,94,0,0.15)")
    fig.add_annotation(
        x=0, y=t, text=f"Fillet weld: {rec['weld_size_mm']} mm (as called out)",
        showarrow=True, arrowhead=2, ay=-45, ax=0,
    )
    fig.add_annotation(
        x=plate_x / 2, y=t / 2, text=f"t = {t} mm", showarrow=False, xanchor="left",
    )
    fig.update_layout(
        title="Elevation (illustrative column length)",
        xaxis_title="X (mm)", yaxis_title="Z (mm)",
        yaxis=dict(scaleanchor="x", scaleratio=1),
        height=480, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

st.title("CB1 Column Base Lookup - H-Shape")
st.warning(DISCLAIMER, icon="⚠️")

with st.expander("Source drawing"):
    st.write(
        f"**{SOURCE_METADATA['drawing_title']}**  \n"
        f"Drawing: {SOURCE_METADATA['drawing_number']} Rev {SOURCE_METADATA['drawing_revision']}  \n"
        f"Source: {SOURCE_METADATA['source_file']}, page {SOURCE_METADATA['source_page']}"
    )

col_search, col_dropdown = st.columns([2, 1])
with col_search:
    query = st.text_input(
        "Search by member mark or member name (e.g. \"H253\" or \"UB254x146x37\")",
        value="",
        help="Case-insensitive, spaces ignored. Must match exactly - no closest-match substitution.",
    )
with col_dropdown:
    dropdown_mark = st.selectbox("...or pick a mark", options=get_marks())

selected = None
not_found = False
if query.strip():
    selected = find_record(query)
    if selected is None:
        not_found = True
else:
    selected = get_record_by_mark(dropdown_mark)

if not_found:
    st.error(NOT_FOUND_MESSAGE)

if selected:
    rec = selected
    grid = rec["bolt_grid_mm"]

    st.subheader(f"{rec['mark']} — {rec['member']}")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("**H-section (depth x flange width x web t x flange t)**")
        d, bf, tw, tf = rec["section_mm"]
        st.write(f"{d} x {bf} x {tw} x {tf} mm")
        st.markdown("**Base plate (X x Y x thickness)**")
        px, py = rec["plate_xy_mm"]
        st.write(f"{px} x {py} x {rec['plate_thickness_mm']} mm")
    with c2:
        st.markdown("**Anchor bolts**")
        st.write(f"Count: {rec['bolt_count']}")
        st.write(f"A.BOLT size: {rec['bolt_size']}")
        st.write(f"Hole diameter: {rec['hole_diameter_mm']} mm")
        st.write(f"PJ: {rec['pj_mm']} mm")
    with c3:
        st.markdown("**Bolt edge distances / pitches**")
        st.write(f"Edge X: {grid['edge_x']} mm, Pitch X: {grid['pitch_x']} mm")
        st.write(f"Edge Y: {grid['edge_y']} mm, Pitch Y: {grid['pitch_y']} mm")
        st.markdown("**Fillet weld (as called out on the drawing)**")
        st.write(f"{rec['weld_size_mm']} mm")
        st.markdown("**Minimum pedestal plan size**")
        pdx, pdy = rec["pedestal_xy_mm"]
        st.write(f"{pdx} x {pdy} mm")

    export_payload = {"record": rec, "source": SOURCE_METADATA, "disclaimer": DISCLAIMER}
    dcol1, dcol2 = st.columns(2)
    with dcol1:
        st.download_button(
            "Download record (JSON)",
            data=json.dumps(export_payload, indent=2),
            file_name=f"{rec['mark']}_cb1_hshape.json",
            mime="application/json",
        )
    with dcol2:
        csv_buf = io.StringIO()
        flat = {
            "mark": rec["mark"], "member": rec["member"],
            "section_depth_mm": d, "section_flange_width_mm": bf,
            "section_web_thickness_mm": tw, "section_flange_thickness_mm": tf,
            "plate_x_mm": px, "plate_y_mm": py, "plate_thickness_mm": rec["plate_thickness_mm"],
            "weld_size_mm": rec["weld_size_mm"], "pedestal_x_mm": pdx, "pedestal_y_mm": pdy,
            "bolt_count": rec["bolt_count"], "bolt_size": rec["bolt_size"],
            "hole_diameter_mm": rec["hole_diameter_mm"], "pj_mm": rec["pj_mm"],
            "bolt_edge_x_mm": grid["edge_x"], "bolt_pitch_x_mm": grid["pitch_x"],
            "bolt_edge_y_mm": grid["edge_y"], "bolt_pitch_y_mm": grid["pitch_y"],
            "source_drawing": SOURCE_METADATA["drawing_number"],
            "source_revision": SOURCE_METADATA["drawing_revision"],
            "source_page": SOURCE_METADATA["source_page"],
        }
        header = ",".join(flat.keys())
        values = ",".join(str(v) for v in flat.values())
        st.download_button(
            "Download record (CSV)",
            data=f"{header}\n{values}\n",
            file_name=f"{rec['mark']}_cb1_hshape.csv",
            mime="text/csv",
        )

    st.divider()
    st.subheader("Visualization")
    st.caption(
        "Pedestal and column heights below are illustrative only - they are not "
        "defined by this lookup table. The pedestal plan dimensions shown are minimums."
    )

    scol1, scol2 = st.columns(2)
    with scol1:
        pedestal_height = st.slider("Illustrative pedestal height (mm)", 200, 1200, 500, step=50)
    with scol2:
        exposed_height = st.slider("Illustrative exposed column height (mm)", 200, 2000, 800, step=50)

    st.plotly_chart(build_3d_figure(rec, pedestal_height, exposed_height), use_container_width=True)

    pcol, ecol = st.columns(2)
    with pcol:
        st.plotly_chart(build_plan_figure(rec), use_container_width=True)
    with ecol:
        st.plotly_chart(build_elevation_figure(rec), use_container_width=True)

st.divider()
st.subheader("Compare up to three marks")
compare_marks = st.multiselect("Select marks to compare", options=get_marks(), max_selections=3)
if compare_marks:
    st.caption("Comparison is informational only and does not determine structural suitability.")
    rows = {"Field": [
        "Member", "Section (d x bf x tw x tf, mm)", "Plate (X x Y x t, mm)",
        "Bolt count", "A.BOLT size", "Hole dia (mm)", "PJ (mm)",
        "Weld size (mm, as called out)", "Pedestal min plan (X x Y, mm)",
    ]}
    for m in compare_marks:
        r = get_record_by_mark(m)
        d, bf, tw, tf = r["section_mm"]
        px, py = r["plate_xy_mm"]
        pdx, pdy = r["pedestal_xy_mm"]
        rows[m] = [
            r["member"], f"{d} x {bf} x {tw} x {tf}", f"{px} x {py} x {r['plate_thickness_mm']}",
            r["bolt_count"], r["bolt_size"], r["hole_diameter_mm"], r["pj_mm"],
            r["weld_size_mm"], f"{pdx} x {pdy}",
        ]
    st.table(rows)

with st.expander("Drawing notes"):
    st.markdown(
        "- Pedestal size shown is minimum.\n"
        "- Plate washer detail is supplied by the steel fabricator."
    )

st.caption(DISCLAIMER)