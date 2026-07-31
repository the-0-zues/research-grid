"""
dgsweep_fault_raw.py <n_dg> [max_events]
========================================
Mid-line fault raw for the DG sweep. Same validated line-split mechanism as
nodg_fault_raw_lines.py, plus:
  * n_dg Cat-3520 DGs (dgsweep.add_dgs) on the 3 biggest customers
  * bolted-inclusive fault mix (dgsweep.build_fault_list_bolted)
  * per event: pre-fault solve with DG as Generator (dispatch), then swap to
    Vsource behind X'' for the during-fault solve (real fault contribution)
Feeder loads scaled by L1xL2; the ~71 MW substation lump held fixed.

Out: PMU_dataset_v2/DGsweep/{n}DG/Faulty/{raw/results.csv, lateral_currents.csv}
"""
import os, sys, csv
import numpy as np
from collections import defaultdict, deque
import opendssdirect as dss
import advanced_pmu_fault_simulation as fs
import dgsweep

N_DG = int(sys.argv[1]) if len(sys.argv) > 1 else 0
MAXEV = int(sys.argv[2]) if len(sys.argv) > 2 else None
OUT = rf"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\PMU_dataset_v2\DGsweep\{N_DG}DG\Faulty"
FUSECSV = r"C:\EPRI_Ckt7_DER_Project\fuse_sizing_nodg.csv"
UNIT = {0:"none",1:"mi",2:"kft",3:"km",4:"m",5:"ft",6:"in",7:"cm"}
FRAC_LO, FRAC_HI = 0.02, 0.98
os.makedirs(os.path.join(OUT, "raw"), exist_ok=True)
with open(FUSECSV) as f:
    FUSED = [r["line"].upper() for r in csv.DictReader(f)]

print("=" * 60); print(f"DG SWEEP fault raw: {N_DG} DG(s)"); print("=" * 60)
dss.Basic.Start(0)
dss.Command(f'Redirect "{fs.MASTER}"')
dss.Command("Set VoltageBases=[115, 12.47, 0.48]"); dss.Command("CalcVoltageBases")
dss.Command("Solve")

meta, adj = {}, defaultdict(list)
i = dss.Lines.First()
while i > 0:
    nm = dss.Lines.Name().upper(); dss.Lines.Name(nm)
    d = dict(lc=dss.Lines.LineCode(), units=dss.Lines.Units(), ph=dss.Lines.Phases(),
             L=dss.Lines.Length(), b1=dss.Lines.Bus1(), b2=dss.Lines.Bus2())
    dss.Circuit.SetActiveElement(f"Line.{nm}"); d["en"] = dss.CktElement.Enabled()
    meta[nm] = d
    if d["en"]:
        a, b = d["b1"].split(".")[0].upper(), d["b2"].split(".")[0].upper()
        adj[a].append((b, nm)); adj[b].append((a, nm))
    i = dss.Lines.Next()

mv_buses = fs.get_3phase_mv_buses(); mv_set = set(mv_buses)
adj_mv, _ = fs.build_mv_adjacency(mv_set); bus_zone = fs.build_bus_zone_map(adj_mv, mv_set)
CAND = [nm for nm, d in meta.items() if d["en"] and d["ph"] == 3 and d["L"] > 0 and d["lc"]
        and d["b1"].split(".")[0].upper() in mv_set and d["b2"].split(".")[0].upper() in mv_set]
LENS = np.array([meta[n]["L"] for n in CAND]); PROB = LENS / LENS.sum()

dss.Meters.First(); elem = dss.Meters.MeteredElement(); term = dss.Meters.MeteredTerminal()
dss.Circuit.SetActiveElement(elem); SUB = dss.CktElement.BusNames()[term-1].split(".")[0].upper()
parent = {SUB: None}; q = deque([SUB])
while q:
    x = q.popleft()
    for nb, nm in adj[x]:
        if nb not in parent: parent[nb] = (x, nm); q.append(nb)
def bus1_of(l):
    dss.Circuit.SetActiveElement(f"Line.{dict(fs.PMU_LINES)[l]}")
    return dss.CktElement.BusNames()[0].split(".")[0].upper()
MP = {l: bus1_of(l) for l in ("PMU2","PMU4","PMU8","PMU11")}
def bfs_path(a, b):
    prev = {a: None}; qq = deque([a])
    while qq:
        x = qq.popleft()
        if x == b: break
        for nb, nm in adj[x]:
            if nb not in prev: prev[nb] = (x, nm); qq.append(nb)
    segs = []; x = b
    while prev[x] is not None: p, nm = prev[x]; segs.append((p, nm, x)); x = p
    return list(reversed(segs))
km_at = {MP["PMU2"]: 0.0}; k = 0.0; chain_line_info = {}
for a, nm, b in bfs_path(MP["PMU2"], MP["PMU11"]):
    chain_line_info[nm] = (a, k, meta[nm]["L"]); k += meta[nm]["L"]/1000.0; km_at[b] = k
