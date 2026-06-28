"""
fault_simulation_2000.py
========================
EPRI Ckt7 — Realistic Fault Simulation (2,000 Events)

DG setup:
  - 10% penetration: 20 Cat 3520 generators randomly placed across 203 MV buses
  - Single fixed scenario (no k-run incrementation)

Fault distribution (realistic, grounded in utility statistics):
  SLG A/B/C     : 1,400 (70%) — wet grass 144 Ω / dry grass 288 Ω
  LL  AB/BC/CA  :   300 (15%) — 2 Ω phase-to-phase arc
  LLG ABG/BCG/ACG:  200 (10%) — 2 Ω phase-to-phase + wet/dry grass to ground
  3PH           :   100  (5%) — 2 Ω triangle, no ground connection

Impedance sources:
  Wet grass: 7,200 V / 50 A = 144 Ω  (IEEE PSRC WG D15)
  Dry grass: 7,200 V / 25 A = 288 Ω  (IEEE PSRC WG D15)
  Phase arc: 2 Ω (standard arc resistance assumption)
  No bolted faults — they do not occur in practice on overhead distribution

Measurement noise (ANSI/IEEE standards, applied post-simulation):
  RFI: RSS of IEEE C57.13-2016 Class 0.6 CT (0.6%/3) and
       ANSI C12.1-2022 Class 0.5 meter (0.7%/3)  → σ ≈ 0.307% per reading
  SM:  ANSI C12.20 Class 0.5 (±0.5%)              → σ ≈ 0.167% per reading
  SM dropout: 10 levels from 5% to 50% (models AMI last-gasp reporting failure)

Outputs:
  Realistic_Simulation/clean/results.csv
  Realistic_Simulation/Degraded_Dropout_05pct/results.csv
  ...
  Realistic_Simulation/Degraded_Dropout_50pct/results.csv
"""

import opendssdirect as dss
import pandas as pd
import numpy as np
import random
import csv
import os
from collections import defaultdict, deque, Counter

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

DG_SEED    = 2025
FAULT_SEED = 2025
DG_COUNT   = 20      # 10% of 203 three-phase MV buses

MASTER  = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
SM_CSV  = r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv"
RFI_DSS = (r"C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-"
           r"EPRITestCircuits-ckt7\RFI_Monitors.dss")
OUT_DIR = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation"

# Fault impedances (IEEE PSRC WG D15 surface contact measurements at 7.2 kV L-N)
R_WET_GRASS = 144.0    # 7200 V / 50 A
R_DRY_GRASS = 288.0    # 7200 V / 25 A
R_PHASE_ARC = 2.0      # phase-to-phase arc resistance (LL, LLG, 3PH)

# ANSI/IEEE noise sigma factors (max deviation treated as 3-sigma bound)
RFI_SIGMA = np.sqrt((0.006 / 3) ** 2 + (0.007 / 3) ** 2)  # ≈ 0.00307
SM_SIGMA  = 0.005 / 3                                        # ≈ 0.001667

DROPOUT_RATE = 0.10    # 10% smart meter dropout — models AMI last-gasp failure

MV_KV = 12470 / 1.7321 / 1000   # line-to-neutral kV for 12.47 kV system ≈ 7.199

RFI_LINES = [
    ("RFI1",  "215299"), ("RFI2",  "298366"), ("RFI3",  "157115"),
    ("RFI4",  "157152"), ("RFI5",  "157168"), ("RFI6",  "175038"),
    ("RFI7",  "255473"), ("RFI8",  "175060"), ("RFI9",  "175064"),
    ("RFI10", "175085"), ("RFI11", "175087"), ("RFI12", "182907"),
    ("RFI13", "182915"), ("RFI14", "157127"), ("RFI15", "318388"),
    ("RFI16", "175042"), ("RFI17", "262345"), ("RFI18", "174952"),
    ("RFI19", "175054"), ("RFI20", "255389"),
]

# Cat 3520 natural gas synchronous generator parameters
DG_KVA   = 2000;  DG_KW   = 1600
DG_KV_HV = 12.47; DG_KV_LV = 0.48
DG_XHL   = 11.13; DG_XDP  = 0.1962; DG_XDPP = 0.1033; DG_XRDP = 11.90

META_COLS = [
    "fault_id", "fault_type", "fault_bus", "zone",
    "impedance_type", "r_ground", "r_phase", "converged"
]


# ═══════════════════════════════════════════════════════════════════════════
# Topology helpers
# ═══════════════════════════════════════════════════════════════════════════

