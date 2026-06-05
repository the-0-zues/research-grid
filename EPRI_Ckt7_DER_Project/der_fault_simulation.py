"""
EPRI Ckt7 DER + Fault Simulation Framework
===========================================
- 25 DG scenarios (2% increments, 4 buses/step, up to ~50% of 203 3-phase MV buses)
- Scenario 1 uses existing G3520 buses: 253842, 165476, 165448, 283954
- Each scenario is cumulative (previous buses + new 4)
- 240 faults fixed across all scenarios: 20 zones x 12 faults each
  (4 SLG phase-A, 4 line-to-line AB, 4 three-phase, all bolted)
- Zone = buses/lines topologically between consecutive RFI monitors
- DG model: Cat 3520, 1600kW/2000kVA, 480V delta, via 12.47kV wye-delta transformer
"""

import opendssdirect as dss
import random
import csv
import os
import json
from collections import defaultdict, deque

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MASTER      = os.path.join(BASE_DIR, "electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7", "Master_ckt7_allocated_base.dss")
OUT_DIR     = os.path.join(BASE_DIR, "Simulation_Results")
CONFIG_FILE = os.path.join(BASE_DIR, "simulation_config.json")

os.makedirs(OUT_DIR, exist_ok=True)

# ── Constants ──────────────────────────────────────────────────────────────
SEED = 42
random.seed(SEED)

SCENARIO1_BUSES = ["253842", "165476", "165448", "283954"]
BUSES_PER_STEP  = 4
N_SCENARIOS     = 25   # 2% to 50% in 2% steps

RFI_LINES = [
    ("RFI1",  "215299"), ("RFI2",  "298366"), ("RFI3",  "157115"),
    ("RFI4",  "157152"), ("RFI5",  "157168"), ("RFI6",  "175038"),
    ("RFI7",  "255473"), ("RFI8",  "175060"), ("RFI9",  "175064"),
    ("RFI10", "175085"), ("RFI11", "175087"), ("RFI12", "182907"),
    ("RFI13", "182915"), ("RFI14", "157127"), ("RFI15", "318388"),
    ("RFI16", "175042"), ("RFI17", "262345"), ("RFI18", "174952"),
    ("RFI19", "175054"), ("RFI20", "255389"),
]
N_ZONES = 20

FAULTS_PER_ZONE = 12   # 4 SLG-A + 4 LL-AB + 4 3-phase
MV_KV           = 12470 / 1.7321 / 1000  # ~7.199 kV line-to-neutral

# DG transformer/generator parameters (Cat 3520)
DG_KVA  = 2000
DG_KW   = 1600
DG_KV_HV = 12.47
DG_KV_LV = 0.48
DG_XHL  = 11.13
DG_XDP  = 0.1962
DG_XDPP = 0.1033
DG_XRDP = 11.90


# ═══════════════════════════════════════════════════════════════════════════
# 1. Circuit loading helpers
# ═══════════════════════════════════════════════════════════════════════════

def load_base_circuit():
    dss.Basic.Start(0)
    dss.Command(f"Compile [{MASTER}]")
    dss.Command("Solve")


def get_3phase_mv_buses():
    """Return sorted list of 3-phase MV bus names (uppercase)."""
    buses = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if abs(dss.Bus.kVBase() - MV_KV) < 0.5 and dss.Bus.NumNodes() >= 3:
            buses.append(bus.upper())
    return sorted(buses)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Topology: assign MV lines to zones
# ═══════════════════════════════════════════════════════════════════════════

def build_mv_adjacency(mv_bus_set):
    """Build undirected adjacency: bus -> [(neighbor, line_name)]  (MV only)."""
    adj = defaultdict(list)
    line_endpoints = {}   # line_name_upper -> (b1, b2)

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


def find_substation_bus():
    """Return the bus name of the feeder head (energy meter element bus)."""
    dss.Meters.First()
    elem = dss.Meters.MeteredElement()   # e.g. "Line.333"
    term = dss.Meters.MeteredTerminal()
    dss.Circuit.SetActiveElement(elem)
    buses = dss.CktElement.BusNames()
    return buses[term - 1].split(".")[0].upper()


