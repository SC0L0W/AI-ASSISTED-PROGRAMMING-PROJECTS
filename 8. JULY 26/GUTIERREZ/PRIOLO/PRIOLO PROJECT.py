# This script requires an empty model opened in STAAD.Pro.
# Warehouse geometry:
#   Width = 60 ft, Length = 100 ft, Frame spacing = 25 ft
#   Eave height = 20 ft, Ridge height = 28 ft
# Global axes: X = building width, Y = vertical, Z = building length

from openstaadpy import os_analytical

staad = os_analytical.connect()
geo = staad.Geometry
prop = staad.Property
sup = staad.Support
load = staad.Load

# Units: Feet and Kips
staad.SetInputUnits(1, 0)
staad.SaveModel(True)

# -------------------------------------------------------------------
# Building parameters
# -------------------------------------------------------------------
WIDTH = 60.0
LENGTH = 100.0
FRAME_SPACING = 25.0
EAVE_HEIGHT = 20.0
RIDGE_HEIGHT = 28.0

frame_positions = [0.0, 25.0, 50.0, 75.0, 100.0]

# Roof loads in kips/sq.ft. Adjust to match your project criteria.
ROOF_DEAD_LOAD = 0.10
ROOF_LIVE_LOAD = 0.20
WIND_PRESSURE = 0.03

half_span = WIDTH / 2.0
rafter_length = (half_span**2 + (RIDGE_HEIGHT - EAVE_HEIGHT)**2) ** 0.5
slope_factor = half_span / rafter_length

# -------------------------------------------------------------------
# Nodes: five nodes per portal frame
# 1 = left base, 2 = left eave, 3 = ridge, 4 = right eave, 5 = right base
# -------------------------------------------------------------------
node_coords = {}
frame_nodes = {}

for frame_index, z in enumerate(frame_positions):
    start_node = frame_index * 5 + 1

    left_base = start_node
    left_eave = start_node + 1
    ridge = start_node + 2
    right_eave = start_node + 3
    right_base = start_node + 4

    frame_nodes[frame_index] = {
        "left_base": left_base,
        "left_eave": left_eave,
        "ridge": ridge,
        "right_eave": right_eave,
        "right_base": right_base,
    }

    node_coords[left_base] = (0.0, 0.0, z)
    node_coords[left_eave] = (0.0, EAVE_HEIGHT, z)
    node_coords[ridge] = (WIDTH / 2.0, RIDGE_HEIGHT, z)
    node_coords[right_eave] = (WIDTH, EAVE_HEIGHT, z)
    node_coords[right_base] = (WIDTH, 0.0, z)

for node_id, (x, y, z) in node_coords.items():
    geo.CreateNode(node_id, x, y, z)

# -------------------------------------------------------------------
# Members
# -------------------------------------------------------------------
member_incidence = {}
portal_columns = []
portal_rafters = []
longitudinal_members = []
bracing_members = []
member_id = 1

# Portal frame members
for frame_index in range(len(frame_positions)):
    n = frame_nodes[frame_index]

    # Columns
    member_incidence[member_id] = (n["left_base"], n["left_eave"])
    portal_columns.append(member_id)
    member_id += 1

    member_incidence[member_id] = (n["right_base"], n["right_eave"])
    portal_columns.append(member_id)
    member_id += 1

    # Rafters
    member_incidence[member_id] = (n["left_eave"], n["ridge"])
    portal_rafters.append(member_id)
    member_id += 1

    member_incidence[member_id] = (n["ridge"], n["right_eave"])
    portal_rafters.append(member_id)
    member_id += 1

# Longitudinal eave and ridge members between portal frames
for frame_index in range(len(frame_positions) - 1):
    current = frame_nodes[frame_index]
    next_frame = frame_nodes[frame_index + 1]

    member_incidence[member_id] = (
        current["left_eave"],
        next_frame["left_eave"]
    )
    longitudinal_members.append(member_id)
    member_id += 1

    member_incidence[member_id] = (
        current["ridge"],
        next_frame["ridge"]
    )
    longitudinal_members.append(member_id)
    member_id += 1

    member_incidence[member_id] = (
        current["right_eave"],
        next_frame["right_eave"]
    )
    longitudinal_members.append(member_id)
    member_id += 1

# Sidewall X-bracing in the first bay
first_frame = frame_nodes[0]
second_frame = frame_nodes[1]

member_incidence[member_id] = (
    first_frame["left_base"],
    second_frame["left_eave"]
)
bracing_members.append(member_id)
member_id += 1

member_incidence[member_id] = (
    first_frame["left_eave"],
    second_frame["left_base"]
)
bracing_members.append(member_id)
member_id += 1

member_incidence[member_id] = (
    first_frame["right_base"],
    second_frame["right_eave"]
)
bracing_members.append(member_id)
member_id += 1

member_incidence[member_id] = (
    first_frame["right_eave"],
    second_frame["right_base"]
)
bracing_members.append(member_id)
member_id += 1

for beam_id, (start_node, end_node) in member_incidence.items():
    geo.CreateBeam(beam_id, start_node, end_node)

# -------------------------------------------------------------------
# Steel properties
# Country code 1 = American steel table.
# Confirm these shapes are available in your STAAD.Pro installation.
# -------------------------------------------------------------------
cc = 1

