"""
normal_operations_simulation.py
================================
EPRI Ckt7 -- Normal Operations Baseline (500 Samples)

Simulates the feeder under normal conditions (no fault) at four time-of-day
load levels. Applies the same ANSI/IEEE measurement noise and 10% smart meter
dropout as the fault simulation so the model sees a realistic "no fault" class.

Each sample = one AMI polling cycle under normal conditions:
  - Load level drawn randomly (overnight / morning / afternoon / peak)
  - Capacitor banks settle via controlmode=static
  - RFI zone currents and SM voltages read from OpenDSS
  - Proportional Gaussian noise applied (C57.13 CT + C12.1 meter + C12.20 SM)
  - 10% of SM readings randomly dropped (NaN) -- AMI last-gasp failure model

Output columns match fault_simulation_2000.py exactly so both CSVs can be
concatenated for training:
  fault_type = "no_fault"   zone = 0   fault_bus / impedance / r cols = ""

Outputs:
  Realistic_Simulation/Normal_Operations/clean/results.csv
  Realistic_Simulation/Normal_Operations/Degraded_Dropout_10pct/results.csv
"""

import opendssdirect as dss
import pandas as pd
import numpy as np
import csv
import os
import re
from collections import defaultdict, deque

# =============================================================================
# Configuration  (mirrors fault_simulation_2000.py)
# =============================================================================

DG_SEED  = 2025
DG_COUNT = 20
N_SAMPLES = 500

MASTER    = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
LOADS_DSS = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Loads_ckt7.dss"
SM_CSV    = r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv"
RFI_DSS   = (r"C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-"
             r"EPRITestCircuits-ckt7\RFI_Monitors.dss")
OUT_DIR   = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\Normal_Operations"

RFI_SIGMA    = np.sqrt((0.006 / 3) ** 2 + (0.007 / 3) ** 2)   # ~0.00307
SM_SIGMA     = 0.005 / 3                                         # ~0.001667
DROPOUT_RATE = 0.10
DEMAND_FACTOR = 0.80

LOAD_LEVELS = [
    (0.20, "overnight"),
    (0.50, "morning"),
    (0.75, "afternoon"),
    (1.00, "peak"),
]

CAPACITOR_NAMES = ["CP-NR-613", "CP-85W-900"]

MV_KV = 12470 / 1.7321 / 1000

RFI_LINES = [
    ("RFI1",  "215299"), ("RFI2",  "298366"), ("RFI3",  "157115"),
    ("RFI4",  "157152"), ("RFI5",  "157168"), ("RFI6",  "175038"),
    ("RFI7",  "255473"), ("RFI8",  "175060"), ("RFI9",  "175064"),
    ("RFI10", "175085"), ("RFI11", "175087"), ("RFI12", "182907"),
    ("RFI13", "182915"), ("RFI14", "157127"), ("RFI15", "318388"),
    ("RFI16", "175042"), ("RFI17", "262345"), ("RFI18", "174952"),
    ("RFI19", "175054"), ("RFI20", "255389"),
]

DG_KVA = 2000; DG_KW = 1600
DG_KV_HV = 12.47; DG_KV_LV = 0.48
DG_XHL = 11.13; DG_XDP = 0.1962; DG_XDPP = 0.1033; DG_XRDP = 11.90

META_COLS = [
    "sample_id", "fault_type", "fault_bus", "zone",
    "impedance_type", "r_ground", "r_phase",
    "load_level", "time_of_day",
    "cap_CP_NR_613", "cap_CP_85W_900",
    "converged",
]

# =============================================================================
# Helpers  (identical to fault_simulation_2000.py)
# =============================================================================

def get_3phase_mv_buses():
    buses = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if abs(dss.Bus.kVBase() - MV_KV) < 0.5 and dss.Bus.NumNodes() >= 3:
            buses.append(bus.upper())
    return sorted(buses)


def add_dg(bus):
    bus = bus.upper()
    dss.Command(
        f"New Transformer.XFM_{bus} phases=3 windings=2 "
        f"buses=[{bus}.1.2.3, DG_{bus}.1.2.3] "
        f"kVs=[{DG_KV_HV}, {DG_KV_LV}] kVAs=[{DG_KVA}, {DG_KVA}] "
        f"XHL={DG_XHL}"
    )
    dss.Command(
        f"New Generator.DG_{bus} bus1=DG_{bus}.1.2.3 "
        f"kV={DG_KV_LV} kW={DG_KW} kVA={DG_KVA} pf=1.0 "
        f"Xdp={DG_XDP} Xdpp={DG_XDPP} H=2 D=0 XRdp={DG_XRDP} "
        f"conn=wye"
    )


