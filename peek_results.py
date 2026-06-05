import csv
from collections import defaultdict, Counter

f = r"C:\EPRI_Ckt7_DER_Project\Simulation_Results\all_results.csv"

rows = []
with open(f) as fh:
    reader = csv.DictReader(fh)
    for row in reader:
        rows.append(row)

print(f"Rows so far: {len(rows)}")

# Convergence
converged = [r for r in rows if r['converged'] == 'True']
failed    = [r for r in rows if r['converged'] == 'False']
print(f"Converged: {len(converged)}  |  Failed: {len(failed)}")

# Scenarios covered
scenarios = sorted(set(r['scenario_label'] for r in rows))
print(f"Scenarios covered: {scenarios}")

# Fault type breakdown
ft = Counter(r['fault_type'] for r in converged)
print(f"\nFault types (converged): {dict(ft)}")

# Zone breakdown
zc = Counter(r['zone'] for r in converged)
print(f"Zones hit: {dict(sorted(zc.items(), key=lambda x: int(x[0])))}")

# RFI columns
rfi_cols = [f"RFI{i}" for i in range(1, 21)]

# Per-fault-type: avg max RFI current
print("\nAvg max RFI current by fault type (across all RFIs):")
by_type = defaultdict(list)
for r in converged:
    vals = []
    for col in rfi_cols:
        try:
            vals.append(float(r[col]))
        except:
            pass
    if vals:
        by_type[r['fault_type']].append(max(vals))

for ft_name, vals in sorted(by_type.items()):
    print(f"  {ft_name:8s}: avg max RFI = {sum(vals)/len(vals):.1f} A  (min={min(vals):.1f}, max={max(vals):.1f})")

# Highest current events
print("\nTop 5 highest RFI readings so far:")
top = []
for r in converged:
    for col in rfi_cols:
        try:
            v = float(r[col])
            top.append((v, col, r['fault_type'], r['zone'], r['scenario_label']))
        except:
            pass
top.sort(reverse=True)
for v, rfi, ft, z, sc in top[:5]:
    print(f"  {rfi} = {v:.1f} A  | {ft} | Zone {z} | {sc}")