def get_3phase_mv_buses():
    """Return sorted list of all three-phase MV bus names."""
    buses = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if abs(dss.Bus.kVBase() - MV_KV) < 0.5 and dss.Bus.NumNodes() >= 3:
            buses.append(bus.upper())
    return sorted(buses)


def build_mv_adjacency(mv_bus_set):
    """Build adjacency list and line endpoint map for MV network."""
    adj            = defaultdict(list)
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


def build_bus_zone_map(adj, mv_bus_set):
    """
    BFS from substation to assign each MV bus to an RFI zone (1-20).
    A bus enters zone Z when traversal crosses RFI line Z-1.
    """
    rfi_line_set    = {ln.upper() for _, ln in RFI_LINES}
    rfi_line_to_idx = {ln.upper(): i for i, (_, ln) in enumerate(RFI_LINES)}

    # Locate substation via energy meter
    dss.Meters.First()
    elem = dss.Meters.MeteredElement()
    term = dss.Meters.MeteredTerminal()
    dss.Circuit.SetActiveElement(elem)
    substation = dss.CktElement.BusNames()[term - 1].split(".")[0].upper()
    if substation not in mv_bus_set:
        substation = sorted(mv_bus_set)[0]

    bus_zone      = {substation: 1}
    visited_buses = {substation}
    visited_lines = set()
    queue         = deque([(substation, 1)])

    while queue:
        bus, zone = queue.popleft()
        for neighbor, line_name in adj.get(bus, []):
            if line_name in visited_lines:
                continue
            visited_lines.add(line_name)
            next_zone = rfi_line_to_idx[line_name] + 1 if line_name in rfi_line_set else zone
            if neighbor not in visited_buses:
                visited_buses.add(neighbor)
                bus_zone[neighbor] = next_zone
                queue.append((neighbor, next_zone))

    return bus_zone


# ═══════════════════════════════════════════════════════════════════════════
# Fault list construction
# ═══════════════════════════════════════════════════════════════════════════

def build_fault_list(mv_buses, bus_zone, seed=FAULT_SEED):
    """
    Build the complete 2,000-fault event list.
    Each event is a dict with type, bus, zone, impedance parameters.
    Buses are drawn randomly from all 203 three-phase MV buses.
    """
    rng    = random.Random(seed)
    faults = []

    def add_slg(phase_label, n_wet, n_dry):
        impedances = [R_WET_GRASS] * n_wet + [R_DRY_GRASS] * n_dry
        rng.shuffle(impedances)
        for r in impedances:
            bus = rng.choice(mv_buses)
            faults.append({
                "fault_type":     f"SLG_{phase_label}",
                "fault_bus":      bus,
                "zone":           bus_zone.get(bus, 0),
                "impedance_type": "wet_grass" if r == R_WET_GRASS else "dry_grass",
                "r_ground":       r,
                "r_phase":        "",
            })

    def add_ll(phase_pair, count):
        for _ in range(count):
            bus = rng.choice(mv_buses)
            faults.append({
                "fault_type":     f"LL_{phase_pair}",
                "fault_bus":      bus,
                "zone":           bus_zone.get(bus, 0),
                "impedance_type": "arc",
                "r_ground":       "",
                "r_phase":        R_PHASE_ARC,
            })

    def add_llg(phase_pair, n_wet, n_dry):
        impedances = [R_WET_GRASS] * n_wet + [R_DRY_GRASS] * n_dry
        rng.shuffle(impedances)
        for r in impedances:
            bus = rng.choice(mv_buses)
            faults.append({
                "fault_type":     f"LLG_{phase_pair}G",
                "fault_bus":      bus,
                "zone":           bus_zone.get(bus, 0),
                "impedance_type": "wet_grass" if r == R_WET_GRASS else "dry_grass",
                "r_ground":       r,
                "r_phase":        R_PHASE_ARC,
            })

    def add_3ph(count):
        for _ in range(count):
            bus = rng.choice(mv_buses)
            faults.append({
                "fault_type":     "3PH",
                "fault_bus":      bus,
                "zone":           bus_zone.get(bus, 0),
                "impedance_type": "arc",
                "r_ground":       "",
                "r_phase":        R_PHASE_ARC,
            })

    # Exact counts per user specification
    add_slg("A",  n_wet=233, n_dry=233)   # 466  total
    add_slg("B",  n_wet=234, n_dry=233)   # 467  total
    add_slg("C",  n_wet=234, n_dry=233)   # 467  total
    add_ll("AB",  100)
    add_ll("BC",  100)
    add_ll("CA",  100)
    add_llg("AB", n_wet=33,  n_dry=33)    #  66  total
    add_llg("BC", n_wet=34,  n_dry=33)    #  67  total
    add_llg("AC", n_wet=34,  n_dry=33)    #  67  total
    add_3ph(100)
    # Grand total: 1400 + 300 + 200 + 100 = 2000

    rng.shuffle(faults)
    for i, f in enumerate(faults):
        f["fault_id"] = f"F{i + 1:04d}"

    return faults


