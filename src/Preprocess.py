"""
preprocess.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Pipeline stages:
  1. Load raw OpenDSS simulation exports
  2. Extract statistical features per phase (RMS, peak, std, mean)
  3. Apply smart meter dropout (0% or 50%)
  4. Inject Gaussian measurement noise (bounded by IEEE C57.13-2016 accuracy classes)
  5. Assemble labeled feature matrix for RF/SVM training
"""

import numpy as np
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# STAGE 1 — Load raw simulation data
# ---------------------------------------------------------------------------

def load_opendss_export(filepath: str) -> pd.DataFrame:
    """
    Load a single OpenDSS CSV export for one fault scenario.

    Expected columns (to be confirmed with Olt):
        time   — simulation timestep (seconds)
        Va, Vb, Vc  — three-phase voltages (kV, line-to-neutral)
        Ia, Ib, Ic  — three-phase currents (A)

    Returns a DataFrame with those columns.
    """
    df = pd.read_csv(filepath)
    required = ["time", "Va", "Vb", "Vc", "Ia", "Ib", "Ic"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {filepath}: {missing}")
    return df


# ---------------------------------------------------------------------------
# STAGE 2 — Feature extraction
# ---------------------------------------------------------------------------

SIGNAL_COLS = ["Va", "Vb", "Vc", "Ia", "Ib", "Ic"]

def extract_features(df: pd.DataFrame) -> dict:
    """
    Extract statistical features from one fault scenario's waveform data.

    For each of the 6 signals (Va, Vb, Vc, Ia, Ib, Ic) we compute:
      - RMS     : captures the effective magnitude; drops sharply during faults
      - Peak    : maximum absolute value; useful for detecting transient spikes
      - Std dev : spread of the signal; high during asymmetric faults
      - Mean    : DC offset; helps distinguish fault types

    Also computes voltage unbalance ratio — a power-systems feature that
    increases during single-phase and line-to-line faults.

    Returns a flat dict of feature_name -> scalar value.
    """
    features = {}

    for col in SIGNAL_COLS:
        sig = df[col].values
        features[f"{col}_rms"]  = np.sqrt(np.mean(sig ** 2))
        features[f"{col}_peak"] = np.max(np.abs(sig))
        features[f"{col}_std"]  = np.std(sig)
        features[f"{col}_mean"] = np.mean(sig)

    # Voltage unbalance ratio (NEMA definition approximation)
    v_rms = np.array([features[f"V{ph}_rms"] for ph in ("a", "b", "c")])
    v_avg = np.mean(v_rms)
    if v_avg > 0:
        features["V_unbalance"] = np.max(np.abs(v_rms - v_avg)) / v_avg
    else:
        features["V_unbalance"] = 0.0

    return features


# ---------------------------------------------------------------------------
# STAGE 3 — Smart meter dropout
# ---------------------------------------------------------------------------

def apply_dropout(df: pd.DataFrame, dropout_rate: float = 0.0,
                  seed: int = 42) -> pd.DataFrame:
    """
    Simulate smart meter communication failures by zeroing out a fraction
    of current readings (meters report last-known or null on dropout).

    dropout_rate: 0.0 = no dropout (baseline), 0.5 = 50% dropout
    Zeroing is applied to current channels only (Ia, Ib, Ic) — voltage
    measurements come from substation VTs which are assumed always available.

    Why this matters for the paper: AMI infrastructure in high-DER feeders
    suffers elevated packet loss due to RF interference from inverters.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()
    if dropout_rate > 0:
        mask = rng.random(len(df)) < dropout_rate
        df.loc[mask, ["Ia", "Ib", "Ic"]] = 0.0
    return df


# ---------------------------------------------------------------------------
# STAGE 4 — Noise injection (IEEE C57.13-2016 bounded)
# ---------------------------------------------------------------------------

# IEEE C57.13-2016 accuracy classes for instrument transformers:
#   Metering class (0.3): ±0.3% ratio error
#   Standard class (0.6): ±0.6% ratio error
#   Relaying class (C200): ±10% at 20x rated current (not used here)
#
# We inject zero-mean Gaussian noise with sigma = accuracy_class * signal_std.
# This keeps noise physically realistic and citeable.

ACCURACY_CLASS = {
    "voltage": 0.003,   # 0.3% — metering-class VT (C57.13 Table 6)
    "current": 0.006,   # 0.6% — standard-class CT (C57.13 Table 4)
}

def inject_noise(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Add Gaussian measurement noise to all six signal channels.

    Noise sigma is scaled to the signal's own standard deviation,
    bounded by IEEE C57.13-2016 accuracy class limits.

    Using a fixed seed ensures reproducibility across experimental runs.
    """
    rng = np.random.default_rng(seed)
    df = df.copy()

    for col in ["Va", "Vb", "Vc"]:
        sigma = ACCURACY_CLASS["voltage"] * df[col].std()
        df[col] += rng.normal(0, sigma, len(df))

    for col in ["Ia", "Ib", "Ic"]:
        sigma = ACCURACY_CLASS["current"] * df[col].std()
        df[col] += rng.normal(0, sigma, len(df))

    return df


# ---------------------------------------------------------------------------
# STAGE 5 — Build full labeled dataset from a folder of scenario CSVs
# ---------------------------------------------------------------------------

def build_dataset(data_dir: str, dropout_rate: float = 0.0,
                  add_noise: bool = True) -> pd.DataFrame:
    """
    Process all scenario CSV files in data_dir into a single feature matrix.

    Expected filename format (to confirm with Olt):
        {fault_type}_{zone}_{der_level}.csv
        e.g.  SLG_zone2_50der.csv
              LL_zone1_0der.csv
              3ph_zone3_50der.csv

    Returns a DataFrame where:
      - Each row is one fault scenario (one CSV file)
      - Columns are extracted features
      - 'label' column = fault zone (e.g. "zone1", "zone2", "zone3")
      - 'fault_type' column = SLG / LL / 3ph
      - 'der_level' column = 0 or 50
    """
    records = []
    data_path = Path(data_dir)
    csv_files = list(data_path.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    for fpath in csv_files:
        # Parse metadata from filename
        parts = fpath.stem.split("_")   # e.g. ["SLG", "zone2", "50der"]
        if len(parts) < 3:
            print(f"  Skipping {fpath.name} — unexpected filename format")
            continue

        fault_type = parts[0]                         # SLG, LL, 3ph
        zone       = parts[1]                         # zone1, zone2, ...
        der_level  = int(parts[2].replace("der", "")) # 0 or 50

        # Load and process
        df = load_opendss_export(fpath)
        if add_noise:
            df = inject_noise(df)
        df = apply_dropout(df, dropout_rate=dropout_rate)

        # Extract features
        feats = extract_features(df)
        feats["label"]      = zone
        feats["fault_type"] = fault_type
        feats["der_level"]  = der_level

        records.append(feats)

    dataset = pd.DataFrame(records)
    print(f"Dataset built: {len(dataset)} samples, {len(dataset.columns)} columns")
    return dataset


# ---------------------------------------------------------------------------
# Synthetic data generator — use this until Olt's exports are ready
# ---------------------------------------------------------------------------

def generate_synthetic_data(n_per_class: int = 50, seed: int = 0) -> pd.DataFrame:
    """
    Generate a synthetic dataset that mimics the structure of real OpenDSS exports.

    Three fault zones × three fault types × two DER levels = 18 classes.
    Signal statistics are loosely based on a 12.47 kV distribution feeder.

    Use this to develop and test the full pipeline before real data arrives.
    """
    rng = np.random.default_rng(seed)
    records = []

    zones      = ["zone1", "zone2", "zone3"]
    fault_types = ["SLG", "LL", "3ph"]
    der_levels  = [0, 50]

    # Base signal parameters (approximate 12.47 kV feeder, per-unit style)
    base_v = 7200.0   # V (line-to-neutral, 12.47 kV / sqrt(3))
    base_i = 200.0    # A

    for zone in zones:
        for ft in fault_types:
            for der in der_levels:
                for _ in range(n_per_class):
                    n = 240  # 2 cycles at 120 samples/cycle

                    # Healthy phase voltages
                    Va = base_v + rng.normal(0, base_v * 0.01, n)
                    Vb = base_v + rng.normal(0, base_v * 0.01, n)
                    Vc = base_v + rng.normal(0, base_v * 0.01, n)
                    Ia = base_i + rng.normal(0, base_i * 0.05, n)
                    Ib = base_i + rng.normal(0, base_i * 0.05, n)
                    Ic = base_i + rng.normal(0, base_i * 0.05, n)

                    # Apply fault disturbances based on type
                    if ft == "SLG":
                        Va *= 0.3   # faulted phase collapses
                        Ia *= 5.0   # fault current surge
                    elif ft == "LL":
                        Vb *= 0.5
                        Vc *= 0.5
                        Ib *= 4.0
                        Ic *= 4.0
                    elif ft == "3ph":
                        Va *= 0.2
                        Vb *= 0.2
                        Vc *= 0.2
                        Ia *= 6.0
                        Ib *= 6.0
                        Ic *= 6.0

                    # DER slightly raises current levels
                    if der == 50:
                        Ia *= 1.15
                        Ib *= 1.15
                        Ic *= 1.15

                    df_sim = pd.DataFrame(
                        {"time": np.linspace(0, 1/30, n),
                         "Va": Va, "Vb": Vb, "Vc": Vc,
                         "Ia": Ia, "Ib": Ib, "Ic": Ic}
                    )

                    feats = extract_features(df_sim)
                    feats["label"]      = zone
                    feats["fault_type"] = ft
                    feats["der_level"]  = der
                    records.append(feats)

    df_out = pd.DataFrame(records)
    print(f"Synthetic dataset: {len(df_out)} samples, {len(df_out.columns)} columns")
    return df_out


# ---------------------------------------------------------------------------
# Quick test — run this file directly to verify everything works
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Running preprocessing pipeline on synthetic data...\n")

    df = generate_synthetic_data(n_per_class=50)

    print("\nFirst 3 rows:")
    print(df.head(3).to_string())

    print("\nFeature columns:")
    feature_cols = [c for c in df.columns if c not in ("label", "fault_type", "der_level")]
    print(feature_cols)

    print("\nClass distribution:")
    print(df["label"].value_counts())

    # Save to results so you can inspect it
    out_path = Path(__file__).parent.parent / "results" / "synthetic_features.csv"
    out_path.parent.mkdir(exist_ok=True)
    df.to_csv(out_path, index=False)
    print(f"\nSaved to {out_path}")