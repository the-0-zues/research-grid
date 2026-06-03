import re
import pandas as pd
from pathlib import Path

# ------------------------------------------------------------
# Input and output paths
# ------------------------------------------------------------
project_folder = Path(r"C:\EPRI_Ckt7_DER_Project")

loads_file = Path(
  "C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7\Loads_ckt7.dss"
)
output_file = project_folder / "smart_meter_locations.csv"

# ------------------------------------------------------------
# Helper function to extract OpenDSS properties
# ------------------------------------------------------------
def get_property(line, property_name):
    pattern = rf"\b{property_name}=([^\s]+)"
    match = re.search(pattern, line, flags=re.IGNORECASE)
    return match.group(1) if match else None

rows = []

with open(loads_file, "r") as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("!"):
            continue

        load_match = re.search(r"New\s+Load\.([^\s]+)", line, flags=re.IGNORECASE)

        if not load_match:
            continue

        load_name = load_match.group(1)
        bus1 = get_property(line, "Bus1")
        phases = get_property(line, "Phases")
        kv = get_property(line, "kV")
        kw = get_property(line, "kW")
        pf = get_property(line, "pf")
        xfkva = get_property(line, "xfkVA")

        # Base bus removes phase suffix, for example:
        # S1X_1000663.1 -> S1X_1000663
        if bus1 is not None:
            base_bus = bus1.split(".")[0]
        else:
            base_bus = None

        rows.append({
            "SmartMeter_ID": f"SM_{len(rows) + 1}",
            "Load_Name": load_name,
            "Bus1": bus1,
            "Base_Bus": base_bus,
            "Phases": phases,
            "kV": kv,
            "kW": kw,
            "pf": pf,
            "xfkVA": xfkva
        })

smart_meters = pd.DataFrame(rows)

smart_meters.to_csv(output_file, index=False)

print("Smart meter placement file created.")
print(f"Saved to: {output_file}")
print()
print(f"Total smart meters: {len(smart_meters)}")
print(f"Unique Bus1 entries: {smart_meters['Bus1'].nunique()}")
print(f"Unique base LV buses: {smart_meters['Base_Bus'].nunique()}")
print()
print(smart_meters.head(10))