# ═══════════════════════════════════════════════════════════════════════════
# DG and fault element helpers
# ═══════════════════════════════════════════════════════════════════════════

def add_dg(bus):
    """Add one Cat 3520 DG (step-up transformer + synchronous generator)."""
    bus = bus.upper()
    lv  = f"DG_{bus}_LV"
    dss.Command(f"New Transformer.T_DG_{bus} phases=3 windings=2 XHL={DG_XHL}")
    dss.Command(f"~ wdg=1 bus={bus}.1.2.3.0 conn=wye   kV={DG_KV_HV} kVA={DG_KVA} %R=0")
    dss.Command(f"~ wdg=2 bus={lv}.1.2.3   conn=delta kV={DG_KV_LV}  kVA={DG_KVA} %R=0")
    dss.Command(f"New Generator.G_DG_{bus} phases=3 bus1={lv}.1.2.3 conn=delta")
    dss.Command(f"~ kV={DG_KV_LV} kW={DG_KW} kvar=0 kVA={DG_KVA} model=1 status=fixed")
    dss.Command(f"~ Xdp={DG_XDP} Xdpp={DG_XDPP} XRdp={DG_XRDP}")


def init_fault_slots(anchor_bus):
    """
    Pre-define three reusable fault slots on an anchor bus.
    Properties (bus, r) are overwritten for each event via Edit commands.
    Three slots support LLG and 3PH faults which need simultaneous elements.
    """
    b = anchor_bus
    for slot in ["FLT_S1", "FLT_S2", "FLT_S3"]:
        dss.Command(
            f"New Fault.{slot} Bus1={b}.1 Bus2={b}.0 phases=1 r=1 enabled=false"
        )


def apply_fault(fault):
    """
    Reconfigure and enable the appropriate fault slots for this event.

    SLG  → 1 element (phase to ground)
    LL   → 1 element (phase to phase)
    LLG  → 3 elements (phase A to ground, phase B to ground, A to B arc)
    3PH  → 3 elements (A-B arc, B-C arc, C-A arc — no ground)
    """
    bus   = fault["fault_bus"]
    ftype = fault["fault_type"]
    rg    = fault["r_ground"]
    rp    = fault["r_phase"]

    if ftype == "SLG_A":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.1 Bus2={bus}.0 r={rg} enabled=true")

    elif ftype == "SLG_B":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.2 Bus2={bus}.0 r={rg} enabled=true")

    elif ftype == "SLG_C":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.3 Bus2={bus}.0 r={rg} enabled=true")

    elif ftype == "LL_AB":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.1 Bus2={bus}.2 r={rp} enabled=true")

    elif ftype == "LL_BC":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.2 Bus2={bus}.3 r={rp} enabled=true")

    elif ftype == "LL_CA":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.3 Bus2={bus}.1 r={rp} enabled=true")

    elif ftype == "LLG_ABG":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.1 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S2 Bus1={bus}.2 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S3 Bus1={bus}.1 Bus2={bus}.2 r={rp} enabled=true")

    elif ftype == "LLG_BCG":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.2 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S2 Bus1={bus}.3 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S3 Bus1={bus}.2 Bus2={bus}.3 r={rp} enabled=true")

    elif ftype == "LLG_ACG":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.1 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S2 Bus1={bus}.3 Bus2={bus}.0 r={rg} enabled=true")
        dss.Command(f"Edit Fault.FLT_S3 Bus1={bus}.1 Bus2={bus}.3 r={rp} enabled=true")

    elif ftype == "3PH":
        dss.Command(f"Edit Fault.FLT_S1 Bus1={bus}.1 Bus2={bus}.2 r={rp} enabled=true")
        dss.Command(f"Edit Fault.FLT_S2 Bus1={bus}.2 Bus2={bus}.3 r={rp} enabled=true")
        dss.Command(f"Edit Fault.FLT_S3 Bus1={bus}.3 Bus2={bus}.1 r={rp} enabled=true")


def clear_faults():
    """Disable all three fault slots after each solve."""
    dss.Command("Edit Fault.FLT_S1 enabled=false")
    dss.Command("Edit Fault.FLT_S2 enabled=false")
    dss.Command("Edit Fault.FLT_S3 enabled=false")


