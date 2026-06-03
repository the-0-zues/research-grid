import csv
with open(r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv") as f:
    rows = list(csv.DictReader(f))
print(f"Total smart meters: {len(rows)}")
phases = {}
for r in rows:
    p = r['Phases']
    phases[p] = phases.get(p, 0) + 1
print("By phase count:", phases)