def upstream_end(nm):
    d = meta[nm]; a, b = d["b1"].split(".")[0].upper(), d["b2"].split(".")[0].upper()
    if parent.get(b) and parent[b][0] == a: return a, b
    if parent.get(a) and parent[a][0] == b: return b, a
    da = 0; x = a
    while parent.get(x): x = parent[x][0]; da += 1
    db = 0; x = b
    while parent.get(x): x = parent[x][0]; db += 1
    return (a, b) if da <= db else (b, a)
def chain_attach(nm, frac):
    d = meta[nm]; b1 = d["b1"].split(".")[0].upper()
    if nm in chain_line_info:
        bus_a, km_a, L = chain_line_info[nm]
        along = frac if b1 == bus_a else (1.0 - frac)
        return km_a + along * L / 1000.0, 1
    up, _ = upstream_end(nm); x = up
    while x is not None and x not in km_at:
        pr = parent.get(x); x = pr[0] if pr else None
    return (np.nan, 0) if x is None else (km_at[x], 0)

base_faults = dgsweep.build_fault_list_bolted(mv_buses, bus_zone)
rng_loc = np.random.default_rng(fs.FAULT_SEED + 77)
pick = rng_loc.choice(len(CAND), size=len(base_faults), p=PROB)
fracs = rng_loc.uniform(FRAC_LO, FRAC_HI, size=len(base_faults))
faults = []
for j, fl in enumerate(base_faults):
    nm = CAND[pick[j]]; frac = float(fracs[j]); akm, on = chain_attach(nm, frac)
    _, dn = upstream_end(nm)
    faults.append({**fl, "fault_line": nm, "fault_frac": frac,
                   "zone": bus_zone.get(dn, 0), "chain_attach_km": akm, "on_chain": on})
if MAXEV: faults = faults[:MAXEV]
print(f"faults: {len(faults)}  on-chain: {sum(f['on_chain'] for f in faults)}")

# setup: feeder-only load scaling, DGs, fault segments
load_list = fs.capture_base_loads()
feeder_loads, lump_loads = fs.partition_loads(load_list)
fs.set_event_loads(lump_loads, 1.0, np.ones(len(lump_loads)))
dss.Command("set loadmult=1.0"); fs.disable_capcontrols()
dgsweep.add_dgs(N_DG)
m0 = meta[CAND[0]]
dss.Command(f"New Line.FLTSEG_A bus1={m0['b1']} bus2=FLTPT.1.2.3 linecode={m0['lc']} "
            f"length=0.001 units={UNIT[m0['units']]} phases=3 enabled=false")
dss.Command(f"New Line.FLTSEG_B bus1=FLTPT.1.2.3 bus2={m0['b2']} linecode={m0['lc']} "
            f"length=0.001 units={UNIT[m0['units']]} phases=3 enabled=false")
fs.init_fault_slots(mv_buses[0])
dss.Command("set controlmode=static"); dss.Command("set maxcontroliter=100"); dss.Command("Solve")
print(f"setup done ({len(feeder_loads)} feeder + {len(lump_loads)} lump loads), {N_DG} DGs")

def nodes(b): return "." + b.split(".",1)[1] if "." in b else ""
def split_line(nm, f):
    d = meta[nm]; u = UNIT[d["units"]]; nd = nodes(d["b1"])
    dss.Command(f"Edit Line.FLTSEG_A bus1={d['b1']} bus2=FLTPT{nd} linecode={d['lc']} "
                f"length={d['L']*f:.8f} units={u} phases={d['ph']} enabled=true")
    dss.Command(f"Edit Line.FLTSEG_B bus1=FLTPT{nd} bus2={d['b2']} linecode={d['lc']} "
                f"length={d['L']*(1-f):.8f} units={u} phases={d['ph']} enabled=true")
    dss.Command(f"Edit Line.{nm} enabled=false")
def restore_line(nm):
    dss.Command(f"Edit Line.{nm} enabled=true")
    dss.Command("Edit Line.FLTSEG_A enabled=false"); dss.Command("Edit Line.FLTSEG_B enabled=false")

