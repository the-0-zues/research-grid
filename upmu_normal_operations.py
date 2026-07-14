"""
upmu_normal_operations.py
=========================
EPRI Ckt7 -- μPMU Normal Operations Baseline (500 Samples)

Simulates the feeder under normal conditions (no fault) at four time-of-day
load levels. Applies CT/VT + TVE measurement noise to PMU phasors and ANSI
C12.20 proportional noise to smart meter voltages. No smart meter dropout is
applied because no fault interrupts supply in this dataset.

Output columns match upmu_fault_simulation.py exactly so both CSVs can be
concatenated for training:
  fault_type = "no_fault"   zone = 0   fault_bus / impedance / r cols = ""

Outputs:
  Realistic_Simulation/uPMU_only/Normal_Operations/clean/results.csv
  Realistic_Simulation/uPMU_only/Normal_Operations/Degraded_NoiseOnly/results.csv

Noise model (IEEE C57.13-2016 Class 0.3 + IEEE C37.118.1-2011 TVE 0.1%):
  sigma_I_mag = sqrt((0.3%/3)^2 + (0.1%/sqrt(2))^2) ~= 0.1225%  proportional
  sigma_I_ang = sqrt((5 arcmin)^2 + (0.1%/sqrt(2))^2) ~= 0.0926 deg  absolute
  sigma_V_mag = sigma_I_mag  (VT Class 0.3 same as CT)
  sigma_V_ang = sigma_I_ang
  SM noise    = ANSI C12.20 Class 0.5: sigma = 0.5%/3 proportional
"""

import opendssdirect as dss
import pandas as pd
import numpy as np
import csv
import os
import re

# =============================================================================
# Configuration  (mirrors upmu_fault_simulation.py)
# =============================================================================

DG_SEED   = 2025
DG_COUNT  = 20
N_SAMPLES = 500

MASTER    = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
LOADS_DSS = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Loads_ckt7.dss"
SM_CSV    = r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv"
OUT_DIR   = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\uPMU_only\Normal_Operations"

# IEEE C57.13-2016 Class 0.3 CT/VT + IEEE C37.118.1-2011 TVE 0.1%
_CT_SIGMA_MAG = 0.003 / 3
_VT_SIGMA_MAG = 0.003 / 3
_TVE_COMP     = 0.001 / np.sqrt(2)
_CT_SIGMA_ANG = (15.0 / 3.0) * (np.pi / 180.0 / 60.0)
_VT_SIGMA_ANG = (15.0 / 3.0) * (np.pi / 180.0 / 60.0)

SIGMA_I_MAG     = float(np.sqrt(_CT_SIGMA_MAG**2 + _TVE_COMP**2))
SIGMA_I_ANG     = float(np.sqrt(_CT_SIGMA_ANG**2 + _TVE_COMP**2))
SIGMA_V_MAG     = float(np.sqrt(_VT_SIGMA_MAG**2 + _TVE_COMP**2))
SIGMA_V_ANG     = float(np.sqrt(_VT_SIGMA_ANG**2 + _TVE_COMP**2))
SIGMA_I_ANG_DEG = float(np.degrees(SIGMA_I_ANG))
SIGMA_V_ANG_DEG = float(np.degrees(SIGMA_V_ANG))

SM_SIGMA = 0.005 / 3   # ANSI C12.20 Class 0.5

DEMAND_FACTOR = 0.80

LOAD_LEVELS = [
    (0.20, "overnight"),
    (0.50, "morning"),
    (0.75, "afternoon"),
    (1.00, "peak"),
]

CAPACITOR_NAMES = ["CP-NR-613", "CP-85W-900"]
MV_KV = 12470 / 1.7321 / 1000

PMU_LINES = [
    ("PMU1",  "215299"), ("PMU2",  "298366"), ("PMU3",  "157115"),
    ("PMU4",  "157152"), ("PMU5",  "157168"), ("PMU6",  "175038"),
    ("PMU7",  "255473"), ("PMU8",  "175060"), ("PMU9",  "175064"),
    ("PMU10", "175085"), ("PMU11", "175087"), ("PMU12", "182907"),
    ("PMU13", "182915"), ("PMU14", "157127"), ("PMU15", "318388"),
    ("PMU16", "175042"), ("PMU17", "262345"), ("PMU18", "174952"),
    ("PMU19", "175054"), ("PMU20", "255389"),
]

