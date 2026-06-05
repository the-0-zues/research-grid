"""
EPRI Ckt7 DER + Fault Simulation Framework (Efficient Version)
===============================================================
Structure:
  - Compile circuit ONCE
  - Add RFI monitors ONCE (20 monitors)
  - Add smart meter voltage monitors ONCE (867 meters, read as bus voltages)
  - Pre-define all 240 fault elements ONCE (disabled)
  - For each DG scenario (25 total, 2%->50%):
      - Incrementally add 4 new Cat 3520 DGs (no recompile)
      - For each fault (240):
          - Enable fault -> Solve -> Read RFI currents + SM voltages -> Disable fault
  - Total: 1 compile, 25 x 4 DG additions, 6000 solves
"""

import opendssdirect as dss
import random
import csv
import os
import json
from collections import defaultdict, deque

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = r"C:\EPRI_Ckt7_DER_Project"
MASTER      = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
SM_CSV      = r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv"
RFI_DSS     = r"C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7\RFI_Monitors.dss"
OUT_DIR     = os.path.join(BASE_DIR, "Simulation_Results")
CONFIG_FILE = os.path.join(BASE_DIR, "simulation_config.json")

os.makedirs(OUT_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

SCENARIO1_BUSES = ["253842", "165476", "165448", "283954"]
BUSES_PER_STEP  = 4
N_SCENARIOS     = 25

RFI_LINES = [
    ("RFI1",  "215299"), ("RFI2",  "298366"), ("RFI3",  "157115"),
    ("RFI4",  "157152"), ("RFI5",  "157168"), ("RFI6",  "175038"),
    ("RFI7",  "255473"), ("RFI8",  "175060"), ("RFI9",  "175064"),
    ("RFI10", "175085"), ("RFI11", "175087"), ("RFI12", "182907"),
    ("RFI13", "182915"), ("RFI14", "157127"), ("RFI15", "318388"),
    ("RFI16", "175042"), ("RFI17", "262345"), ("RFI18", "174952"),
    ("RFI19", "175054"), ("RFI20", "255389"),
]
N_ZONES         = 20
FAULTS_PER_ZONE = 12
MV_KV           = 12470 / 1.7321 / 1000

# Cat 3520 DG parameters
DG_KVA   = 2000
DG_KW    = 1600
DG_KV_HV = 12.47
DG_KV_LV = 0.48
DG_XHL   = 11.13
DG_XDP   = 0.1962
DG_XDPP  = 0.1033
DG_XRDP  = 11.90


# ═══════════════════════════════════════════════════════════════════════════
# Topology helpers (same as before)
# ═══════════════════════════════════════════════════════════════════════════

def get_3phase_mv_buses():
    buses = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if abs(dss.Bus.kVBase() - MV_KV) < 0.5 and dss.Bus.NumNodes() >= 3:
            buses.append(bus.upper())
    return sorted(buses)


def build_mv_adjacency(mv_bus_set):
    adj = defaultdict(list)
    line_endpoints = {}
    dss.Lines.First()
    while True:
        name = dss.Lines.Name().upper()
        b1   = dss.Lines.Bus1().split(".")[0].upper()
        b2   = dss.Lines.Bus2().split(".")[0].upper()
        line_endpoints[name] = (b1, b2)
        if b1 in mv_bus_set and b2 in mv_bus_set:
            adj[b1].append((b2, name))
            adj[b2].append((b1, name))
        if not dss.Lines.Next():
            break
    return adj, line_endpoints


def assign_lines_to_zones(adj, line_endpoints, mv_bus_set):
    rfi_line_set   = {ln.upper() for _, ln in RFI_LINES}
    rfi_line_to_idx = {ln.upper(): i for i, (_, ln) in enumerate(RFI_LINES)}

    # Find substation bus
    dss.Meters.First()
    elem  = dss.Meters.MeteredElement()
    term  = dss.Meters.MeteredTerminal()
    dss.Circuit.SetActiveElement(elem)
    substation = dss.CktElement.BusNames()[term - 1].split(".")[0].upper()
    if substation not in mv_bus_set:
        substation = "CKT7"

    visited_buses = set([substation])
    visited_lines = set()
    line_zone     = {}
    queue = deque([(substation, 0)])

    while queue:
        bus, zone = queue.popleft()
        for neighbor, line_name in adj.get(bus, []):
            if line_name in visited_lines:
                continue
            visited_lines.add(line_name)
            if line_name in rfi_line_set:
                line_zone[line_name] = zone
                next_zone = rfi_line_to_idx[line_name] + 1
            else:
                line_zone[line_name] = zone
                next_zone = zone
            if neighbor not in visited_buses:
                visited_buses.add(neighbor)
                queue.append((neighbor, next_zone))

    zone_lines = defaultdict(list)
    for ln, z in line_zone.items():
        zone_lines[z].append(ln)
    return line_zone, zone_lines


def select_fault_locations(zone_lines, line_endpoints, mv_bus_set):
    faults = []
    fault_types = ["SLG_A"] * 4 + ["LL_AB"] * 4 + ["3PH"] * 4
    for zone_idx in range(N_ZONES):
        candidates = [
            ln for ln in zone_lines.get(zone_idx, [])
            if ln in line_endpoints
            and line_endpoints[ln][0] in mv_bus_set
            and line_endpoints[ln][1] in mv_bus_set
        ]
        if not candidates:
            print(f"  WARNING: Zone {zone_idx+1} has no eligible lines")
            continue
        chosen = (random.sample(candidates, FAULTS_PER_ZONE)
                  if len(candidates) >= FAULTS_PER_ZONE
                  else random.choices(candidates, k=FAULTS_PER_ZONE))
        for i, ln in enumerate(chosen):
            b1, _ = line_endpoints[ln]
            faults.append({
                "zone":       zone_idx + 1,
                "fault_id":   f"Z{zone_idx+1:02d}_F{i+1:02d}",
                "line":       ln,
                "bus":        b1,
                "fault_type": fault_types[i],
                "fault_name": f"FLT_Z{zone_idx+1:02d}_F{i+1:02d}",
            })
    return faults


def build_dg_scenarios(all_mv_buses):
    used      = set(b.upper() for b in SCENARIO1_BUSES)
    pool      = [b for b in all_mv_buses if b not in used]
    random.shuffle(pool)
    scenarios = []
    cumulative = list(SCENARIO1_BUSES)
    scenarios.append({
        "scenario_id": 1, "label": "DG_2pct",
        "new_buses": list(SCENARIO1_BUSES), "all_buses": list(cumulative),
    })
    for step in range(2, N_SCENARIOS + 1):
        new_buses  = pool[:BUSES_PER_STEP]
        pool       = pool[BUSES_PER_STEP:]
        cumulative = cumulative + new_buses
        scenarios.append({
            "scenario_id": step, "label": f"DG_{step*2}pct",
            "new_buses": new_buses, "all_buses": list(cumulative),
        })
    return scenarios


# ═══════════════════════════════════════════════════════════════════════════
# OpenDSS element helpers
# ═══════════════════════════════════════════════════════════════════════════

def add_dg(bus):
    """Add one Cat 3520 DG at a 12.47kV bus (transformer + generator)."""
    bus = bus.upper()
    lv  = f"DG_{bus}_LV"
    dss.Command(f"New Transformer.T_DG_{bus} phases=3 windings=2 XHL={DG_XHL}")
    dss.Command(f"~ wdg=1 bus={bus}.1.2.3.0 conn=wye   kV={DG_KV_HV} kVA={DG_KVA} %R=0")
    dss.Command(f"~ wdg=2 bus={lv}.1.2.3   conn=delta kV={DG_KV_LV}  kVA={DG_KVA} %R=0")
    dss.Command(f"New Generator.G_DG_{bus} phases=3 bus1={lv}.1.2.3 conn=delta")
    dss.Command(f"~ kV={DG_KV_LV} kW={DG_KW} kvar=0 kVA={DG_KVA} model=1 status=fixed")
    dss.Command(f"~ Xdp={DG_XDP} Xdpp={DG_XDPP} XRdp={DG_XRDP}")


def define_fault_disabled(fault):
    """Pre-define a fault element in disabled state."""
    name  = fault["fault_name"]
    bus   = fault["bus"]
    ftype = fault["fault_type"]
    if ftype == "SLG_A":
        dss.Command(f"New Fault.{name} bus1={bus}.1       phases=1 r=0.0001 enabled=false")
    elif ftype == "LL_AB":
        dss.Command(f"New Fault.{name} bus1={bus}.1.2     phases=2 r=0.0001 enabled=false")
    else:
        dss.Command(f"New Fault.{name} bus1={bus}.1.2.3   phases=3 r=0.0001 enabled=false")


def enable_fault(fault_name):
    dss.Command(f"Fault.{fault_name}.enabled=true")


def disable_fault(fault_name):
    dss.Command(f"Fault.{fault_name}.enabled=false")


# ═══════════════════════════════════════════════════════════════════════════
# Reading results
# ═══════════════════════════════════════════════════════════════════════════

def read_rfi_currents():
    """Read max phase current magnitude (A) from each RFI line element."""
    results = {}
    for rfi_label, line_name in RFI_LINES:
        dss.Circuit.SetActiveElement(f"Line.{line_name}")
        cmag = dss.CktElement.CurrentsMagAng()
        n    = dss.CktElement.NumPhases()
        mags = [cmag[2 * i] for i in range(n)]
        results[rfi_label] = max(mags) if mags else 0.0
    return results


def read_smart_meter_voltages(sm_list):
    """
    Read per-unit voltage magnitude at each smart meter bus.
    sm_list: list of (sm_id, bus_name, phase_node)
    Returns dict: sm_id -> pu voltage (min phase if multi-phase)
    """
    results = {}
    for sm_id, bus, phase_node in sm_list:
        try:
            dss.Circuit.SetActiveBus(bus)
            pu_vmag = dss.Bus.puVmagAngle()  # [V1mag, V1ang, V2mag, V2ang, ...]
            # Take the phase of interest (phase_node 0 = all phases, take min)
            mags = [pu_vmag[2 * i] for i in range(len(pu_vmag) // 2)]
            if phase_node > 0 and phase_node <= len(mags):
                results[sm_id] = mags[phase_node - 1]
            else:
                results[sm_id] = min(mags) if mags else 0.0
        except Exception:
            results[sm_id] = 0.0
    return results


def load_smart_meters():
    """
    Load smart meter list from CSV.
    Returns list of (sm_id, bus_name, phase_node).
    For single-phase meters the bus includes .N so we strip it and track phase.
    """
    sm_list = []
    with open(SM_CSV) as f:
        for row in csv.DictReader(f):
            sm_id = row["SmartMeter_ID"]
            bus1  = row["Bus1"]          # e.g. S1X_1000824.1  or S1X_0862099
            # Parse bus and phase
            if "." in bus1:
                parts = bus1.split(".")
                bus   = parts[0]
                phase = int(parts[1])
            else:
                bus   = bus1
                phase = 0   # all phases
            sm_list.append((sm_id, bus.upper(), phase))
    return sm_list


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("EPRI Ckt7 DER + Fault Simulation (Efficient)")
    print("=" * 60)

    # ── 1. Compile circuit ONCE ──
    print("\n[1] Compiling base circuit...")
    dss.Basic.Start(0)
    dss.Command(f"Compile [{MASTER}]")
    dss.Command("Solve")
    print(f"    Circuit: {dss.Circuit.Name()} | Converged: {dss.Solution.Converged()}")

    # ── 2. Topology ──
    print("\n[2] Building topology and zone assignments...")
    mv_buses   = get_3phase_mv_buses()
    mv_bus_set = set(mv_buses)
    adj, line_endpoints = build_mv_adjacency(mv_bus_set)
    line_zone, zone_lines = assign_lines_to_zones(adj, line_endpoints, mv_bus_set)
    print(f"    3-phase MV buses: {len(mv_buses)}")

    # ── 3. Select fixed faults ──
    print("\n[3] Selecting fixed fault locations (seed={})...".format(SEED))
    faults = select_fault_locations(zone_lines, line_endpoints, mv_bus_set)
    print(f"    Total faults: {len(faults)} ({len(faults)//3} per type x 3 types)")

    # ── 4. Build scenario sequence ──
    print("\n[4] Building DG scenario sequence...")
    scenarios = build_dg_scenarios(mv_buses)
    for s in scenarios:
        print(f"    Scenario {s['scenario_id']:2d} ({s['label']}): "
              f"{len(s['all_buses'])} buses | new: {s['new_buses']}")

    # ── Save config ──
    with open(CONFIG_FILE, "w") as f:
        json.dump({"seed": SEED, "faults": faults, "scenarios": scenarios}, f, indent=2)
    print(f"\n    Config saved -> {CONFIG_FILE}")

    # ── 5. Add RFI monitors ONCE ──
    print("\n[5] Adding RFI monitors...")
    dss.Command(f"Redirect [{RFI_DSS}]")
    print(f"    Added 20 RFI monitors")

    # ── 6. Load smart meter list ──
    print("\n[6] Loading smart meter locations...")
    sm_list = load_smart_meters()
    print(f"    {len(sm_list)} smart meters loaded")

    # ── 7. Pre-define all faults as DISABLED ──
    print("\n[7] Pre-defining all fault elements (disabled)...")
    for fault in faults:
        define_fault_disabled(fault)
    print(f"    {len(faults)} fault elements defined (all disabled)")
    dss.Command("Solve")   # re-solve clean base with monitors but no faults
    print(f"    Base re-solve converged: {dss.Solution.Converged()}")

    # ── 8. Output file setup ──
    results_file = os.path.join(OUT_DIR, "all_results.csv")
    rfi_cols = [r for r, _ in RFI_LINES]
    sm_cols  = [sm[0] for sm in sm_list]   # SM_1 ... SM_867
    fieldnames = (
        ["scenario_id", "scenario_label", "n_dg_buses",
         "fault_id", "zone", "fault_type", "fault_line", "fault_bus", "converged"]
        + rfi_cols + sm_cols
    )

    # Check for already-completed runs (resume support)
    completed_keys = set()
    if os.path.exists(results_file):
        with open(results_file, "r", newline="") as ef:
            for row in csv.DictReader(ef):
                completed_keys.add((row["scenario_label"], row["fault_id"]))
        print(f"\n    Resuming: {len(completed_keys)} runs already done")

    file_mode  = "a" if completed_keys else "w"
    write_hdr  = len(completed_keys) == 0

    # ── 9. Main simulation loop ──
    total_runs = len(scenarios) * len(faults)
    print(f"\n[8] Running {len(scenarios)} scenarios x {len(faults)} faults = {total_runs} simulations...")
    print(     "    (1 compile | incremental DGs | enable/disable fault per solve)\n")

    completed = len(completed_keys)

    with open(results_file, file_mode, newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_hdr:
            writer.writeheader()

        for scenario in scenarios:
            sc_label = scenario["label"]

            # Add only the NEW DGs for this scenario (incremental)
            for bus in scenario["new_buses"]:
                add_dg(bus)
            dss.Command("Solve")   # settle base case with new DGs

            scenario_results = []

            for fault in faults:
                key = (sc_label, fault["fault_id"])
                if key in completed_keys:
                    continue

                # Enable -> Solve -> Read -> Disable
                enable_fault(fault["fault_name"])
                dss.Command("Solve")
                converged = dss.Solution.Converged()

                row = {
                    "scenario_id":    scenario["scenario_id"],
                    "scenario_label": sc_label,
                    "n_dg_buses":     len(scenario["all_buses"]),
                    "fault_id":       fault["fault_id"],
                    "zone":           fault["zone"],
                    "fault_type":     fault["fault_type"],
                    "fault_line":     fault["line"],
                    "fault_bus":      fault["bus"],
                    "converged":      converged,
                }

                if converged:
                    row.update(read_rfi_currents())
                    row.update(read_smart_meter_voltages(sm_list))
                else:
                    row.update({r: "" for r in rfi_cols})
                    row.update({s: "" for s in sm_cols})

                disable_fault(fault["fault_name"])

                writer.writerow(row)
                csvfile.flush()
                scenario_results.append(row)
                completed += 1

                if completed % 100 == 0 or completed == total_runs:
                    pct = 100 * completed / total_runs
                    print(f"    Progress: {completed}/{total_runs} ({pct:.1f}%) | "
                          f"Scenario: {sc_label}")

            # Per-scenario CSV
            sc_dir  = os.path.join(OUT_DIR, f"Scenario_{scenario['scenario_id']:02d}_{sc_label}")
            os.makedirs(sc_dir, exist_ok=True)
            sc_file = os.path.join(sc_dir, f"results_{sc_label}.csv")
            sc_mode = "a" if os.path.exists(sc_file) else "w"
            with open(sc_file, sc_mode, newline="") as sf:
                sw = csv.DictWriter(sf, fieldnames=fieldnames)
                if sc_mode == "w":
                    sw.writeheader()
                sw.writerows(scenario_results)

    print(f"\n[9] Done. Results -> {results_file}")


if __name__ == "__main__":
    main()
