from openstaadpy import os_analytical

# -------------------------------------------------
# 1️⃣ Connect to STAAD
# -------------------------------------------------
staad = os_analytical.connect()

if not staad:
    raise Exception("❌ STAAD is not open.")

print("✅ Connected to STAAD")

# -------------------------------------------------
# 2️⃣ Create / Activate Load Case
# -------------------------------------------------
load_case_number = 1
load_case_title = "DL + 10kN/m"

existing_cases = staad.Load.GetPrimaryLoadCaseNumbers()

if load_case_number not in existing_cases:
    staad.Load.CreateNewPrimaryLoad(load_case_number, load_case_title)
    print(f"✅ Created Load Case {load_case_number}")
else:
    print(f"ℹ Load Case {load_case_number} already exists")

# Set Active Load Case
staad.Load.SetLoadActive(load_case_number)
print(f"✅ Load Case {load_case_number} is now active")

# -------------------------------------------------
# 3️⃣ Add Selfweight (Global Y, Downward)
# -------------------------------------------------
# Direction: 1=X, 2=Y, 3=Z
# Downward → negative factor

selfweight_result = staad.Load.AddSelfWeightInXYZ(2, -1.0)

if selfweight_result:
    print("✅ Selfweight added successfully")
else:
    print("❌ Failed to add selfweight")

# -------------------------------------------------
# 4️⃣ Get All Beams
# -------------------------------------------------
beam_list = staad.Geometry.GetBeamList()

if not beam_list:
    raise Exception("❌ No beams found in model.")

print(f"✅ Total Beams Found: {len(beam_list)}")

# -------------------------------------------------
# 5️⃣ Add 10 kN/m UDL to ALL Beams (Batch Method)
# -------------------------------------------------
# Parameters:
# AddMemberUniformForce(member_list, direction, force, d1, d2, load_case)

udl_result = staad.Load.AddMemberUniformForce(
    beam_list,   # List of members
    2,           # Global Y direction
    -10.0,       # 10 kN/m downward
    0,           # Start distance
    0,           # End distance (0 = full length)
    load_case_number
)

if udl_result:
    print("✅ 10 kN/m UDL applied to all beams successfully")
else:
    print("❌ Failed to apply UDL")

print("🎯 Load application completed.")