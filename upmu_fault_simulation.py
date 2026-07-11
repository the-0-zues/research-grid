"""
upmu_fault_simulation.py
========================
EPRI Ckt7 - Micro-PMU Fault Simulation (2,000 Events) + Ablation Study

Replaces the 20 RFIs with 20 micro-PMUs measuring per-phase current and
voltage phasors plus symmetrical components at 20 zone boundaries.

Noise model (IEEE C57.13-2016 Class 0.3 + IEEE C37.118.1-2011 TVE 0.1%):
  sigma_I_mag = sqrt((0.3%/3)^2 + (0.1%/sqrt(2))^2) ~= 0.1225%  proportional
  sigma_I_ang = sqrt((5 arcmin)^2 + (0.1%/sqrt(2))^2) ~= 0.0926 deg  absolute
  sigma_V_mag = sigma_I_mag  (VT Class 0.3 same as CT)
  sigma_V_ang = sigma_I_ang

Ablation output (21 total CSV files):
  clean/results.csv           -- all 20 PMUs, no noise
  20_PMUs/results.csv         -- all 20 PMUs with noise + 10% SM dropout
  19_PMUs/results.csv         -- PMUs 1-19 active (PMU20 removed)
  ...
  01_PMUs/results.csv         -- only PMU1 active

DG/fault/SM setup identical to fault_simulation_2000.py:
  - 10% penetration: 20 Cat 3520 generators, same seeds, same buses
  - Exact 2000-fault list (same bus, type, impedance per event)
  - 10% SM dropout, same noise seed formula
"""

import opendssdirect as dss
import pandas as pd
import numpy as np
import random
import csv
import os
from collections import defaultdict, deque, Counter

# =============================================================================
# Configuration
# =============================================================================

DG_SEED    = 2025
FAULT_SEED = 2025
DG_COUNT   = 20      # 10% of 203 three-phase MV buses

MASTER    = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_sim.dss"
LOADS_DSS = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Loads_ckt7.dss"
SM_CSV    = r"C:\EPRI_Ckt7_DER_Project\smart_meter_locations.csv"
OUT_DIR   = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\uPMU_only"

R_WET_GRASS = 144.0
R_DRY_GRASS = 288.0
R_PHASE_ARC = 2.0

# IEEE C57.13-2016 Class 0.3 CT/VT + IEEE C37.118.1-2011 TVE 0.1%
_CT_SIGMA_MAG = 0.003 / 3                                     # 0.3% max / 3 -> 1-sigma
_VT_SIGMA_MAG = 0.003 / 3
_TVE_COMP     = 0.001 / np.sqrt(2)                            # TVE 0.1% split equally
_CT_SIGMA_ANG = (15.0 / 3.0) * (np.pi / 180.0 / 60.0)       # 15 arcmin max / 3 -> 1-sigma rad
_VT_SIGMA_ANG = (15.0 / 3.0) * (np.pi / 180.0 / 60.0)

SIGMA_I_MAG     = float(np.sqrt(_CT_SIGMA_MAG**2 + _TVE_COMP**2))   # ~0.001225
SIGMA_I_ANG     = float(np.sqrt(_CT_SIGMA_ANG**2 + _TVE_COMP**2))   # ~1.617e-3 rad
SIGMA_V_MAG     = float(np.sqrt(_VT_SIGMA_MAG**2 + _TVE_COMP**2))
SIGMA_V_ANG     = float(np.sqrt(_VT_SIGMA_ANG**2 + _TVE_COMP**2))
SIGMA_I_ANG_DEG = float(np.degrees(SIGMA_I_ANG))   # ~0.0926 deg
SIGMA_V_ANG_DEG = float(np.degrees(SIGMA_V_ANG))

SM_SIGMA     = 0.005 / 3    # ANSI C12.20 Class 0.5
DROPOUT_RATE = 0.10

LOAD_LEVELS = [
    (0.20, "overnight"),
    (0.50, "morning"),
    (0.75, "afternoon"),
    (1.00, "peak"),
]