def assign_lines_to_zones(adj, line_endpoints, mv_bus_set):
    """
    BFS from substation.  When we cross an RFI line we enter the next zone.
    Zone numbering:
      Zone 0  = from substation to (and including) RFI1 line
      Zone 1  = from downstream of RFI1 to (and including) RFI2 line
      ...
      Zone 19 = from downstream of RFI19 to end of feeder (past RFI20)

    Returns:
      line_zone : dict  line_name_upper -> zone_index (0-based)
      zone_lines: dict  zone_index -> [line_name, ...]
    """
    rfi_line_set = {ln.upper() for _, ln in RFI_LINES}
    # Map each RFI line to its zone-boundary index (0-based, same as RFI number -1)
    rfi_line_to_idx = {ln.upper(): i for i, (_, ln) in enumerate(RFI_LINES)}

    substation = find_substation_bus()
    if substation not in mv_bus_set:
        # Fall back to first bus in CKT7 / feeder head
        substation = "CKT7"

    # BFS
    visited_buses = set()
    visited_lines = set()
    line_zone     = {}
    current_zone  = 0

    queue = deque([(substation, current_zone)])
    visited_buses.add(substation)

    while queue:
        bus, zone = queue.popleft()
        for neighbor, line_name in adj.get(bus, []):
            if line_name in visited_lines:
                continue
            visited_lines.add(line_name)

            # If this is an RFI boundary line, assign it to the current zone
            # then step into the next zone on the downstream side
            if line_name in rfi_line_set:
                line_zone[line_name] = zone
                next_zone = rfi_line_to_idx[line_name] + 1
            else:
                line_zone[line_name] = zone
                next_zone = zone

            if neighbor not in visited_buses:
                visited_buses.add(neighbor)
                queue.append((neighbor, next_zone))

    # Collect zone -> lines
    zone_lines = defaultdict(list)
    for ln, z in line_zone.items():
        zone_lines[z].append(ln)

    return line_zone, zone_lines


# ═══════════════════════════════════════════════════════════════════════════
# 3. Fault selection (fixed for all scenarios)
# ═══════════════════════════════════════════════════════════════════════════

def select_fault_locations(zone_lines, line_endpoints, mv_bus_set):
    """
    For each zone pick 12 fault lines:
      4 SLG (phase A), 4 LL (phases AB), 4 3-phase
    Returns list of dicts with fault metadata.
    """
    faults = []
    for zone_idx in range(N_ZONES):
        candidates = [
            ln for ln in zone_lines.get(zone_idx, [])
            if ln in line_endpoints
            and line_endpoints[ln][0] in mv_bus_set
            and line_endpoints[ln][1] in mv_bus_set
        ]
        if not candidates:
            print(f"  WARNING: Zone {zone_idx} has no eligible fault lines — skipping")
            continue

        # Sample with replacement if fewer than 12 candidates
        k = min(FAULTS_PER_ZONE, len(candidates))
        chosen = random.sample(candidates, k) if k >= FAULTS_PER_ZONE else \
                 random.choices(candidates, k=FAULTS_PER_ZONE)

        for i, ln in enumerate(chosen):
            b1, b2 = line_endpoints[ln]
            fault_type = ["SLG_B", "SLG_B", "SLG_C", "SLG_C",
                          "LL_AB", "LL_BC", "LL_CA", "LL_AB",
                          "3PH",   "3PH",   "3PH",   "3PH"]
            faults.append({
                "zone": zone_idx + 1,       # 1-based
                "fault_id": f"Z{zone_idx+1:02d}_F{i+1:02d}",
                "line": ln,
                "bus": b1,
                "fault_type": fault_type[i],
            })

    return faults


# ═══════════════════════════════════════════════════════════════════════════
# 4. DG scenario sequence
# ═══════════════════════════════════════════════════════════════════════════