_A_OP = np.exp(1j * 2 * np.pi / 3)

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


def _pmu_cols(label):
    return [
        f"{label}_Ia",     f"{label}_Ib",     f"{label}_Ic",
        f"{label}_Ia_ang", f"{label}_Ib_ang", f"{label}_Ic_ang",
        f"{label}_I0",     f"{label}_I1",     f"{label}_I2",
        f"{label}_Va",     f"{label}_Vb",     f"{label}_Vc",
        f"{label}_Va_ang", f"{label}_Vb_ang", f"{label}_Vc_ang",
        f"{label}_V0",     f"{label}_V1",     f"{label}_V2",
    ]


# =============================================================================
# Circuit helpers
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


# =============================================================================
# PMU reading
# =============================================================================

def read_pmu_measurements():
    results = {}
    for pmu_label, line_name in PMU_LINES:
        dss.Circuit.SetActiveElement(f"Line.{line_name}")
        cmag    = dss.CktElement.CurrentsMagAng()
        n_phase = dss.CktElement.NumPhases()

        ia,     ia_ang = (cmag[0],  cmag[1])  if n_phase >= 1 else (0.0, 0.0)
        ib,     ib_ang = (cmag[2],  cmag[3])  if n_phase >= 2 else (0.0, 0.0)
        ic,     ic_ang = (cmag[4],  cmag[5])  if n_phase >= 3 else (0.0, 0.0)

        Ia = ia * np.exp(1j * np.radians(ia_ang))
        Ib = ib * np.exp(1j * np.radians(ib_ang))
        Ic = ic * np.exp(1j * np.radians(ic_ang))
        i0 = abs((Ia + Ib + Ic) / 3)
        i1 = abs((Ia + _A_OP * Ib + _A_OP**2 * Ic) / 3)
        i2 = abs((Ia + _A_OP**2 * Ib + _A_OP * Ic) / 3)

        bus1 = dss.CktElement.BusNames()[0].split(".")[0]
        dss.Circuit.SetActiveBus(bus1)
        pv      = dss.Bus.puVmagAngle()
        n_nodes = len(pv) // 2

        va,     va_ang = (pv[0], pv[1]) if n_nodes >= 1 else (0.0, 0.0)
        vb,     vb_ang = (pv[2], pv[3]) if n_nodes >= 2 else (0.0, 0.0)
        vc,     vc_ang = (pv[4], pv[5]) if n_nodes >= 3 else (0.0, 0.0)

        Va = va * np.exp(1j * np.radians(va_ang))
        Vb = vb * np.exp(1j * np.radians(vb_ang))
        Vc = vc * np.exp(1j * np.radians(vc_ang))
        v0 = abs((Va + Vb + Vc) / 3)
        v1 = abs((Va + _A_OP * Vb + _A_OP**2 * Vc) / 3)
        v2 = abs((Va + _A_OP**2 * Vb + _A_OP * Vc) / 3)

        results.update({
            f"{pmu_label}_Ia":     ia,     f"{pmu_label}_Ib":     ib,
            f"{pmu_label}_Ic":     ic,     f"{pmu_label}_Ia_ang": ia_ang,
            f"{pmu_label}_Ib_ang": ib_ang, f"{pmu_label}_Ic_ang": ic_ang,
            f"{pmu_label}_I0":     i0,     f"{pmu_label}_I1":     i1,
            f"{pmu_label}_I2":     i2,     f"{pmu_label}_Va":     va,
            f"{pmu_label}_Vb":     vb,     f"{pmu_label}_Vc":     vc,
            f"{pmu_label}_Va_ang": va_ang, f"{pmu_label}_Vb_ang": vb_ang,
            f"{pmu_label}_Vc_ang": vc_ang, f"{pmu_label}_V0":     v0,
            f"{pmu_label}_V1":     v1,     f"{pmu_label}_V2":     v2,
        })
    return results


def read_smart_meter_voltages(sm_list):
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


# =============================================================================
# Noise  (no dropout — supply is uninterrupted under normal operation)
# =============================================================================

def _proportional_noise(vals, sigma_factor, rng):
    sigma      = sigma_factor * np.abs(vals)
    safe_sigma = np.where((sigma == 0) | np.isnan(sigma), 1.0, sigma)
    noise      = rng.normal(0.0, safe_sigma)
    noise      = np.where(np.isnan(vals) | (sigma == 0), 0.0, noise)
    return vals + noise