DEMAND_FACTOR   = 0.80
CAPACITOR_NAMES = ["CP-NR-613", "CP-85W-900"]
MV_KV = 12470 / 1.7321 / 1000   # line-to-neutral kV for 12.47 kV system

N_PMUS = 20

PMU_LINES = [
    ("PMU1",  "215299"), ("PMU2",  "298366"), ("PMU3",  "157115"),
    ("PMU4",  "157152"), ("PMU5",  "157168"), ("PMU6",  "175038"),
    ("PMU7",  "255473"), ("PMU8",  "175060"), ("PMU9",  "175064"),
    ("PMU10", "175085"), ("PMU11", "175087"), ("PMU12", "182907"),
    ("PMU13", "182915"), ("PMU14", "157127"), ("PMU15", "318388"),
    ("PMU16", "175042"), ("PMU17", "262345"), ("PMU18", "174952"),
    ("PMU19", "175054"), ("PMU20", "255389"),
]

_A_OP = np.exp(1j * 2 * np.pi / 3)   # 120-degree rotation operator

# Cat 3520 synchronous generator parameters
DG_KVA   = 2000;  DG_KW   = 1600
DG_KV_HV = 12.47; DG_KV_LV = 0.48
DG_XHL   = 11.13; DG_XDP  = 0.1962; DG_XDPP = 0.1033; DG_XRDP = 11.90