def build_dg_scenarios(all_mv_buses):
    """
    Returns list of 25 scenario dicts, each with cumulative bus list.
    Scenario 1 = existing 4 buses.  Subsequent scenarios add 4 random buses.
    """
    used       = set(b.upper() for b in SCENARIO1_BUSES)
    pool       = [b for b in all_mv_buses if b not in used]
    random.shuffle(pool)

    scenarios  = []
    cumulative = list(SCENARIO1_BUSES)

    scenarios.append({
        "scenario_id": 1,
        "label": "DG_2pct",
        "new_buses": list(SCENARIO1_BUSES),
        "all_buses": list(cumulative),
    })

    for step in range(2, N_SCENARIOS + 1):
        new_buses  = pool[:BUSES_PER_STEP]
        pool       = pool[BUSES_PER_STEP:]
        cumulative = cumulative + new_buses
        scenarios.append({
            "scenario_id": step,
            "label": f"DG_{step*2}pct",
            "new_buses": new_buses,
            "all_buses": list(cumulative),
        })

    return scenarios


# ═══════════════════════════════════════════════════════════════════════════
# 5. OpenDSS DSS text for one DG at a bus
# ═══════════════════════════════════════════════════════════════════════════

def dg_dss_commands(bus):
    """Return DSS commands (list of strings) to add one Cat 3520 DG at an MV bus."""
    bus = bus.upper()
    lv_bus = f"DG_{bus}_LV"
    return [
        f"New Transformer.T_DG_{bus} phases=3 windings=2 XHL={DG_XHL}",
        f"~ wdg=1 bus={bus}.1.2.3.0 conn=wye   kV={DG_KV_HV} kVA={DG_KVA} %R=0",
        f"~ wdg=2 bus={lv_bus}.1.2.3 conn=delta kV={DG_KV_LV}  kVA={DG_KVA} %R=0",
        f"New Generator.G_DG_{bus} phases=3 bus1={lv_bus}.1.2.3 conn=delta",
        f"~ kV={DG_KV_LV} kW={DG_KW} kvar=0 kVA={DG_KVA} model=1 status=fixed",
        f"~ Xdp={DG_XDP} Xdpp={DG_XDPP} XRdp={DG_XRDP}",
    ]


# ═══════════════════════════════════════════════════════════════════════════
# 6. Fault DSS commands
# ═══════════════════════════════════════════════════════════════════════════

def fault_dss_commands(fault):
    """Return DSS New Fault command string for a fault dict. All faults start disabled."""
    bus   = fault["bus"]
    ftype = fault["fault_type"]
    fname = f"Fault_{fault['fault_id']}"
    suffix = "Enabled=No"

    if ftype == "SLG_A":
        return f"New Fault.{fname} bus1={bus}.1   phases=1 r=0.0001 {suffix}"
    elif ftype == "SLG_B":
        return f"New Fault.{fname} bus1={bus}.2   phases=1 r=0.0001 {suffix}"
    elif ftype == "SLG_C":
        return f"New Fault.{fname} bus1={bus}.3   phases=1 r=0.0001 {suffix}"
    elif ftype == "LL_AB":
        return f"New Fault.{fname} bus1={bus}.1.2 phases=2 r=0.0001 {suffix}"
    elif ftype == "LL_BC":
        return f"New Fault.{fname} bus1={bus}.2.3 phases=2 r=0.0001 {suffix}"
    elif ftype == "LL_CA":
        return f"New Fault.{fname} bus1={bus}.3.1 phases=2 r=0.0001 {suffix}"
    else:  # 3PH
        return f"New Fault.{fname} bus1={bus}.1.2.3 phases=3 r=0.0001 {suffix}"


# ═══════════════════════════════════════════════════════════════════════════
# 7. Read RFI monitor currents after a solved fault
# ═══════════════════════════════════════════════════════════════════════════

def read_rfi_currents():
    """
    Read peak phase current magnitude from each RFI monitor.
    Returns dict: rfi_name -> max phase current (A)
    """
    results = {}
    dss.Monitors.First()
    while True:
        name = dss.Monitors.Name().upper()
        if name.startswith("RFI"):
            # Export monitor and read channel data
            dss.Monitors.Save()
            header = dss.Monitors.Channel(1)  # dummy to trigger byte stream
            n_channels = dss.Monitors.NumChannels()
            # Channels: I1, Angle1, I2, Angle2, I3, Angle3  (for 3-phase mode=0)
            magnitudes = []
            for ch in range(1, n_channels + 1, 2):   # magnitude channels only
                try:
                    val = dss.Monitors.Channel(ch)
                    magnitudes.append(abs(val))
                except Exception:
                    pass
            results[name] = max(magnitudes) if magnitudes else 0.0
        if not dss.Monitors.Next():
            break
    return results


