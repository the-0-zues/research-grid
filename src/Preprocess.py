"""
preprocess.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Pipeline stages:
  1. Load raw OpenDSS simulation exports (baseline + post-fault pairs)
  2. Extract delta features (post-fault minus baseline) per monitor
  3. Apply smart meter dropout using 0.5 pu voltage threshold (physics-based)
  4. Inject Gaussian measurement noise (bounded by IEEE C57.13-2016 accuracy classes)
  5. Wire in RFI threshold table (monitor → feeder line mapping)
  6. Assemble labeled feature matrix for RF/SVM training

Change log vs. original:
  FIX 1 — Dropout now uses actual 0.5 pu voltage threshold from smart meter CSV
           instead of random 50% zeroing. A meter goes offline if its post-fault
           voltage magnitude falls below 0.5 × nominal kV at that bus.
  FIX 2 — Feature extraction now computes delta features (post-fault minus baseline)
           rather than raw statistical features on post-fault data alone. This gives
           the classifier a direct fault signature rather than absolute signal levels.
  FIX 3 — RFI threshold table (rfi_thresholds_2x_with_RFI20_25A.csv) is now loaded
           and wired in. Each monitor's normal current and 2x pickup threshold are
           available as metadata and as additional features.
"""

import numpy as np
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# STAGE 0 — Load supporting lookup tables
# ---------------------------------------------------------------------------

