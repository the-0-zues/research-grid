"""
dgsweep_normal_raw.py <n_dg>
============================
No-fault (clean) raw for the DG sweep: 500 samples, n_dg Cat-3520 DGs
dispatching 1600 kW each (Generator mode; no fault so no source swap).
Feeder loads scaled by L1xL2; ~71 MW substation lump held fixed.
Out: PMU_dataset_v2/DGsweep/{n}DG/Clean/raw/results.csv  (pre == flt)
"""
import os, sys, csv
import numpy as np
import opendssdirect as dss
import advanced_pmu_fault_simulation as fs
import dgsweep

N_DG = int(sys.argv[1]) if len(sys.argv) > 1 else 0
N_SAMPLES = 500
OUT = rf"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\PMU_dataset_v2\DGsweep\{N_DG}DG\Clean"
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
META = ["sample_id","fault_type","fault_line","fault_frac","zone","impedance_type",
        "r_ground","r_phase","load_L1","cap_CP_NR_613","cap_CP_85W_900",
        "chain_attach_km","fault_on_chain","converged"]

print(f"DG SWEEP clean raw: {N_DG} DG(s), {N_SAMPLES} samples")
dss.Basic.Start(0)
dss.Command(f'Redirect "{fs.MASTER}"')
dss.Command("Set VoltageBases=[115, 12.47, 0.48]"); dss.Command("CalcVoltageBases"); dss.Command("Solve")
load_list = fs.capture_base_loads()
feeder_loads, lump_loads = fs.partition_loads(load_list)
fs.set_event_loads(lump_loads, 1.0, np.ones(len(lump_loads)))
dss.Command("set loadmult=1.0"); fs.disable_capcontrols()
dgsweep.add_dgs(N_DG); dgsweep.dg_normal_mode(N_DG)
dss.Command("set controlmode=static"); dss.Command("set maxcontroliter=100"); dss.Command("Solve")
print(f"setup done ({len(feeder_loads)} feeder + {len(lump_loads)} lump), {N_DG} DGs, "
      f"converged={dss.Solution.Converged()}")

pmu_labels = [l for l, _ in fs.PMU_LINES]
sm_list = fs.load_smart_meters(); sm_ids = [s[0] for s in sm_list]
raw_cols = fs._raw_cols(pmu_labels, sm_ids)
rng_scn = np.random.default_rng(fs.DG_SEED + 1)
n_conv = 0
with open(os.path.join(OUT, "raw", "results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=META + raw_cols); w.writeheader()
    for i in range(N_SAMPLES):
        l1 = float(rng_scn.uniform(fs.L1_MIN, fs.L1_MAX))
        l2 = rng_scn.uniform(fs.L2_MIN, fs.L2_MAX, size=len(feeder_loads))
        fs.set_event_loads(feeder_loads, l1, l2); caps = fs.set_cap_states(rng_scn, l1)
        dss.Command("set controlmode=static"); dss.Command("set maxcontroliter=100"); dss.Command("Solve")
        ok = dss.Solution.Converged()
        state = fs.read_state(sm_list) if ok else None
        row = {"sample_id":f"N{i+1:04d}","fault_type":"no_fault","fault_line":"","fault_frac":"",
               "zone":0,"impedance_type":"","r_ground":"","r_phase":"","load_L1":round(l1,6),
               "cap_CP_NR_613":caps.get("CP-NR-613",False),"cap_CP_85W_900":caps.get("CP-85W-900",False),
               "chain_attach_km":"","fault_on_chain":"","converged":ok}
        if ok:
            for k, v in state.items(): row[f"pre_{k}"] = v; row[f"flt_{k}"] = v
            n_conv += 1
        else:
            row.update({c: "" for c in raw_cols})
        w.writerow(row); f.flush()
        if (i+1) % 100 == 0 or (i+1) == N_SAMPLES:
            print(f"  {i+1}/{N_SAMPLES} converged={n_conv}", flush=True)
print(f"DONE {N_DG}DG clean -> {OUT}")