def read_rfi_via_element(rfi_label, line_name):
    """
    Fallback: read current directly from the line element via CktElement.
    Returns max phase current magnitude (A).
    """
    dss.Circuit.SetActiveElement(f"Line.{line_name}")
    currents = dss.CktElement.CurrentsMagAng()
    # currents = [I1mag, I1ang, I2mag, I2ang, ...] for terminal 1 then terminal 2
    n_phases = dss.CktElement.NumPhases()
    mags = [currents[2 * i] for i in range(n_phases)]
    return max(mags) if mags else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# 8. Run one fault scenario: compile + DGs + fault + solve + read
# ═══════════════════════════════════════════════════════════════════════════

def run_one_fault(dg_buses, fault):
    """
    Full round-trip:
      1. Recompile base circuit
      2. Add RFI monitors
      3. Add all DGs for this scenario
      4. Add fault
      5. Solve
      6. Read RFI currents
    Returns dict of RFI current readings.
    """
    dss.Command(f"Compile [{MASTER}]")

    # RFI monitors
    rfi_dss = os.path.join(
        BASE_DIR,
        "electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7",
        "RFI_Monitors.dss"
    )
    dss.Command(f"Redirect [{rfi_dss}]")

    # DGs
    for bus in dg_buses:
        for cmd in dg_dss_commands(bus):
            dss.Command(cmd)

    # Fault
    dss.Command(fault_dss_commands(fault))

    # Solve
    dss.Command("Set Mode=Snapshot")
    dss.Command("Solve")

    if not dss.Solution.Converged():
        return None   # mark as non-convergent

    # Read RFI currents from line elements (reliable vs. monitor byte stream)
    readings = {}
    for rfi_label, line_name in RFI_LINES:
        readings[rfi_label] = read_rfi_via_element(rfi_label, line_name)

    return readings