def _absolute_noise(vals, sigma, rng):
    noise = rng.normal(0.0, sigma, size=vals.shape)
    noise = np.where(np.isnan(vals), 0.0, noise)
    return vals + noise


def _recompute_sequence(df, pmu_labels):
    a = _A_OP
    for lbl in pmu_labels:
        Ia_m = pd.to_numeric(df[f"{lbl}_Ia"],     errors="coerce").values
        Ia_a = pd.to_numeric(df[f"{lbl}_Ia_ang"], errors="coerce").values
        Ib_m = pd.to_numeric(df[f"{lbl}_Ib"],     errors="coerce").values
        Ib_a = pd.to_numeric(df[f"{lbl}_Ib_ang"], errors="coerce").values
        Ic_m = pd.to_numeric(df[f"{lbl}_Ic"],     errors="coerce").values
        Ic_a = pd.to_numeric(df[f"{lbl}_Ic_ang"], errors="coerce").values

        Ia = Ia_m * np.exp(1j * np.radians(Ia_a))
        Ib = Ib_m * np.exp(1j * np.radians(Ib_a))
        Ic = Ic_m * np.exp(1j * np.radians(Ic_a))
        df[f"{lbl}_I0"] = np.abs((Ia + Ib + Ic) / 3)
        df[f"{lbl}_I1"] = np.abs((Ia + a * Ib + a**2 * Ic) / 3)
        df[f"{lbl}_I2"] = np.abs((Ia + a**2 * Ib + a * Ic) / 3)

        Va_m = pd.to_numeric(df[f"{lbl}_Va"],     errors="coerce").values
        Va_a = pd.to_numeric(df[f"{lbl}_Va_ang"], errors="coerce").values
        Vb_m = pd.to_numeric(df[f"{lbl}_Vb"],     errors="coerce").values
        Vb_a = pd.to_numeric(df[f"{lbl}_Vb_ang"], errors="coerce").values
        Vc_m = pd.to_numeric(df[f"{lbl}_Vc"],     errors="coerce").values
        Vc_a = pd.to_numeric(df[f"{lbl}_Vc_ang"], errors="coerce").values

        Va = Va_m * np.exp(1j * np.radians(Va_a))
        Vb = Vb_m * np.exp(1j * np.radians(Vb_a))
        Vc = Vc_m * np.exp(1j * np.radians(Vc_a))
        df[f"{lbl}_V0"] = np.abs((Va + Vb + Vc) / 3)
        df[f"{lbl}_V1"] = np.abs((Va + a * Vb + a**2 * Vc) / 3)
        df[f"{lbl}_V2"] = np.abs((Va + a**2 * Vb + a * Vc) / 3)

    return df