def load_smart_meter_registry(filepath: str) -> pd.DataFrame:
    """
    Load the smart meter inventory CSV (smart_meter_locations.csv).
    867 rows — one per meter. Key columns:
      SmartMeter_ID, Bus1, Base_Bus, Phases, kV, kW, pf, xfkVA

    The kV column gives nominal voltage at each meter's bus.
    Used by apply_dropout_pu() to compute the 0.5 pu threshold per meter.
    """
    df = pd.read_csv(filepath)
    required = ["SmartMeter_ID", "Bus1", "Base_Bus", "kV"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in smart meter registry: {missing}")
    return df


def load_rfi_thresholds(filepath: str) -> pd.DataFrame:
    """
    FIX 3 — Load the RFI threshold table (rfi_thresholds_2x_with_RFI20_25A.csv).

    This table maps each of the 20 RFI monitors to:
      - The feeder line it sits on (e.g. Line.215299)
      - Normal operating current (A)
      - 2x pickup threshold current (A) — used to flag fault inception

    These values become additional features for the classifier and provide
    the monitor → feeder line mapping needed for zone assignment once Olt
    provides a zone map.

    Expected columns (adjust if Olt's file differs):
      rfi_id, line_name, normal_current_A, threshold_2x_A
    """
    df = pd.read_csv(filepath)
    print(f"  RFI threshold table loaded: {len(df)} monitors")
    print(f"  Columns: {list(df.columns)}")
    return df


# ---------------------------------------------------------------------------
# STAGE 1 — Load raw simulation data
# ---------------------------------------------------------------------------

# Actual column names from Olt's OpenDSS exports:
#   hour(sec), V1, VAngle1, V2, VAngle2, V3, VAngle3,
#              I1, IAngle1, I2, IAngle2, I3, IAngle3
#
# We rename these to a clean internal schema on load.

RAW_COL_MAP = {
    "hour(sec)": "time",
    "V1": "Va_mag", "VAngle1": "Va_ang",
    "V2": "Vb_mag", "VAngle2": "Vb_ang",
    "V3": "Vc_mag", "VAngle3": "Vc_ang",
    "I1": "Ia_mag", "IAngle1": "Ia_ang",
    "I2": "Ib_mag", "IAngle2": "Ib_ang",
    "I3": "Ic_mag", "IAngle3": "Ic_ang",
}

VOLTAGE_COLS  = ["Va_mag", "Vb_mag", "Vc_mag"]
CURRENT_COLS  = ["Ia_mag", "Ib_mag", "Ic_mag"]
ANGLE_COLS    = ["Va_ang", "Vb_ang", "Vc_ang", "Ia_ang", "Ib_ang", "Ic_ang"]
ALL_SIGNAL_COLS = VOLTAGE_COLS + CURRENT_COLS + ANGLE_COLS


def load_opendss_export(filepath: str) -> pd.DataFrame:
    """
    Load a single OpenDSS monitor CSV (baseline or post-fault).
    Renames columns to clean internal schema defined in RAW_COL_MAP.
    """
    df = pd.read_csv(filepath)
    # Rename known columns; keep any extras as-is
    df = df.rename(columns={k: v for k, v in RAW_COL_MAP.items() if k in df.columns})
    missing = [v for v in RAW_COL_MAP.values() if v not in df.columns]
    if missing:
        raise ValueError(f"After renaming, still missing columns in {filepath}: {missing}")
    return df


def load_monitor_pair(baseline_path: str, faulted_path: str):
    """
    Load a matched pair of baseline and post-fault CSVs for one monitor.
    Returns (df_baseline, df_faulted).
    """
    df_base   = load_opendss_export(baseline_path)
    df_fault  = load_opendss_export(faulted_path)
    return df_base, df_fault


# ---------------------------------------------------------------------------
# STAGE 2 — FIX 2: Delta feature extraction (post-fault minus baseline)
# ---------------------------------------------------------------------------

def extract_delta_features(df_base: pd.DataFrame,
                           df_fault: pd.DataFrame,
                           rfi_id: int = None,
                           rfi_thresholds: pd.DataFrame = None) -> dict:
    """
    FIX 2 — Extract delta features: post-fault value minus baseline value.

    Instead of computing raw statistics on the post-fault waveform alone,
    we compute the *change* from normal operating conditions. This gives the
    classifier a direct fault signature that is independent of absolute load
    level — critical for a real feeder where load varies throughout the day.

    For each signal channel we compute:
      - delta_mean  : mean(faulted) - mean(baseline)
      - delta_rms   : rms(faulted)  - rms(baseline)
      - delta_std   : std(faulted)  - std(baseline)
      - ratio       : mean(faulted) / mean(baseline)  — fractional change

    Also computes:
      - voltage unbalance in faulted state (increases for SLG/LL)
      - current unbalance in faulted state
      - per-phase voltage drop ratio (Va_fault / Va_base, etc.)

    If rfi_thresholds is provided and rfi_id is given, also adds:
      - normal_current_A   : normal current at this monitor from threshold table
      - threshold_2x_A     : 2x pickup threshold
      - current_ratio_to_threshold : peak fault current / threshold
    """
    features = {}

    def rms(arr): return np.sqrt(np.mean(arr ** 2))

    for col in VOLTAGE_COLS + CURRENT_COLS:
        base_vals  = df_base[col].values
        fault_vals = df_fault[col].values

        base_mean  = np.mean(base_vals)
        fault_mean = np.mean(fault_vals)

        features[f"{col}_delta_mean"] = fault_mean - base_mean
        features[f"{col}_delta_rms"]  = rms(fault_vals) - rms(base_vals)
        features[f"{col}_delta_std"]  = np.std(fault_vals) - np.std(base_vals)
        # Ratio: how much did the signal change relative to normal?
        features[f"{col}_ratio"] = fault_mean / base_mean if abs(base_mean) > 1e-6 else 0.0

    # Voltage unbalance in faulted state (NEMA approximation)
    v_rms_fault = np.array([rms(df_fault[c].values) for c in VOLTAGE_COLS])
    v_avg_fault = np.mean(v_rms_fault)
    features["V_unbalance_fault"] = (
        np.max(np.abs(v_rms_fault - v_avg_fault)) / v_avg_fault
        if v_avg_fault > 0 else 0.0
    )

    # Voltage unbalance in baseline (should be ~0 for healthy feeder)
    v_rms_base = np.array([rms(df_base[c].values) for c in VOLTAGE_COLS])
    v_avg_base = np.mean(v_rms_base)
    features["V_unbalance_base"] = (
        np.max(np.abs(v_rms_base - v_avg_base)) / v_avg_base
        if v_avg_base > 0 else 0.0
    )

    # Current unbalance in faulted state
    i_rms_fault = np.array([rms(df_fault[c].values) for c in CURRENT_COLS])
    i_avg_fault = np.mean(i_rms_fault)
    features["I_unbalance_fault"] = (
        np.max(np.abs(i_rms_fault - i_avg_fault)) / i_avg_fault
        if i_avg_fault > 0 else 0.0
    )

    # FIX 3 — Wire in RFI threshold table features
    if rfi_thresholds is not None and rfi_id is not None:
        row = rfi_thresholds[rfi_thresholds["rfi_id"] == rfi_id]
        if not row.empty:
            normal_I   = float(row["normal_current_A"].iloc[0])
            thresh_2x  = float(row["threshold_2x_A"].iloc[0])
            peak_fault_I = np.max(np.abs(df_fault["Ia_mag"].values))
            features["normal_current_A"]  = normal_I
            features["threshold_2x_A"]    = thresh_2x
            features["current_ratio_to_threshold"] = (
                peak_fault_I / thresh_2x if thresh_2x > 0 else 0.0
            )
        else:
            features["normal_current_A"]  = np.nan
            features["threshold_2x_A"]    = np.nan
            features["current_ratio_to_threshold"] = np.nan

    return features


# ---------------------------------------------------------------------------
# STAGE 3 — FIX 1: Physics-based dropout using 0.5 pu voltage threshold
# ---------------------------------------------------------------------------

def apply_dropout_pu(df_fault: pd.DataFrame,
                     sm_registry: pd.DataFrame,
                     monitor_bus: str,
                     pu_threshold: float = 0.5) -> pd.DataFrame:
    """
    FIX 1 — Physics-based smart meter dropout using 0.5 pu voltage threshold.

    A smart meter goes offline (its readings are masked to NaN) if the
    post-fault voltage at its bus falls below pu_threshold × nominal_kV.

    This replaces the original random 50% zeroing with a physically motivated
    rule: meters lose power when feeder voltage collapses during a fault.
    The 0.5 pu threshold was specified by Olt based on the simulation setup.

    Args:
        df_fault     : post-fault monitor DataFrame (already noise-injected)
        sm_registry  : smart meter locations CSV (867 rows)
        monitor_bus  : the Base_Bus this monitor's data corresponds to
        pu_threshold : voltage threshold in per-unit (default 0.5)

    Returns a copy of df_fault with current readings masked to NaN for any
    timestep where any phase voltage is below threshold at this bus.

    Note: When zone mapping is complete, this should be applied per-meter
    across all 867 meters, not just at the monitor bus. For now we use the
    monitor bus voltage as a proxy for the local voltage zone.
    """
    df = df_fault.copy()

    # Get nominal kV for meters on this bus
    bus_meters = sm_registry[sm_registry["Base_Bus"] == monitor_bus]

    if bus_meters.empty:
        # No meters registered at this bus — no dropout to apply
        return df

    # Use the nominal kV from the registry (meters on this bus share same kV)
    nominal_kv = float(bus_meters["kV"].iloc[0])
    nominal_v  = nominal_kv * 1000.0   # convert to volts (matches V1/V2/V3 units)
    threshold_v = pu_threshold * nominal_v

    # Mask current readings at any timestep where voltage drops below threshold
    # (any phase below threshold → meter loses power)
    low_voltage_mask = (
        (df["Va_mag"] < threshold_v) |
        (df["Vb_mag"] < threshold_v) |
        (df["Vc_mag"] < threshold_v)
    )

    n_dropout = low_voltage_mask.sum()
    if n_dropout > 0:
        df.loc[low_voltage_mask, ["Ia_mag", "Ib_mag", "Ic_mag"]] = np.nan
        print(f"    Dropout applied at {monitor_bus}: {n_dropout}/{len(df)} "
              f"timesteps masked ({100*n_dropout/len(df):.1f}%)")

    return df


# ---------------------------------------------------------------------------
# STAGE 4 — Noise injection (IEEE C57.13-2016 bounded) — unchanged
# ---------------------------------------------------------------------------

# IEEE C57.13-2016 accuracy classes for instrument transformers:
#   Metering class (0.3): ±0.3% ratio error → voltage channels
#   Standard class (0.6): ±0.6% ratio error → current channels

ACCURACY_CLASS = {
    "voltage": 0.003,   # 0.3% — metering-class VT (C57.13 Table 6)
    "current": 0.006,   # 0.6% — standard-class CT (C57.13 Table 4)
}

def inject_noise(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Add Gaussian measurement noise to voltage and current magnitude channels.
    Noise sigma is scaled to the signal's own standard deviation,
    bounded by IEEE C57.13-2016 accuracy class limits.
    Applied to both baseline and post-fault DataFrames before delta extraction.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()

    for col in VOLTAGE_COLS:
        sigma = ACCURACY_CLASS["voltage"] * df[col].std()
        df[col] += rng.normal(0, sigma, len(df))

    for col in CURRENT_COLS:
        sigma = ACCURACY_CLASS["current"] * df[col].std()
        df[col] += rng.normal(0, sigma, len(df))

    return df


# ---------------------------------------------------------------------------
# STAGE 5 — Build full labeled dataset
# ---------------------------------------------------------------------------

def build_dataset(baseline_dir: str,
                  faulted_dir: str,
                  sm_registry_path: str,
                  rfi_threshold_path: str,
                  dropout_rate: float = 0.0,
                  add_noise: bool = True,
                  zone_map: dict = None) -> pd.DataFrame:
    """
    Process all matched baseline/post-fault CSV pairs into a feature matrix.

    Expects:
      baseline_dir  : folder with ckt7_Mon_rfi1.csv … rfi20.csv  (normal conditions)
      faulted_dir   : folder with ckt7_Mon_rfi1_1.csv … rfi20_1.csv (post-fault)
      sm_registry_path   : path to smart_meter_locations.csv
      rfi_threshold_path : path to rfi_thresholds_2x_with_RFI20_25A.csv
      dropout_rate  : 0.0 = no dropout, 0.5 = 50% dropout (legacy random mode)
                      Set to 0.0 to use physics-based PU dropout instead (recommended)
      add_noise     : whether to inject IEEE C57.13-bounded noise
      zone_map      : dict mapping rfi_id (int) → zone label (str)
                      e.g. {1: "zone1", 2: "zone1", 3: "zone2", ...}
                      Pass None until Olt provides the zone map — label will be "unknown"

    Returns a DataFrame where each row is one monitor's fault observation,
    with delta features, threshold features, and label columns.

    NOTE: fault_type label is currently "unknown" — blocked on Olt confirming
    what fault type the _1 suffix represents (likely SLG).
    """
    sm_registry    = load_smart_meter_registry(sm_registry_path)
    rfi_thresholds = load_rfi_thresholds(rfi_threshold_path)

    records = []
    baseline_path = Path(baseline_dir)
    faulted_path  = Path(faulted_dir)

    for rfi_id in range(1, 21):
        base_file   = baseline_path / f"ckt7_Mon_rfi{rfi_id}.csv"
        fault_file  = faulted_path  / f"ckt7_Mon_rfi{rfi_id}_1.csv"

        if not base_file.exists():
            print(f"  WARNING: baseline file not found: {base_file}")
            continue
        if not fault_file.exists():
            print(f"  WARNING: faulted file not found: {fault_file}")
            continue

        print(f"  Processing RFI {rfi_id}...")

        # Load pair
        df_base, df_fault = load_monitor_pair(str(base_file), str(fault_file))

        # Inject noise on both (before delta, so noise is symmetric)
        if add_noise:
            df_base  = inject_noise(df_base,  seed=rfi_id * 10)
            df_fault = inject_noise(df_fault, seed=rfi_id * 10 + 1)

        # FIX 1 — Physics-based dropout on faulted readings
        # Get the line this monitor is on from the threshold table
        thresh_row = rfi_thresholds[rfi_thresholds["rfi_id"] == rfi_id]
        monitor_bus = ""
        if not thresh_row.empty and "line_name" in thresh_row.columns:
            monitor_bus = str(thresh_row["line_name"].iloc[0])

        df_fault = apply_dropout_pu(df_fault, sm_registry,
                                    monitor_bus=monitor_bus,
                                    pu_threshold=0.5)

        # FIX 2 — Delta feature extraction
        feats = extract_delta_features(df_base, df_fault,
                                       rfi_id=rfi_id,
                                       rfi_thresholds=rfi_thresholds)

        # Labels — zone blocked on Olt's zone map; fault type blocked on Olt confirmation
        feats["rfi_id"]     = rfi_id
        feats["zone"]       = zone_map.get(rfi_id, "unknown") if zone_map else "unknown"
        feats["fault_type"] = "unknown"   # update once Olt confirms _1 = SLG
        feats["der_level"]  = 0           # update once 50% DER runs are available

        records.append(feats)

    dataset = pd.DataFrame(records)
    print(f"\nDataset built: {len(dataset)} samples, {len(dataset.columns)} columns")
    return dataset


# ---------------------------------------------------------------------------
# Synthetic data generator — unchanged, still useful for pipeline testing
# ---------------------------------------------------------------------------

def generate_synthetic_data(n_per_class: int = 50, seed: int = 0) -> pd.DataFrame:
    """
    Generate synthetic data mimicking real OpenDSS delta features.
    Now generates delta-style features to match the updated real pipeline.
    Three fault zones x three fault types x two DER levels = 18 classes.
    """
    rng = np.random.default_rng(seed)
    records = []

    zones       = ["zone1", "zone2", "zone3"]
    fault_types = ["SLG", "LL", "3ph"]
    der_levels  = [0, 50]

    base_v = 7200.0
    base_i = 200.0

    for zone in zones:
        for ft in fault_types:
            for der in der_levels:
                for _ in range(n_per_class):
                    n = 240

                    Va_b = base_v + rng.normal(0, base_v * 0.01, n)
                    Vb_b = base_v + rng.normal(0, base_v * 0.01, n)
                    Vc_b = base_v + rng.normal(0, base_v * 0.01, n)
                    Ia_b = base_i + rng.normal(0, base_i * 0.05, n)
                    Ib_b = base_i + rng.normal(0, base_i * 0.05, n)
                    Ic_b = base_i + rng.normal(0, base_i * 0.05, n)

                    Va_f, Vb_f, Vc_f = Va_b.copy(), Vb_b.copy(), Vc_b.copy()
                    Ia_f, Ib_f, Ic_f = Ia_b.copy(), Ib_b.copy(), Ic_b.copy()

                    if ft == "SLG":
                        Va_f *= 0.3; Ia_f *= 5.0
                    elif ft == "LL":
                        Vb_f *= 0.5; Vc_f *= 0.5
                        Ib_f *= 4.0; Ic_f *= 4.0
                    elif ft == "3ph":
                        Va_f *= 0.2; Vb_f *= 0.2; Vc_f *= 0.2
                        Ia_f *= 6.0; Ib_f *= 6.0; Ic_f *= 6.0

                    if der == 50:
                        Ia_f *= 1.15; Ib_f *= 1.15; Ic_f *= 1.15

                    df_base = pd.DataFrame({
                        "time": np.linspace(0, 1/30, n),
                        "Va_mag": Va_b, "Vb_mag": Vb_b, "Vc_mag": Vc_b,
                        "Va_ang": np.zeros(n), "Vb_ang": np.zeros(n), "Vc_ang": np.zeros(n),
                        "Ia_mag": Ia_b, "Ib_mag": Ib_b, "Ic_mag": Ic_b,
                        "Ia_ang": np.zeros(n), "Ib_ang": np.zeros(n), "Ic_ang": np.zeros(n),
                    })
                    df_fault = pd.DataFrame({
                        "time": np.linspace(0, 1/30, n),
                        "Va_mag": Va_f, "Vb_mag": Vb_f, "Vc_mag": Vc_f,
                        "Va_ang": np.zeros(n), "Vb_ang": np.zeros(n), "Vc_ang": np.zeros(n),
                        "Ia_mag": Ia_f, "Ib_mag": Ib_f, "Ic_mag": Ic_f,
                        "Ia_ang": np.zeros(n), "Ib_ang": np.zeros(n), "Ic_ang": np.zeros(n),
                    })

                    feats = extract_delta_features(df_base, df_fault)
                    feats["rfi_id"]     = 0
                    feats["zone"]       = zone
                    feats["fault_type"] = ft
                    feats["der_level"]  = der
                    records.append(feats)

    df_out = pd.DataFrame(records)
    print(f"Synthetic dataset: {len(df_out)} samples, {len(df_out.columns)} columns")
    return df_out


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running preprocessing pipeline on synthetic data...\n")

    df = generate_synthetic_data(n_per_class=50)

    print("\nFirst 3 rows:")
    print(df.head(3).to_string())

    print("\nFeature columns:")
    feature_cols = [c for c in df.columns
                    if c not in ("rfi_id", "zone", "fault_type", "der_level")]
    print(feature_cols)

    print("\nClass distribution:")
    print(df["zone"].value_counts())

    out_path = Path(__file__).parent.parent / "results" / "synthetic_features.csv"
    out_path.parent.mkdir(exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")