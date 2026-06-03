import csv
from collections import defaultdict

f = r"C:\EPRI_Ckt7_DER_Project\Simulation_Results\all_results.csv"
rfi_cols = [f"RFI{i}" for i in range(1, 21)]

# Load all converged rows
rows = []
with open(f) as fh:
    for row in csv.DictReader(fh):
        if row['converged'] == 'True':
            rows.append(row)

print(f"Total converged rows: {len(rows)}")
scenarios = sorted(set(r['scenario_label'] for r in rows))
print(f"Scenarios available: {scenarios}\n")

# For each scenario: avg max-RFI-current per fault, broken down by fault type
print("=== Avg Peak RFI Current by Scenario and Fault Type ===")
print(f"{'Scenario':<14} {'N_DGs':>5} | {'SLG_A':>9} {'LL_AB':>9} {'3PH':>9} | {'Overall':>9}")
print("-" * 65)

scenario_ndg = {r['scenario_label']: int(r['n_dg_buses']) for r in rows}

for sc in scenarios:
    sc_rows = [r for r in rows if r['scenario_label'] == sc]
    ndg = scenario_ndg[sc]
    by_type = defaultdict(list)
    for r in sc_rows:
        vals = [float(r[c]) for c in rfi_cols if r[c]]
        if vals:
            by_type[r['fault_type']].append(max(vals))

    avg = lambda lst: sum(lst)/len(lst) if lst else 0
    slg  = avg(by_type.get('SLG_A', []))
    ll   = avg(by_type.get('LL_AB', []))
    tph  = avg(by_type.get('3PH',   []))
    all_vals = by_type['SLG_A'] + by_type['LL_AB'] + by_type['3PH']
    overall  = avg(all_vals)
    print(f"{sc:<14} {ndg:>5} | {slg:>9.1f} {ll:>9.1f} {tph:>9.1f} | {overall:>9.1f}")

# Now look at individual RFI monitors — do any shift significantly?
print("\n=== Avg Current per RFI Monitor by Scenario (all fault types combined) ===")
header = f"{'RFI':<6}" + "".join(f"{sc:>10}" for sc in scenarios)
print(header)
print("-" * (6 + 10*len(scenarios)))

for rfi in rfi_cols:
    row_str = f"{rfi:<6}"
    for sc in scenarios:
        sc_rows = [r for r in rows if r['scenario_label'] == sc and r[rfi]]
        vals = [float(r[rfi]) for r in sc_rows if r[rfi]]
        avg = sum(vals)/len(vals) if vals else 0
        row_str += f"{avg:>10.1f}"
    print(row_str)

# Delta between lowest and highest penetration
print("\n=== Delta: highest vs lowest penetration scenario (per RFI, all fault types) ===")
low_sc  = scenarios[0]
high_sc = scenarios[-1]
print(f"Comparing {low_sc} ({scenario_ndg[low_sc]} DGs) vs {high_sc} ({scenario_ndg[high_sc]} DGs)\n")
print(f"{'RFI':<6} {'Low':>9} {'High':>9} {'Delta':>9} {'Delta%':>8}")
print("-" * 45)
for rfi in rfi_cols:
    lo_vals = [float(r[rfi]) for r in rows if r['scenario_label']==low_sc and r[rfi]]
    hi_vals = [float(r[rfi]) for r in rows if r['scenario_label']==high_sc and r[rfi]]
    lo_avg = sum(lo_vals)/len(lo_vals) if lo_vals else 0
    hi_avg = sum(hi_vals)/len(hi_vals) if hi_vals else 0
    delta  = hi_avg - lo_avg
    dpct   = 100*delta/lo_avg if lo_avg else 0
    flag   = " <--" if abs(dpct) > 10 else ""
    print(f"{rfi:<6} {lo_avg:>9.1f} {hi_avg:>9.1f} {delta:>+9.1f} {dpct:>7.1f}%{flag}")