META_COLS = [
    "fault_id", "fault_type", "fault_bus", "zone",
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
# Topology helpers
# =============================================================================

def get_3phase_mv_buses():
    buses = []
    for bus in dss.Circuit.AllBusNames():
        dss.Circuit.SetActiveBus(bus)
        if abs(dss.Bus.kVBase() - MV_KV) < 0.5 and dss.Bus.NumNodes() >= 3:
            buses.append(bus.upper())
    return sorted(buses)


def build_mv_adjacency(mv_bus_set):
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
    pmu_line_set    = {ln.upper() for _, ln in PMU_LINES}
    pmu_line_to_idx = {ln.upper(): i for i, (_, ln) in enumerate(PMU_LINES)}

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
            next_zone = pmu_line_to_idx[line_name] + 1 if line_name in pmu_line_set else zone
            if neighbor not in visited_buses:
                visited_buses.add(neighbor)
                bus_zone[neighbor] = next_zone
                queue.append((neighbor, next_zone))

    return bus_zone


# =============================================================================
# Load initialisation and capacitor state helpers
# =============================================================================

def initialize_load_kw():
    import re
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


# =============================================================================
# Fault list construction (verbatim from fault_simulation_2000.py)
# =============================================================================

def build_fault_list(mv_buses, bus_zone, seed=FAULT_SEED):
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

    add_slg("A",  n_wet=233, n_dry=233)
    add_slg("B",  n_wet=234, n_dry=233)
    add_slg("C",  n_wet=234, n_dry=233)
    add_ll("AB",  100)
    add_ll("BC",  100)
    add_ll("CA",  100)
    add_llg("AB", n_wet=33,  n_dry=33)
    add_llg("BC", n_wet=34,  n_dry=33)
    add_llg("AC", n_wet=34,  n_dry=33)
    add_3ph(100)

    rng.shuffle(faults)
    for i, f in enumerate(faults):
        f["fault_id"] = f"F{i + 1:04d}"

    return faults


# =============================================================================
# DG and fault element helpers
# =============================================================================

def add_dg(bus):
    bus = bus.upper()
    lv  = f"DG_{bus}_LV"
    dss.Command(f"New Transformer.T_DG_{bus} phases=3 windings=2 XHL={DG_XHL}")
    dss.Command(f"~ wdg=1 bus={bus}.1.2.3.0 conn=wye   kV={DG_KV_HV} kVA={DG_KVA} %R=0")
    dss.Command(f"~ wdg=2 bus={lv}.1.2.3   conn=delta kV={DG_KV_LV}  kVA={DG_KVA} %R=0")
    dss.Command(f"New Generator.G_DG_{bus} phases=3 bus1={lv}.1.2.3 conn=delta")
    dss.Command(f"~ kV={DG_KV_LV} kW={DG_KW} kvar=0 kVA={DG_KVA} model=1 status=fixed")
    dss.Command(f"~ Xdp={DG_XDP} Xdpp={DG_XDPP} XRdp={DG_XRDP}")


def init_fault_slots(anchor_bus):
    b = anchor_bus
    for slot in ["FLT_S1", "FLT_S2", "FLT_S3"]:
        dss.Command(
            f"New Fault.{slot} Bus1={b}.1 Bus2={b}.0 phases=1 r=1 enabled=false"
        )


def apply_fault(fault):
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
    dss.Command("Edit Fault.FLT_S1 enabled=false")
    dss.Command("Edit Fault.FLT_S2 enabled=false")
    dss.Command("Edit Fault.FLT_S3 enabled=false")


# =============================================================================
# PMU measurement reading
# =============================================================================

def read_pmu_measurements():
    """
    Read per-phase current and voltage phasors from each PMU line.
    Currents via CktElement.CurrentsMagAng() at terminal 1.
    Voltages via Bus.puVmagAngle() at bus1 of each line (per-unit).
    Symmetrical components computed from clean phasors inline.
    """
    results = {}
    for pmu_label, line_name in PMU_LINES:
        dss.Circuit.SetActiveElement(f"Line.{line_name}")
        cmag = dss.CktElement.CurrentsMagAng()
        n_ph = dss.CktElement.NumPhases()
        bus1 = dss.CktElement.BusNames()[0].split(".")[0]

        ia,  ia_ang = (cmag[0], cmag[1]) if n_ph >= 1 else (0.0, 0.0)
        ib,  ib_ang = (cmag[2], cmag[3]) if n_ph >= 2 else (0.0, 0.0)
        ic,  ic_ang = (cmag[4], cmag[5]) if n_ph >= 3 else (0.0, 0.0)

        Ia = ia * np.exp(1j * np.radians(ia_ang))
        Ib = ib * np.exp(1j * np.radians(ib_ang))
        Ic = ic * np.exp(1j * np.radians(ic_ang))
        i0 = abs((Ia + Ib + Ic) / 3)
        i1 = abs((Ia + _A_OP * Ib + _A_OP**2 * Ic) / 3)
        i2 = abs((Ia + _A_OP**2 * Ib + _A_OP * Ic) / 3)

        dss.Circuit.SetActiveBus(bus1)
        pv      = dss.Bus.puVmagAngle()
        n_nodes = len(pv) // 2

        va, va_ang = (pv[0], pv[1]) if n_nodes >= 1 else (0.0, 0.0)
        vb, vb_ang = (pv[2], pv[3]) if n_nodes >= 2 else (0.0, 0.0)
        vc, vc_ang = (pv[4], pv[5]) if n_nodes >= 3 else (0.0, 0.0)

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


# =============================================================================
# Smart meter reading
# =============================================================================

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
# Noise, sequence recomputation, and dropout
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
    """Overwrite I0/I1/I2 and V0/V1/V2 columns from current noisy phasors."""
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


def apply_pmu_noise_and_sm_dropout(df, pmu_labels, sm_cols, dropout_rate, seed):
    """
    Apply CT/VT Class 0.3 + TVE 0.1% noise to PMU phasors, recompute sequence
    components from noisy phasors, then apply SM proportional noise + dropout.
    """
    rng = np.random.default_rng(seed)
    out = df.copy()

    for lbl in pmu_labels:
        # Current magnitudes: proportional noise
        for col in [f"{lbl}_Ia", f"{lbl}_Ib", f"{lbl}_Ic"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _proportional_noise(v, SIGMA_I_MAG, rng)

        # Current angles: absolute noise (degrees)
        for col in [f"{lbl}_Ia_ang", f"{lbl}_Ib_ang", f"{lbl}_Ic_ang"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _absolute_noise(v, SIGMA_I_ANG_DEG, rng)

        # Voltage magnitudes: proportional noise
        for col in [f"{lbl}_Va", f"{lbl}_Vb", f"{lbl}_Vc"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _proportional_noise(v, SIGMA_V_MAG, rng)

        # Voltage angles: absolute noise (degrees)
        for col in [f"{lbl}_Va_ang", f"{lbl}_Vb_ang", f"{lbl}_Vc_ang"]:
            v = pd.to_numeric(out[col], errors="coerce").values.astype(float)
            out[col] = _absolute_noise(v, SIGMA_V_ANG_DEG, rng)

    # Recompute sequence components from noisy phasors
    out = _recompute_sequence(out, pmu_labels)

    # Smart meter: proportional noise then dropout
    sm_vals = out[sm_cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    out[sm_cols] = _proportional_noise(sm_vals, SM_SIGMA, rng)

    n_rows, n_sm = len(out), len(sm_cols)
    dropout_mask = rng.random((n_rows, n_sm)) < dropout_rate
    sm_noisy = out[sm_cols].values.copy().astype(float)
    sm_noisy[dropout_mask] = np.nan
    out[sm_cols] = sm_noisy

    return out


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 65)
    print("EPRI Ckt7  -  Micro-PMU Fault Simulation  -  2,000 Events")
    print(f"  DG seed: {DG_SEED}   Fault seed: {FAULT_SEED}   DG count: {DG_COUNT}")
    print(f"  PMUs: {N_PMUS}   CT/VT Class 0.3 + TVE 0.1%")
    print(f"  sigma_I_mag={SIGMA_I_MAG:.6f}  sigma_I_ang={SIGMA_I_ANG_DEG:.6f} deg")
    print(f"  sigma_V_mag={SIGMA_V_MAG:.6f}  sigma_V_ang={SIGMA_V_ANG_DEG:.6f} deg")
    print("=" * 65)

    os.makedirs(OUT_DIR, exist_ok=True)

    # -- 1. Compile base circuit --
    print("\n[1] Compiling base circuit...")
    dss.Basic.Start(0)
    dss.Command(f"Compile [{MASTER}]")
    dss.Command("Solve")
    print(f"    Circuit : {dss.Circuit.Name()}")
    print(f"    Converged: {dss.Solution.Converged()}")

    # -- 2. Build topology --
    print("\n[2] Building MV topology and zone map...")
    mv_buses    = get_3phase_mv_buses()
    mv_bus_set  = set(mv_buses)
    adj, _      = build_mv_adjacency(mv_bus_set)
    bus_zone    = build_bus_zone_map(adj, mv_bus_set)
    print(f"    Three-phase MV buses : {len(mv_buses)}")
    zone_counts = Counter(bus_zone.values())
    print(f"    Zones covered        : {sorted(zone_counts.keys())}")

    # -- 3. Build fault list --
    print("\n[3] Building 2,000-fault event list...")
    faults = build_fault_list(mv_buses, bus_zone)
    dist   = Counter(f["fault_type"] for f in faults)
    print(f"    Total: {len(faults)} faults")
    for ft in sorted(dist):
        print(f"      {ft:<14}: {dist[ft]:4d}")

    # -- 4. Place DGs --
    print(f"\n[4] Placing {DG_COUNT} Cat 3520 DGs (10% penetration)...")
    rng_dg   = random.Random(DG_SEED)
    dg_buses = rng_dg.sample(mv_buses, DG_COUNT)
    for bus in dg_buses:
        add_dg(bus)
    dss.Command("Solve")
    print(f"    DGs placed. Converged: {dss.Solution.Converged()}")

    # -- 5. Initialise load kW --
    print("\n[5] Initialising load kW values from transformer kVA...")
    n_loads = initialize_load_kw()
    print(f"    {n_loads} loads set to peak kW (demand factor {DEMAND_FACTOR})")

    # -- 6. Load smart meter list --
    print("\n[6] Loading smart meter locations...")
    sm_list = load_smart_meters()
    print(f"    {len(sm_list)} smart meters loaded")

    # -- 7. Initialise fault slots --
    print("\n[7] Initialising reusable fault slots...")
    init_fault_slots(mv_buses[0])
    dss.Command("set controlmode=static")
    dss.Command("set maxcontroliter=100")
    dss.Command("Solve")
    print(f"    Base with DGs converged: {dss.Solution.Converged()}")

    # -- 8. Simulation loop --
    pmu_labels   = [lbl for lbl, _ in PMU_LINES]
    all_pmu_cols = []
    for lbl in pmu_labels:
        all_pmu_cols.extend(_pmu_cols(lbl))
    sm_cols    = [sm[0] for sm in sm_list]
    fieldnames = META_COLS + all_pmu_cols + sm_cols
    rng_load   = random.Random(FAULT_SEED + 1)

    clean_dir  = os.path.join(OUT_DIR, "clean")
    clean_path = os.path.join(clean_dir, "results.csv")
    os.makedirs(clean_dir, exist_ok=True)

    print(f"\n[8] Running {len(faults)} fault simulations...")
    rows        = []
    n_converged = 0
    n_diverged  = 0

    with open(clean_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, fault in enumerate(faults):
            load_mult, time_label = rng_load.choice(LOAD_LEVELS)

            dss.Command(f"set loadmult={load_mult}")
            dss.Command("set controlmode=static")
            dss.Command("set maxcontroliter=100")
            dss.Command("Solve")

            cap_states = get_cap_states()
            dss.Command("set controlmode=off")

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
                "load_level":     load_mult,
                "time_of_day":    time_label,
                "cap_CP_NR_613":  cap_states.get("CP-NR-613",  False),
                "cap_CP_85W_900": cap_states.get("CP-85W-900", False),
                "converged":      converged,
            }

            if converged:
                row.update(read_pmu_measurements())
                row.update(read_smart_meter_voltages(sm_list))
                n_converged += 1
            else:
                row.update({c: "" for c in all_pmu_cols + sm_cols})
                n_diverged += 1

            clear_faults()
            writer.writerow(row)
            f.flush()
            rows.append(row)

            if (i + 1) % 100 == 0 or (i + 1) == len(faults):
                print(f"    {i + 1:4d}/{len(faults)}  "
                      f"({100*(i+1)/len(faults):.0f}%)  "
                      f"converged={n_converged}  diverged={n_diverged}")

    print(f"\n    Clean data saved -> {clean_path}")
    print(f"    Converged: {n_converged}  |  Diverged: {n_diverged}")

    # -- 9. Generate degraded + ablation datasets --
    print("\n[9] Generating degraded and ablation datasets...")
    clean_df = pd.DataFrame(rows)

    seed          = int(round(DROPOUT_RATE * 100)) * 1000   # 10000
    degraded_full = apply_pmu_noise_and_sm_dropout(
        clean_df, pmu_labels, sm_cols, DROPOUT_RATE, seed
    )
    print(f"    Noise + dropout applied (seed={seed})")

    for n_active in range(N_PMUS, 0, -1):
        active_labels = pmu_labels[:n_active]
        active_cols   = []
        for lbl in active_labels:
            active_cols.extend(_pmu_cols(lbl))
        out_cols  = META_COLS + active_cols + sm_cols
        folder    = os.path.join(OUT_DIR, f"{n_active:02d}_PMUs")
        os.makedirs(folder, exist_ok=True)
        degraded_full[out_cols].to_csv(
            os.path.join(folder, "results.csv"), index=False
        )
        print(f"    {n_active:02d}_PMUs ({n_active*18} PMU features) -> {folder}")

    # -- 10. Summary --
    total_cols_max = len(META_COLS) + N_PMUS * 18 + len(sm_cols)
    print("\n" + "=" * 65)
    print("DONE")
    print(f"  Clean (no noise) : {clean_path}")
    print(f"  Degraded datasets: 20_PMUs/ down to 01_PMUs/")
    print(f"  Max columns      : {total_cols_max}  "
          f"(12 meta + {N_PMUS*18} PMU + {len(sm_cols)} SM)")
    print(f"  Total CSV outputs: {N_PMUS + 1}")
    print("=" * 65)


if __name__ == "__main__":
    main()