# ═══════════════════════════════════════════════════════════════════════════
# 9. Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("EPRI Ckt7 DER + Fault Simulation  [1 compile, enable/disable loop]")
    print("=" * 60)

    # ── 1. One-time circuit setup ─────────────────────────────
    print("\n[1] Loading base circuit (once)...")
    dss.Basic.Start(0)
    dss.Command(f"Compile [{MASTER}]")
    dss.Command("Set Mode=Snapshot")
    dss.Command("Solve")

    mv_buses   = get_3phase_mv_buses()
    mv_bus_set = set(mv_buses)
    print(f"    3-phase MV buses: {len(mv_buses)}")

    print("\n[2] Building MV adjacency and zone assignments...")
    adj, line_endpoints = build_mv_adjacency(mv_bus_set)
    line_zone, zone_lines = assign_lines_to_zones(adj, line_endpoints, mv_bus_set)
    for z in range(N_ZONES):
        print(f"    Zone {z+1:2d}: {len(zone_lines.get(z, []))} lines")

    print("\n[3] Selecting fault locations (seed={})...".format(SEED))
    faults = select_fault_locations(zone_lines, line_endpoints, mv_bus_set)
    print(f"    Total faults: {len(faults)}")
    by_type = defaultdict(int)
    for f in faults:
        by_type[f["fault_type"]] += 1
    for ft, cnt in sorted(by_type.items()):
        print(f"      {ft}: {cnt}")

    print("\n[4] Building DG scenario sequence...")
    scenarios = build_dg_scenarios(mv_buses)
    for s in scenarios:
        print(f"    Scenario {s['scenario_id']:2d} ({s['label']}): "
              f"{len(s['all_buses'])} cumulative buses | new: {s['new_buses']}")

    # RFI monitors (once)
    rfi_dss = os.path.join(
        BASE_DIR,
        "electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7",
        "RFI_Monitors.dss"
    )
    dss.Command(f"Redirect [{rfi_dss}]")

    # Pre-define all 240 fault elements as disabled (once)
    print("\n[5] Pre-defining fault elements (disabled)...")
    for fault in faults:
        dss.Command(fault_dss_commands(fault))

    # ── 2. Save config ────────────────────────────────────────
    config = {
        "seed": SEED,
        "n_scenarios": N_SCENARIOS,
        "n_faults": len(faults),
        "faults": faults,
        "scenarios": scenarios,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    print(f"    Config saved -> {CONFIG_FILE}")

    # ── 3. Resume check (scenario-level) ─────────────────────
    results_file = os.path.join(OUT_DIR, "all_results.csv")
    rfi_cols = [r for r, _ in RFI_LINES]
    fieldnames = (
        ["scenario_id", "scenario_label", "n_dg_buses",
         "fault_id", "zone", "fault_type", "fault_line", "fault_bus", "converged"]
        + rfi_cols
    )

    completed_scenarios = set()
    if os.path.exists(results_file):
        sc_counts = defaultdict(int)
        with open(results_file, "r", newline="") as f:
            for row in csv.DictReader(f):
                sc_counts[row["scenario_label"]] += 1
        completed_scenarios = {label for label, cnt in sc_counts.items()
                                if cnt >= len(faults)}
        if completed_scenarios:
            print(f"    Resuming: {len(completed_scenarios)} full scenarios already done.")

    file_mode  = "a" if completed_scenarios else "w"
    completed  = len(completed_scenarios) * len(faults)
    total_runs = len(scenarios) * len(faults)
    print(f"\n[6] Running {len(scenarios)} scenarios x {len(faults)} faults = {total_runs} simulations...")

    # ── 4. Scenario × fault loop ──────────────────────────────
    with open(results_file, file_mode, newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if file_mode == "w":
            writer.writeheader()

        for scenario in scenarios:
            # Add only the NEW DGs for this scenario (cumulative; never removed)
            for bus in scenario["new_buses"]:
                for cmd in dg_dss_commands(bus):
                    dss.Command(cmd)

            if scenario["label"] in completed_scenarios:
                continue  # DGs already added above; skip fault loop

            scenario_rows = []
            for fault in faults:
                fname = f"Fault_{fault['fault_id']}"

                dss.Command(f"Edit Fault.{fname} Enabled=Yes")
                dss.Command("Set Mode=Snapshot")
                dss.Command("Solve")
                converged = dss.Solution.Converged()

                row = {
                    "scenario_id":    scenario["scenario_id"],
                    "scenario_label": scenario["label"],
                    "n_dg_buses":     len(scenario["all_buses"]),
                    "fault_id":       fault["fault_id"],
                    "zone":           fault["zone"],
                    "fault_type":     fault["fault_type"],
                    "fault_line":     fault["line"],
                    "fault_bus":      fault["bus"],
                    "converged":      converged,
                }
                if converged:
                    row.update({rfi: read_rfi_via_element(rfi, ln)
                                for rfi, ln in RFI_LINES})
                else:
                    row.update({r: "" for r in rfi_cols})

                dss.Command(f"Edit Fault.{fname} Enabled=No")
                writer.writerow(row)
                csvfile.flush()
                scenario_rows.append(row)
                completed += 1

                if completed % 100 == 0 or completed == total_runs:
                    pct = 100 * completed / total_runs
                    print(f"    Progress: {completed}/{total_runs} ({pct:.1f}%)")

            # Per-scenario CSV
            sc_dir = os.path.join(OUT_DIR, f"Scenario_{scenario['scenario_id']:02d}_{scenario['label']}")
            os.makedirs(sc_dir, exist_ok=True)
            sc_file = os.path.join(sc_dir, f"results_{scenario['label']}.csv")
            with open(sc_file, "w", newline="") as sf:
                sw = csv.DictWriter(sf, fieldnames=fieldnames)
                sw.writeheader()
                sw.writerows(scenario_rows)

    print(f"\n[7] Done. Results -> {results_file}")
    print(f"    Per-scenario CSVs -> {OUT_DIR}/Scenario_XX_*/")


if __name__ == "__main__":
    main()