# ═══════════════════════════════════════════════════════════════════════════
# Reading simulation results
# ═══════════════════════════════════════════════════════════════════════════

def read_rfi_currents():
    """Read maximum phase current magnitude (A) from each of the 20 RFI lines."""
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
    Read per-unit voltage at each of the 867 smart meter buses.
    Returns the phase-specific pu voltage for single-phase meters,
    or the minimum phase pu voltage for three-phase meters.
    """
    results = {}
    for sm_id, bus, phase_node in sm_list:
        try:
            dss.Circuit.SetActiveBus(bus)
            pu_vmag = dss.Bus.puVmagAngle()
            mags    = [pu_vmag[2 * i] for i in range(len(pu_vmag) // 2)]
            if phase_node > 0 and phase_node <= len(mags):
                results[sm_id] = mags[phase_node - 1]
            else:
                results[sm_id] = min(mags) if mags else 0.0
        except Exception:
            results[sm_id] = 0.0
    return results


def load_smart_meters():
    """Load the 867 smart meter bus names and phase nodes from CSV."""
    sm_list = []
    with open(SM_CSV) as f:
        for row in csv.DictReader(f):
            sm_id = row["SmartMeter_ID"]
            bus1  = row["Bus1"]
            if "." in bus1:
                parts = bus1.split(".")
                bus, phase = parts[0], int(parts[1])
            else:
                bus, phase = bus1, 0
            sm_list.append((sm_id, bus.upper(), phase))
    return sm_list


# ═══════════════════════════════════════════════════════════════════════════
# Noise and dropout (ANSI/IEEE — applied in post-processing)
# ═══════════════════════════════════════════════════════════════════════════

def _proportional_noise(vals, sigma_factor, rng):
    """
    Add N(0, sigma_factor * |val|) to each element independently.
    Cells that are NaN or zero receive no noise (sigma would be zero/invalid).
    """
    sigma      = sigma_factor * np.abs(vals)
    safe_sigma = np.where((sigma == 0) | np.isnan(sigma), 1.0, sigma)
    noise      = rng.normal(0.0, safe_sigma)
    noise      = np.where(np.isnan(vals) | (sigma == 0), 0.0, noise)
    return vals + noise


def apply_noise_and_dropout(df, rfi_cols, sm_cols, dropout_rate, seed):
    """
    Apply measurement noise and smart meter dropout to a clean results DataFrame.

    RFI noise : RSS-combined IEEE C57.13 + ANSI C12.1 sigma ≈ 0.307%
    SM  noise : ANSI C12.20 Class 0.5 sigma ≈ 0.167%
    SM dropout: random per-cell NaN mask at dropout_rate probability
    """
    rng = np.random.default_rng(seed)
    out = df.copy()

    # Convert measurement columns to float (empty strings → NaN for non-converged rows)
    rfi_vals = out[rfi_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    sm_vals  = out[sm_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)

    # Apply proportional Gaussian noise
    out[rfi_cols] = _proportional_noise(rfi_vals, RFI_SIGMA, rng)
    out[sm_cols]  = _proportional_noise(sm_vals,  SM_SIGMA,  rng)

    # Apply smart meter dropout — random per-cell NaN mask
    n_rows, n_sm  = len(out), len(sm_cols)
    dropout_mask  = rng.random((n_rows, n_sm)) < dropout_rate
    sm_noisy      = out[sm_cols].values.copy().astype(float)
    sm_noisy[dropout_mask] = np.nan
    out[sm_cols]  = sm_noisy

    return out


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print("=" * 65)
    print("EPRI Ckt7  —  Realistic Fault Simulation  —  2,000 Events")
    print(f"  DG seed: {DG_SEED}   Fault seed: {FAULT_SEED}   DG count: {DG_COUNT}")
    print("=" * 65)

    os.makedirs(OUT_DIR, exist_ok=True)

    # ── 1. Compile base circuit ──────────────────────────────────────────
    print("\n[1] Compiling base circuit...")
    dss.Basic.Start(0)
    dss.Command(f"Compile [{MASTER}]")
    dss.Command("Solve")
    print(f"    Circuit : {dss.Circuit.Name()}")
    print(f"    Converged: {dss.Solution.Converged()}")

    # ── 2. Build topology ────────────────────────────────────────────────
    print("\n[2] Building MV topology and zone map...")
    mv_buses   = get_3phase_mv_buses()
    mv_bus_set = set(mv_buses)
    adj, _     = build_mv_adjacency(mv_bus_set)
    bus_zone   = build_bus_zone_map(adj, mv_bus_set)
    print(f"    Three-phase MV buses : {len(mv_buses)}")
    zone_counts = Counter(bus_zone.values())
    print(f"    Zones covered        : {sorted(zone_counts.keys())}")

    # ── 3. Build fault list ──────────────────────────────────────────────
    print("\n[3] Building 2,000-fault event list...")
    faults = build_fault_list(mv_buses, bus_zone)
    dist   = Counter(f["fault_type"] for f in faults)
    print(f"    Total: {len(faults)} faults")
    for ft in sorted(dist):
        print(f"      {ft:<14}: {dist[ft]:4d}")

    # ── 4. Add RFI monitors ──────────────────────────────────────────────
    print("\n[4] Adding RFI monitors...")
    dss.Command(f"Redirect [{RFI_DSS}]")

    # ── 5. Place 20 DGs (10% penetration) ───────────────────────────────
    print(f"\n[5] Placing {DG_COUNT} Cat 3520 DGs (10% penetration)...")
    rng_dg   = random.Random(DG_SEED)
    dg_buses = rng_dg.sample(mv_buses, DG_COUNT)
    for bus in dg_buses:
        add_dg(bus)
    dss.Command("Solve")
    print(f"    DGs placed. Converged: {dss.Solution.Converged()}")

    # ── 6. Load smart meter list ─────────────────────────────────────────
    print("\n[6] Loading smart meter locations...")
    sm_list = load_smart_meters()
    print(f"    {len(sm_list)} smart meters loaded")

    # ── 7. Initialise fault slots ────────────────────────────────────────
    print("\n[7] Initialising reusable fault slots...")
    init_fault_slots(mv_buses[0])
    dss.Command("Solve")
    print(f"    Base with DGs + monitors converged: {dss.Solution.Converged()}")

    # ── 8. Simulation loop ───────────────────────────────────────────────
    rfi_cols   = [r for r, _ in RFI_LINES]
    sm_cols    = [sm[0] for sm in sm_list]
    fieldnames = META_COLS + rfi_cols + sm_cols

    clean_dir  = os.path.join(OUT_DIR, "clean")
    clean_path = os.path.join(clean_dir, "results.csv")
    os.makedirs(clean_dir, exist_ok=True)

    print(f"\n[8] Running {len(faults)} fault simulations...")
    rows         = []
    n_converged  = 0
    n_diverged   = 0

    with open(clean_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, fault in enumerate(faults):
            apply_fault(fault)
            dss.Command("Solve")
            converged = dss.Solution.Converged()

            row = {
                "fault_id":       fault["fault_id"],
                "fault_type":     fault["fault_type"],
                "fault_bus":      fault["fault_bus"],
                "zone":           fault["zone"],
                "impedance_type": fault["impedance_type"],
                "r_ground":       fault["r_ground"],
                "r_phase":        fault["r_phase"],
                "converged":      converged,
            }

            if converged:
                row.update(read_rfi_currents())
                row.update(read_smart_meter_voltages(sm_list))
                n_converged += 1
            else:
                row.update({c: "" for c in rfi_cols + sm_cols})
                n_diverged += 1

            clear_faults()
            writer.writerow(row)
            f.flush()
            rows.append(row)

            if (i + 1) % 100 == 0 or (i + 1) == len(faults):
                print(f"    {i + 1:4d}/{len(faults)}  "
                      f"({100*(i+1)/len(faults):.0f}%)  "
                      f"converged={n_converged}  diverged={n_diverged}")

    print(f"\n    Clean data saved  →  {clean_path}")
    print(f"    Converged: {n_converged}  |  Diverged (excluded from noise step): {n_diverged}")

    # ── 9. Generate degraded datasets ────────────────────────────────────
    print("\n[9] Generating degraded datasets (ANSI noise + SM dropout)...")
    clean_df = pd.DataFrame(rows)

    pct_label = f"{int(round(DROPOUT_RATE * 100)):02d}pct"
    out_dir   = os.path.join(OUT_DIR, f"Degraded_Dropout_{pct_label}")
    out_path  = os.path.join(out_dir, "results.csv")
    os.makedirs(out_dir, exist_ok=True)

    seed     = int(round(DROPOUT_RATE * 100)) * 1000
    degraded = apply_noise_and_dropout(clean_df, rfi_cols, sm_cols, DROPOUT_RATE, seed)
    degraded.to_csv(out_path, index=False)
    print(f"    Dropout {pct_label}  →  {out_path}")

    # ── 10. Summary ──────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("DONE")
    print(f"  Clean data : {clean_path}")
    print(f"  Degraded   : {out_path}")
    print(f"  Total outputs: 2 CSV files")
    print("=" * 65)


if __name__ == "__main__":
    main()
