"""
Split the 100MB all_results.csv into manageable files:
1. rfi_results.csv       - scenario/fault metadata + 20 RFI columns only
2. sm_results.csv        - scenario/fault metadata + 867 SM voltage columns only
3. summary_by_scenario.csv - aggregated stats per scenario (small, easy to open)
4. summary_by_zone.csv   - aggregated stats per zone x scenario
"""
import csv, os
from collections import defaultdict

IN_FILE  = r"C:\EPRI_Ckt7_DER_Project\Simulation_Results\all_results.csv"
OUT_DIR  = r"C:\EPRI_Ckt7_DER_Project\Simulation_Results"

META_COLS = ["scenario_id","scenario_label","n_dg_buses",
             "fault_id","zone","fault_type","fault_line","fault_bus","converged"]
RFI_COLS  = [f"RFI{i}" for i in range(1, 21)]

print("Reading full results...")
rows = []
sm_cols = []
with open(IN_FILE, newline="") as f:
    reader = csv.DictReader(f)
    all_cols = reader.fieldnames
    sm_cols  = [c for c in all_cols if c.startswith("SM_")]
    for row in reader:
        rows.append(row)
print(f"  {len(rows)} rows | {len(sm_cols)} SM columns")

# ── 1. RFI-only results ──
print("Writing rfi_results.csv...")
with open(os.path.join(OUT_DIR, "rfi_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=META_COLS + RFI_COLS, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

# ── 2. SM-only results ──
print("Writing sm_results.csv...")
with open(os.path.join(OUT_DIR, "sm_results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=META_COLS + sm_cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

# ── 3. Summary by scenario ──
print("Writing summary_by_scenario.csv...")
sc_data = defaultdict(lambda: defaultdict(list))
for row in rows:
    sc  = row["scenario_label"]
    ndg = row["n_dg_buses"]
    ft  = row["fault_type"]
    if row["converged"] != "True":
        continue
    rfi_vals = [float(row[r]) for r in RFI_COLS if row[r]]
    sm_vals  = [float(row[s]) for s in sm_cols if row[s]]
    sc_data[sc]["ndg"]     = ndg
    sc_data[sc]["max_rfi"].append(max(rfi_vals) if rfi_vals else 0)
    sc_data[sc]["avg_rfi"].append(sum(rfi_vals)/len(rfi_vals) if rfi_vals else 0)
    sc_data[sc]["sm_outages_05"].append(sum(1 for v in sm_vals if v < 0.5))
    sc_data[sc]["sm_outages_08"].append(sum(1 for v in sm_vals if v < 0.8))
    sc_data[sc][f"ft_{ft}"].append(max(rfi_vals) if rfi_vals else 0)
    for rfi in RFI_COLS:
        if row[rfi]:
            sc_data[sc][f"avg_{rfi}"].append(float(row[rfi]))

sc_summary_cols = (
    ["scenario_label","n_dg_buses","n_faults",
     "avg_max_rfi_A","min_max_rfi_A","max_max_rfi_A",
     "avg_rfi_all_A",
     "avg_sm_outages_below_0.5pu","avg_sm_outages_below_0.8pu",
     "avg_peak_SLG_A","avg_peak_LL_AB","avg_peak_3PH"]
    + [f"avg_{r}" for r in RFI_COLS]
)

avg = lambda lst: round(sum(lst)/len(lst), 2) if lst else 0

scenarios_sorted = sorted(sc_data.keys(), key=lambda x: int(x.split("_")[1].replace("pct","")))
with open(os.path.join(OUT_DIR, "summary_by_scenario.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=sc_summary_cols)
    w.writeheader()
    for sc in scenarios_sorted:
        d = sc_data[sc]
        w.writerow({
            "scenario_label":               sc,
            "n_dg_buses":                   d["ndg"],
            "n_faults":                     len(d["max_rfi"]),
            "avg_max_rfi_A":                avg(d["max_rfi"]),
            "min_max_rfi_A":                round(min(d["max_rfi"]),2),
            "max_max_rfi_A":                round(max(d["max_rfi"]),2),
            "avg_rfi_all_A":                avg(d["avg_rfi"]),
            "avg_sm_outages_below_0.5pu":   avg(d["sm_outages_05"]),
            "avg_sm_outages_below_0.8pu":   avg(d["sm_outages_08"]),
            "avg_peak_SLG_A":               avg(d.get("ft_SLG_A",[])),
            "avg_peak_LL_AB":               avg(d.get("ft_LL_AB",[])),
            "avg_peak_3PH":                 avg(d.get("ft_3PH",[])),
            **{f"avg_{r}": avg(d.get(f"avg_{r}",[])) for r in RFI_COLS},
        })

# ── 4. Summary by zone x scenario ──
print("Writing summary_by_zone_scenario.csv...")
zone_sc_data = defaultdict(lambda: defaultdict(list))
for row in rows:
    if row["converged"] != "True":
        continue
    key = (row["zone"], row["scenario_label"], row["n_dg_buses"])
    rfi_vals = [float(row[r]) for r in RFI_COLS if row[r]]
    sm_vals  = [float(row[s]) for s in sm_cols if row[s]]
    zone_sc_data[key]["max_rfi"].append(max(rfi_vals) if rfi_vals else 0)
    zone_sc_data[key]["sm_outages"].append(sum(1 for v in sm_vals if v < 0.5))

zone_cols = ["zone","scenario_label","n_dg_buses","n_faults",
             "avg_max_rfi_A","avg_sm_outages_below_0.5pu"]
with open(os.path.join(OUT_DIR, "summary_by_zone_scenario.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=zone_cols)
    w.writeheader()
    for (zone, sc, ndg), d in sorted(zone_sc_data.items(), key=lambda x: (int(x[0][0]), x[0][1])):
        w.writerow({
            "zone": zone, "scenario_label": sc, "n_dg_buses": ndg,
            "n_faults":                   len(d["max_rfi"]),
            "avg_max_rfi_A":              avg(d["max_rfi"]),
            "avg_sm_outages_below_0.5pu": avg(d["sm_outages"]),
        })

print("\nDone. Files written:")
for fn in ["rfi_results.csv","sm_results.csv","summary_by_scenario.csv","summary_by_zone_scenario.csv"]:
    path = os.path.join(OUT_DIR, fn)
    size = os.path.getsize(path) / 1024
    print(f"  {fn:40s} {size:8.0f} KB")