def initialize_load_kw():
    count = 0
    with open(LOADS_DSS) as f:
        for line in f:
            line = line.strip()
            if not line.startswith("New Load."):
                continue
            m_name  = re.search(r"New Load\.(\S+)", line)
            m_pf    = re.search(r"\bpf=([\d.]+)", line)
            m_xfkva = re.search(r"xfkVA=([\d.]+)", line)
            if not (m_name and m_xfkva):
                continue
            name    = m_name.group(1)
            pf      = float(m_pf.group(1)) if m_pf else 0.9
            xfkva   = float(m_xfkva.group(1))
            kw_peak = xfkva * pf * DEMAND_FACTOR
            dss.Command(f"Edit Load.{name} kW={kw_peak:.4f} status=variable")
            count += 1
    return count


def get_cap_states():
    states = {}
    for cap in CAPACITOR_NAMES:
        try:
            dss.Circuit.SetActiveElement(f"Capacitor.{cap}")
            cmag  = dss.CktElement.CurrentsMagAng()
            n     = dss.CktElement.NumPhases()
            max_i = max(cmag[2 * i] for i in range(n)) if n > 0 else 0.0
            states[cap] = max_i > 0.5
        except Exception:
            states[cap] = False
    return states


def load_smart_meters():
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


def read_rfi_currents():
    results = {}
    for rfi_label, line_name in RFI_LINES:
        dss.Circuit.SetActiveElement(f"Line.{line_name}")
        cmag = dss.CktElement.CurrentsMagAng()
        n    = dss.CktElement.NumPhases()
        mags = [cmag[2 * i] for i in range(n)]
        results[rfi_label] = max(mags) if mags else 0.0
    return results


def read_smart_meter_voltages(sm_list):
    results = {}
    for sm_id, bus, phase in sm_list:
        try:
            dss.Circuit.SetActiveBus(bus)
            vmag = dss.Bus.VMagAngle()
            kv   = dss.Bus.kVBase()
            if kv > 0 and vmag:
                idx  = max(0, (phase - 1) * 2)
                v_pu = (vmag[idx] / 1000) / kv if idx < len(vmag) else 0.0
            else:
                v_pu = 0.0
        except Exception:
            v_pu = 0.0
        results[sm_id] = v_pu
    return results


# =============================================================================
# Noise / dropout  (identical to fault_simulation_2000.py)
# =============================================================================

def _proportional_noise(vals, sigma_factor, rng):
    sigma      = sigma_factor * np.abs(vals)
    safe_sigma = np.where((sigma == 0) | np.isnan(sigma), 1.0, sigma)
    noise      = rng.normal(0.0, safe_sigma)
    noise      = np.where(np.isnan(vals) | (sigma == 0), 0.0, noise)
    return vals + noise