def read_state(sm_list, split_nm):
    d = {}
    for lbl, ln in fs.PMU_LINES:
        src = "FLTSEG_A" if ln.upper() == split_nm else ln
        dss.Circuit.SetActiveElement(f"Line.{src}")
        cm = dss.CktElement.CurrentsMagAng(); n = dss.CktElement.NumPhases()
        vals = [(cm[2*j], cm[2*j+1]) if n > j else (0.0, 0.0) for j in range(3)]
        b1 = dss.CktElement.BusNames()[0].split(".")[0]
        dss.Circuit.SetActiveBus(b1); pv = dss.Bus.puVmagAngle(); nn = len(pv)//2
        vv = [(pv[2*j], pv[2*j+1]) if nn > j else (0.0, 0.0) for j in range(3)]
        for j, ph in enumerate("abc"):
            d[f"{lbl}_I{ph}"], d[f"{lbl}_I{ph}_ang"] = vals[j]
            d[f"{lbl}_V{ph}"], d[f"{lbl}_V{ph}_ang"] = vv[j]
    for sm_id, bus, node in sm_list:
        try:
            dss.Circuit.SetActiveBus(bus); pv = dss.Bus.puVmagAngle()
            mags = [pv[2*j] for j in range(len(pv)//2)]
            d[sm_id] = mags[node-1] if 0 < node <= len(mags) else (min(mags) if mags else 0.0)
        except Exception:
            d[sm_id] = 0.0
    return d

lat_ph = {}
for ln in FUSED:
    dss.Circuit.SetActiveElement(f"Line.{ln}"); lat_ph[ln] = dss.CktElement.NumPhases()
pmu_labels = [l for l, _ in fs.PMU_LINES]
sm_list = fs.load_smart_meters(); sm_ids = [s[0] for s in sm_list]
raw_cols = fs._raw_cols(pmu_labels, sm_ids)
META = ["fault_id","fault_type","fault_line","fault_frac","zone","impedance_type",
        "r_ground","r_phase","load_L1","cap_CP_NR_613","cap_CP_85W_900",
        "chain_attach_km","fault_on_chain","converged"]
rng_scn = np.random.default_rng(fs.FAULT_SEED + 1)
n_conv = 0
print(f"running {len(faults)} events...")
with open(os.path.join(OUT,"raw","results.csv"), "w", newline="") as fr, \
     open(os.path.join(OUT,"lateral_currents.csv"), "w", newline="") as fl:
    wr = csv.DictWriter(fr, fieldnames=META + raw_cols); wr.writeheader()
    wl = csv.writer(fl); wl.writerow(["fault_id","converged"] + FUSED)
    for i, flt in enumerate(faults):
        nm = flt["fault_line"]
        l1 = float(rng_scn.uniform(fs.L1_MIN, fs.L1_MAX))
        l2 = rng_scn.uniform(fs.L2_MIN, fs.L2_MAX, size=len(feeder_loads))
        fs.set_event_loads(feeder_loads, l1, l2); caps = fs.set_cap_states(rng_scn, l1)

        dgsweep.dg_normal_mode(N_DG)              # pre-fault: DG dispatches as generator
        split_line(nm, flt["fault_frac"])
        dss.Command("set controlmode=static"); dss.Command("set maxcontroliter=100"); dss.Command("Solve")
        pre_ok = dss.Solution.Converged()
        pre = read_state(sm_list, nm) if pre_ok else None

        dgsweep.dg_fault_mode(N_DG)               # during-fault: DG -> source behind X''
        dss.Command("set controlmode=off")
        fs.apply_fault({**flt, "fault_bus": "FLTPT"})
        dss.Command("Solve")
        flt_ok = dss.Solution.Converged()
        post = read_state(sm_list, nm) if flt_ok else None

        amps = []
        for ln in FUSED:
            if flt_ok:
                src = "FLTSEG_A" if ln == nm else ln
                dss.Circuit.SetActiveElement(f"Line.{src}")
                cm = dss.CktElement.CurrentsMagAng()
                amps.append(f"{max(cm[0:2*lat_ph[ln]:2]):.2f}")
            else:
                amps.append("")
        fs.clear_faults(); restore_line(nm); dgsweep.dg_normal_mode(N_DG)

        ok = pre_ok and flt_ok
        row = {"fault_id":flt["fault_id"],"fault_type":flt["fault_type"],"fault_line":nm,
               "fault_frac":round(flt["fault_frac"],6),"zone":flt["zone"],
               "impedance_type":flt["impedance_type"],"r_ground":flt["r_ground"],
               "r_phase":flt["r_phase"],"load_L1":round(l1,6),
               "cap_CP_NR_613":caps.get("CP-NR-613",False),"cap_CP_85W_900":caps.get("CP-85W-900",False),
               "chain_attach_km":("" if np.isnan(flt["chain_attach_km"]) else round(flt["chain_attach_km"],6)),
               "fault_on_chain":flt["on_chain"],"converged":ok}
        if ok:
            for k2, v in pre.items():  row[f"pre_{k2}"] = v
            for k2, v in post.items(): row[f"flt_{k2}"] = v
            n_conv += 1
        else:
            row.update({c: "" for c in raw_cols})
        wr.writerow(row); fr.flush(); wl.writerow([flt["fault_id"], ok] + amps); fl.flush()
        if (i+1) % 100 == 0 or (i+1) == len(faults):
            print(f"  {i+1:4d}/{len(faults)} converged={n_conv}", flush=True)
print(f"DONE {N_DG}DG -> {OUT}")