def apply_pmu_noise(df, pmu_labels, sm_cols, seed):
    """Apply instrument noise to PMU phasors and SM voltages. No dropout."""
    rng = np.random.default_rng(seed)
    out = df.copy()

    for lbl in pmu_labels:
        for col in [f"{lbl}_Ia", f"{lbl}_Ib", f"{lbl}_Ic"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _proportional_noise(v, SIGMA_I_MAG, rng)

        for col in [f"{lbl}_Ia_ang", f"{lbl}_Ib_ang", f"{lbl}_Ic_ang"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _absolute_noise(v, SIGMA_I_ANG_DEG, rng)

        for col in [f"{lbl}_Va", f"{lbl}_Vb", f"{lbl}_Vc"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _proportional_noise(v, SIGMA_V_MAG, rng)

        for col in [f"{lbl}_Va_ang", f"{lbl}_Vb_ang", f"{lbl}_Vc_ang"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _absolute_noise(v, SIGMA_V_ANG_DEG, rng)

    out = _recompute_sequence(out, pmu_labels)

    sm_vals = out[sm_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    out[sm_cols] = _proportional_noise(sm_vals, SM_SIGMA, rng)

    return out


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 65)
    print("EPRI Ckt7  --  uPMU Normal Operations  --  500 Samples")
    print(f"  DG seed: {DG_SEED}   DG count: {DG_COUNT}")
    print(f"  sigma_I_mag={SIGMA_I_MAG:.6f}  sigma_I_ang={SIGMA_I_ANG_DEG:.6f} deg")
    print(f"  sigma_V_mag={SIGMA_V_MAG:.6f}  sigma_V_ang={SIGMA_V_ANG_DEG:.6f} deg")
    print(f"  SM sigma={SM_SIGMA:.6f}  dropout=None (supply uninterrupted)")
    print("=" * 65)

    os.makedirs(OUT_DIR, exist_ok=True)

    # [1] Compile circuit
    print("\n[1] Compiling base circuit...")
    dss.Command(f"Redirect \"{MASTER}\"")
    dss.Command("Set VoltageBases=[115, 12.47, 0.48]")
    dss.Command("CalcVoltageBases")
    dss.Command("Solve")
    print(f"    Circuit : {dss.Circuit.Name()}")
    print(f"    Converged: {dss.Solution.Converged()}")

    # [2] Place DGs
    print(f"\n[2] Placing {DG_COUNT} Cat 3520 DGs (10% penetration)...")
    mv_buses = get_3phase_mv_buses()
    rng_dg   = np.random.default_rng(DG_SEED)
    dg_buses = list(rng_dg.choice(mv_buses, size=DG_COUNT, replace=False))
    for bus in dg_buses:
        add_dg(bus)
    dss.Command("Solve")
    print(f"    DGs placed. Converged: {dss.Solution.Converged()}")

    # [3] Initialise loads
    print("\n[3] Initialising load kW from transformer kVA...")
    n_loads = initialize_load_kw()
    print(f"    {n_loads} loads set to peak kW (demand factor {DEMAND_FACTOR})")

    # [4] Load smart meters
    print("\n[4] Loading smart meter locations...")
    sm_list = load_smart_meters()
    print(f"    {len(sm_list)} smart meters loaded")

    pmu_labels   = [lbl for lbl, _ in PMU_LINES]
    all_pmu_cols = []
    for lbl in pmu_labels:
        all_pmu_cols.extend(_pmu_cols(lbl))
    sm_cols    = [sm[0] for sm in sm_list]
    fieldnames = META_COLS + all_pmu_cols + sm_cols

    # [5] Run 500 normal-operation samples
    print(f"\n[5] Running {N_SAMPLES} normal-operation samples...")
    rng_load  = np.random.default_rng(DG_SEED + 1)
    clean_dir = os.path.join(OUT_DIR, "clean")
    os.makedirs(clean_dir, exist_ok=True)
    clean_path = os.path.join(clean_dir, "results.csv")

    rows = []

    with open(clean_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

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
                "cap_CP_NR_613":  cap_states.get("CP-NR-613",  False),
                "cap_CP_85W_900": cap_states.get("CP-85W-900", False),
                "converged":      converged,
            }

            if converged:
                row.update(read_pmu_measurements())
                row.update(read_smart_meter_voltages(sm_list))
            else:
                row.update({c: "" for c in all_pmu_cols + sm_cols})

            writer.writerow(row)
            f.flush()
            rows.append(row)

            if (i + 1) % 50 == 0 or (i + 1) == N_SAMPLES:
                print(f"    {i + 1:3d}/{N_SAMPLES}  load={time_label:<9s}  "
                      f"caps={cap_states.get('CP-NR-613', False)}/"
                      f"{cap_states.get('CP-85W-900', False)}  "
                      f"converged={converged}")

    print(f"\n    Clean data saved -> {clean_path}")

    # [6] Generate noise-only degraded dataset (no dropout)
    print("\n[6] Generating Degraded_NoiseOnly dataset (PMU + SM noise, no dropout)...")
    clean_df  = pd.DataFrame(rows)
    deg_dir   = os.path.join(OUT_DIR, "Degraded_NoiseOnly")
    deg_path  = os.path.join(deg_dir, "results.csv")
    os.makedirs(deg_dir, exist_ok=True)

    seed    = int(round(DG_SEED)) * 1000
    noisy   = apply_pmu_noise(clean_df, pmu_labels, sm_cols, seed)
    noisy.to_csv(deg_path, index=False)
    print(f"    Degraded data saved -> {deg_path}")

    cols_total = len(fieldnames)
    print("\n" + "=" * 65)
    print("DONE")
    print(f"  Clean         : {clean_path}")
    print(f"  Degraded      : {deg_path}")
    print(f"  Samples       : {N_SAMPLES}")
    print(f"  Columns       : {cols_total}  (12 meta + 360 PMU + 867 SM)")
    print(f"  SM dropout    : None")
    print("=" * 65)


if __name__ == "__main__":
    main()