def apply_noise_and_dropout(df, rfi_cols, sm_cols, dropout_rate, seed):
    rng = np.random.default_rng(seed)
    out = df.copy()

    rfi_vals = out[rfi_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    sm_vals  = out[sm_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)

    out[rfi_cols] = _proportional_noise(rfi_vals, RFI_SIGMA, rng)
    out[sm_cols]  = _proportional_noise(sm_vals,  SM_SIGMA,  rng)

    n_rows, n_sm = len(out), len(sm_cols)
    mask         = rng.random((n_rows, n_sm)) < dropout_rate
    sm_noisy     = out[sm_cols].values.copy().astype(float)
    sm_noisy[mask] = np.nan
    out[sm_cols] = sm_noisy

    return out


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 65)
    print("EPRI Ckt7  --  Normal Operations Baseline  --  500 Samples")
    print(f"  DG seed: {DG_SEED}   DG count: {DG_COUNT}")
    print("=" * 65)

    # [1] Compile circuit
    print("\n[1] Compiling base circuit...")
    dss.Command(f"Redirect \"{MASTER}\"")
    dss.Command("Set VoltageBases=[115, 12.47, 0.48]")
    dss.Command("CalcVoltageBases")
    dss.Command("Solve")
    print(f"    Circuit : {dss.Circuit.Name()}")
    print(f"    Converged: {dss.Solution.Converged()}")

    # [2] Add RFI monitors
    print("\n[2] Adding RFI monitors...")
    dss.Command(f"Redirect \"{RFI_DSS}\"")

    # [3] Place DGs
    print(f"\n[3] Placing {DG_COUNT} Cat 3520 DGs (10% penetration)...")
    mv_buses = get_3phase_mv_buses()
    rng_dg   = np.random.default_rng(DG_SEED)
    dg_buses = list(rng_dg.choice(mv_buses, size=DG_COUNT, replace=False))
    for bus in dg_buses:
        add_dg(bus)
    dss.Command("Solve")
    print(f"    DGs placed. Converged: {dss.Solution.Converged()}")

    # [4] Initialise load kW
    print("\n[4] Initialising load kW values from transformer kVA...")
    n_loads = initialize_load_kw()
    print(f"    {n_loads} loads set to peak kW (demand factor {DEMAND_FACTOR})")

    # [5] Load smart meters
    print("\n[5] Loading smart meter locations...")
    sm_list = load_smart_meters()
    print(f"    {len(sm_list)} smart meters loaded")

    rfi_cols = [lbl for lbl, _ in RFI_LINES]
    sm_cols  = [sm_id for sm_id, _, _ in sm_list]

    # [6] Run 500 normal-operation samples
    print(f"\n[6] Running {N_SAMPLES} normal-operation samples...")
    rng_load = np.random.default_rng(DG_SEED + 1)

    clean_dir = os.path.join(OUT_DIR, "clean")
    os.makedirs(clean_dir, exist_ok=True)
    clean_path = os.path.join(clean_dir, "results.csv")

    all_cols = META_COLS + rfi_cols + sm_cols
    rows     = []

    with open(clean_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(all_cols)

        for i in range(N_SAMPLES):
            load_mult, time_label = LOAD_LEVELS[rng_load.integers(0, len(LOAD_LEVELS))]

            dss.Command(f"set loadmult={load_mult}")
            dss.Command("set controlmode=static")
            dss.Command("set maxcontroliter=100")
            dss.Command("Solve")

            cap_states = get_cap_states()

            dss.Command("set controlmode=off")
            dss.Command("Solve")

            converged = dss.Solution.Converged()
            rfi_data  = read_rfi_currents()
            sm_data   = read_smart_meter_voltages(sm_list)

            row = {
                "sample_id":      f"N{i + 1:04d}",
                "fault_type":     "no_fault",
                "fault_bus":      "",
                "zone":           0,
                "impedance_type": "",
                "r_ground":       "",
                "r_phase":        "",
                "load_level":     load_mult,
                "time_of_day":    time_label,
                "cap_CP_NR_613":  cap_states.get("CP-NR-613", False),
                "cap_CP_85W_900": cap_states.get("CP-85W-900", False),
                "converged":      converged,
            }
            row.update(rfi_data)
            row.update(sm_data)

            flat = [row[c] for c in all_cols]
            writer.writerow(flat)
            f.flush()
            rows.append(row)

            if (i + 1) % 50 == 0 or (i + 1) == N_SAMPLES:
                print(f"    {i + 1:3d}/{N_SAMPLES}  load={time_label:<9s}  "
                      f"caps={cap_states.get('CP-NR-613',False)}/{cap_states.get('CP-85W-900',False)}  "
                      f"converged={converged}")

    print(f"\n    Clean data saved -> {clean_path}")

    # [7] Generate degraded dataset
    print("\n[7] Generating degraded dataset (ANSI noise + 10% SM dropout)...")
    clean_df  = pd.DataFrame(rows)
    deg_dir   = os.path.join(OUT_DIR, "Degraded_Dropout_10pct")
    deg_path  = os.path.join(deg_dir, "results.csv")
    os.makedirs(deg_dir, exist_ok=True)

    seed     = int(round(DROPOUT_RATE * 100)) * 2000   # different seed from fault sim
    degraded = apply_noise_and_dropout(clean_df, rfi_cols, sm_cols, DROPOUT_RATE, seed)
    degraded.to_csv(deg_path, index=False)

    nan_count = degraded[sm_cols].isna().sum().sum()
    total_sm  = len(degraded) * len(sm_cols)
    print(f"    NaN SM cells: {nan_count}/{total_sm} ({100*nan_count/total_sm:.1f}%)")
    print(f"    Degraded data saved -> {deg_path}")

    print("\n" + "=" * 65)
    print("DONE")
    print(f"  Clean    : {clean_path}")
    print(f"  Degraded : {deg_path}")
    print(f"  Samples  : {N_SAMPLES}")
    print("=" * 65)


if __name__ == "__main__":
    main()
