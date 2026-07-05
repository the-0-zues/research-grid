"""
normal_operations_rfi_perphase.py
===================================
EPRI Ckt7 -- Normal Operations, Per-Phase RFI Currents (500 Samples)

Reports individual phase currents (A, B, C) at each of the 20 RFI zone
boundaries -- 60 RFI features total. No smart meters, no dropout.

Each sample:
  - Load level drawn randomly (overnight / morning / afternoon / peak)
  - Capacitor banks settle via controlmode=static
  - Phase A, B, C current magnitude read independently at each RFI line
  - Independent proportional Gaussian noise applied per phase per zone
    (each CT is a separate physical device with its own measurement error)
    Sigma: RSS of IEEE C57.13-2016 Class 0.6 CT + ANSI C12.1-2022 Class 0.5

Outputs:
  Realistic_Simulation/Normal_Operations/RFI_PerPhase/clean/results.csv
  Realistic_Simulation/Normal_Operations/RFI_PerPhase/Degraded_NoiseOnly/results.csv
"""

import opendssdirect as dss
import pandas as pd
import numpy as np
import csv
import os
import re

# =============================================================================
# Configuration
# =============================================================================

DG_SEED   = 2025
DG_COUNT  = 20
N_SAMPLES = 500

MASTER    = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
LOADS_DSS = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Loads_ckt7.dss"
RFI_DSS   = (r"C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-"
             r"EPRITestCircuits-ckt7\RFI_Monitors.dss")
OUT_DIR   = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\Normal_Operations\RFI_PerPhase"

# RSS of IEEE C57.13-2016 Class 0.6 CT (0.6%/3) and ANSI C12.1-2022 (0.7%/3)
RFI_SIGMA    = np.sqrt((0.006 / 3) ** 2 + (0.007 / 3) ** 2)
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

# Build column names: RFI1_A, RFI1_B, RFI1_C, RFI2_A, ...
RFI_COLS = [f"{lbl}_{ph}" for lbl, _ in RFI_LINES for ph in ("A", "B", "C")]

META_COLS = [
    "sample_id", "load_level", "time_of_day",
    "cap_CP_NR_613", "cap_CP_85W_900", "converged",
]

# =============================================================================
# Helpers
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
        f"Xdp={DG_XDP} Xdpp={DG_XDPP} H=2 D=0 XRdp={DG_XRDP} conn=wye"
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


def read_rfi_perphase():
    """
    Read phase A, B, C current magnitudes (A) at each RFI zone boundary.
    Returns dict: RFIx_A, RFIx_B, RFIx_C -> float
    """
    results = {}
    for rfi_label, line_name in RFI_LINES:
        dss.Circuit.SetActiveElement(f"Line.{line_name}")
        cmag   = dss.CktElement.CurrentsMagAng()
        n      = dss.CktElement.NumPhases()
        # cmag layout: [mag_A, ang_A, mag_B, ang_B, mag_C, ang_C, ...]
        ph_A = cmag[0] if n >= 1 else 0.0
        ph_B = cmag[2] if n >= 2 else 0.0
        ph_C = cmag[4] if n >= 3 else 0.0
        results[f"{rfi_label}_A"] = ph_A
        results[f"{rfi_label}_B"] = ph_B
        results[f"{rfi_label}_C"] = ph_C
    return results


# =============================================================================
# Noise (no dropout -- meters online under normal conditions)
# =============================================================================

def apply_noise(df, rfi_cols, seed):
    """Apply independent proportional Gaussian noise to each RFI phase column."""
    rng = np.random.default_rng(seed)
    out = df.copy()
    vals = out[rfi_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    sigma     = RFI_SIGMA * np.abs(vals)
    safe      = np.where((sigma == 0) | np.isnan(sigma), 1.0, sigma)
    noise     = rng.normal(0.0, safe)
    noise     = np.where(np.isnan(vals) | (sigma == 0), 0.0, noise)
    out[rfi_cols] = vals + noise
    return out


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 65)
    print("EPRI Ckt7  --  Normal Operations, Per-Phase RFI  --  500 Samples")
    print(f"  DG seed: {DG_SEED}   DG count: {DG_COUNT}   RFI features: {len(RFI_COLS)}")
    print("=" * 65)

    # [1] Compile circuit
    print("\n[1] Compiling base circuit...")
    dss.Command(f"Redirect \"{MASTER}\"")
    dss.Command("Set VoltageBases=[115, 12.47, 0.48]")
    dss.Command("CalcVoltageBases")
    dss.Command("Solve")
    print(f"    Converged: {dss.Solution.Converged()}")

    # [2] RFI monitors
    print("\n[2] Adding RFI monitors...")
    dss.Command(f"Redirect \"{RFI_DSS}\"")

    # [3] Place DGs
    print(f"\n[3] Placing {DG_COUNT} DGs...")
    mv_buses = get_3phase_mv_buses()
    rng_dg   = np.random.default_rng(DG_SEED)
    dg_buses = list(rng_dg.choice(mv_buses, size=DG_COUNT, replace=False))
    for bus in dg_buses:
        add_dg(bus)
    dss.Command("Solve")
    print(f"    Converged: {dss.Solution.Converged()}")

    # [4] Initialise load kW
    print("\n[4] Initialising load kW from transformer kVA...")
    n = initialize_load_kw()
    print(f"    {n} loads set")

    # [5] Run samples
    print(f"\n[5] Running {N_SAMPLES} samples...")
    rng_load = np.random.default_rng(DG_SEED + 1)

    clean_dir = os.path.join(OUT_DIR, "clean")
    os.makedirs(clean_dir, exist_ok=True)
    clean_path = os.path.join(clean_dir, "results.csv")

    all_cols = META_COLS + RFI_COLS
    rows = []

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
            rfi_data  = read_rfi_perphase()

            row = {
                "sample_id":      f"N{i + 1:04d}",
                "load_level":     load_mult,
                "time_of_day":    time_label,
                "cap_CP_NR_613":  cap_states.get("CP-NR-613", False),
                "cap_CP_85W_900": cap_states.get("CP-85W-900", False),
                "converged":      converged,
            }
            row.update(rfi_data)

            writer.writerow([row[c] for c in all_cols])
            f.flush()
            rows.append(row)

            if (i + 1) % 50 == 0 or (i + 1) == N_SAMPLES:
                print(f"    {i + 1:3d}/{N_SAMPLES}  {time_label:<9s}  "
                      f"caps={cap_states.get('CP-NR-613',False)}/{cap_states.get('CP-85W-900',False)}")

    print(f"\n    Clean saved -> {clean_path}")

    # [6] Apply noise (no dropout)
    print("\n[6] Applying ANSI/IEEE noise (no dropout)...")
    clean_df = pd.DataFrame(rows)
    deg_dir  = os.path.join(OUT_DIR, "Degraded_NoiseOnly")
    deg_path = os.path.join(deg_dir, "results.csv")
    os.makedirs(deg_dir, exist_ok=True)

    degraded = apply_noise(clean_df, RFI_COLS, seed=30000)
    degraded.to_csv(deg_path, index=False)
    print(f"    Degraded saved -> {deg_path}")

    print("\n" + "=" * 65)
    print("DONE")
    print(f"  RFI features : {len(RFI_COLS)} (20 zones x 3 phases)")
    print(f"  Samples      : {N_SAMPLES}")
    print(f"  Clean        : {clean_path}")
    print(f"  Degraded     : {deg_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()