column_property = prop.CreateBeamPropertyFromTable(
    cc, "W12X40", 0, 0.0, 0.0
)
rafter_property = prop.CreateBeamPropertyFromTable(
    cc, "W18X50", 0, 0.0, 0.0
)
longitudinal_property = prop.CreateBeamPropertyFromTable(
    cc, "W10X30", 0, 0.0, 0.0
)
brace_property = prop.CreateAnglePropertyFromTable(
    cc, "L40404", 0, 0.0
)

prop.AssignBeamProperty(portal_columns, column_property)
prop.AssignBeamProperty(portal_rafters, rafter_property)
prop.AssignBeamProperty(longitudinal_members, longitudinal_property)
prop.AssignBeamProperty(bracing_members, brace_property)

all_members = list(member_incidence.keys())
prop.AssignMaterialToMember("STEEL", all_members)

# Bracing members act as tension/compression truss members.
truss_spec = prop.CreateMemberTrussSpec()
prop.AssignMemberSpecToBeam(bracing_members, truss_spec)

# -------------------------------------------------------------------
# Supports: pinned bases at every portal frame column
# -------------------------------------------------------------------
# --- Pinned support symbols at the base of every warehouse column ---
pinned_support = sup.CreateSupportPinned()

column_base_nodes = []
for frame_index in range(len(frame_positions)):
    frame = frame_nodes[frame_index]
    column_base_nodes.extend([
        frame["left_base"],
        frame["right_base"],
    ])

sup.AssignSupportToNode(column_base_nodes, pinned_support)

# Save so STAAD.Pro updates the model display
staad.SaveModel(True)
# -------------------------------------------------------------------
# Load case 1: Dead load
# Selfweight plus assumed metal roof/deck/cladding allowance.
# -------------------------------------------------------------------
dead_case = load.CreateNewPrimaryLoadEx2("DEAD LOAD", 0, 1)
load.SetLoadActive(dead_case)
load.AddSelfWeightInXYZ(2, -1.0)

for frame_index in range(len(frame_positions)):
    # End frames take half tributary width; interior frames take full width.
    tributary_width = (
        FRAME_SPACING / 2.0
        if frame_index in [0, len(frame_positions) - 1]
        else FRAME_SPACING
    )

    roof_udl = ROOF_DEAD_LOAD * tributary_width * slope_factor
    rafter_1 = portal_rafters[frame_index * 2]
    rafter_2 = portal_rafters[frame_index * 2 + 1]

    load.AddMemberUniformForce([rafter_1, rafter_2], 2, -roof_udl, 0.0, 0.0, 0.0)

# -------------------------------------------------------------------
# Load case 2: Roof live load
# -------------------------------------------------------------------
live_case = load.CreateNewPrimaryLoadEx2("ROOF LIVE LOAD", 0, 2)
load.SetLoadActive(live_case)

for frame_index in range(len(frame_positions)):
    tributary_width = (
        FRAME_SPACING / 2.0
        if frame_index in [0, len(frame_positions) - 1]
        else FRAME_SPACING
    )

    roof_udl = ROOF_LIVE_LOAD * tributary_width * slope_factor
    rafter_1 = portal_rafters[frame_index * 2]
    rafter_2 = portal_rafters[frame_index * 2 + 1]

    load.AddMemberUniformForce([rafter_1, rafter_2], 2, -roof_udl, 0.0, 0.0, 0.0)

# -------------------------------------------------------------------
# Load case 3: Wind from left, Global X direction
# This is a simple preliminary frame load, not a code wind calculation.
# -------------------------------------------------------------------
wind_case = load.CreateNewPrimaryLoadEx2("WIND FROM LEFT", 3, 3)
load.SetLoadActive(wind_case)

for frame_index in range(len(frame_positions)):
    tributary_width = (
        FRAME_SPACING / 2.0
        if frame_index in [0, len(frame_positions) - 1]
        else FRAME_SPACING
    )

    wind_udl = WIND_PRESSURE * tributary_width

    left_column = portal_columns[frame_index * 2]
    right_column = portal_columns[frame_index * 2 + 1]

    # Direction code 4 = Global X, following the convention in your example.
    load.AddMemberUniformForce([left_column, right_column], 4, wind_udl, 0.0, 0.0, 0.0)

# -------------------------------------------------------------------
# Load combinations
# -------------------------------------------------------------------
combination_1 = load.CreateNewLoadCombination("1.4 DEAD LOAD", 4)
load.AddLoadAndFactorToCombination(combination_1, dead_case, 1.4)

combination_2 = load.CreateNewLoadCombination("1.2 DEAD + 1.6 ROOF LIVE", 4)
load.AddLoadAndFactorToCombination(combination_2, dead_case, 1.2)
load.AddLoadAndFactorToCombination(combination_2, live_case, 1.6)

combination_3 = load.CreateNewLoadCombination("1.2 DEAD + 1.0 LIVE + 1.0 WIND", 4)
load.AddLoadAndFactorToCombination(combination_3, dead_case, 1.2)
load.AddLoadAndFactorToCombination(combination_3, live_case, 1.0)
load.AddLoadAndFactorToCombination(combination_3, wind_case, 1.0)

combination_4 = load.CreateNewLoadCombination("0.9 DEAD + 1.0 WIND", 4)
load.AddLoadAndFactorToCombination(combination_4, dead_case, 0.9)
load.AddLoadAndFactorToCombination(combination_4, wind_case, 1.0)

# Save and analyze
staad.SaveModel(True)
staad.Command.PerformAnalysis(0)

print("Steel warehouse model created and analyzed.")
print(f"Nodes: {len(node_coords)}")
print(f"Members: {len(member_incidence)}")
print(f"Portal frames: {len(frame_positions)}")