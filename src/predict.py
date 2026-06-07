"""
predict.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Interactive fault predictor. Loads a fault scenario from the real dataset,
shows the sensor readings, then asks both RF and SVM to guess the zone.

Usage:
  python3 src/predict.py --random
  python3 src/predict.py --zone 6 --fault_type SLG_A
  python3 src/predict.py --zone 18 --fault_type 3PH --der DG_50pct
"""

import argparse
import glob
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT       = Path(__file__).parent.parent
KRUN_GLOB  = str(ROOT / "Simulation_Results_KRun*" / "*" / "results_*.csv")
MODELS_DIR = ROOT / "results" / "models"
RFI_COLS   = [f"RFI{i}" for i in range(1, 21)]

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_data():
    files = sorted(glob.glob(KRUN_GLOB))
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = df[df["converged"] == True].reset_index(drop=True)
    return df

def load_models():
    with open(MODELS_DIR / "rf_model.pkl",  "rb") as f: rf  = pickle.load(f)
    with open(MODELS_DIR / "svm_model.pkl", "rb") as f: svm = pickle.load(f)
    return rf, svm

# ---------------------------------------------------------------------------
# Pick a sample
# ---------------------------------------------------------------------------

def pick_sample(df, zone=None, fault_type=None, der=None, random_seed=None):
    mask = pd.Series([True] * len(df))
    if zone is not None:
        mask &= df["zone"] == int(zone)
    if fault_type is not None:
        mask &= df["fault_type"] == fault_type
    if der is not None:
        mask &= df["scenario_label"] == der

    candidates = df[mask]
    if len(candidates) == 0:
        print(f"\nNo rows match filters: zone={zone}, fault_type={fault_type}, der={der}")
        print(f"Available fault types: {sorted(df['fault_type'].unique())}")
        print(f"Available DER labels:  {sorted(df['scenario_label'].unique())}")
        print(f"Available zones:       {sorted(df['zone'].unique())}")
        raise SystemExit(1)

    rng = np.random.default_rng(random_seed)
    row = candidates.iloc[rng.integers(len(candidates))]
    return row

# ---------------------------------------------------------------------------
# Predict and display
# ---------------------------------------------------------------------------

def run_prediction(row, rf, svm, df):
    sm_cols      = [c for c in df.columns if c.startswith("SM_")]
    feature_cols = RFI_COLS + sm_cols
    X = row[feature_cols].values.astype(np.float32).reshape(1, -1)

    true_zone    = str(int(row["zone"]))
    rf_pred      = rf.predict(X)[0]
    svm_pred     = svm.predict(X)[0]
    rf_proba     = rf.predict_proba(X)[0]
    rf_classes   = [str(c) for c in rf.classes_]

    # Sort proba descending for top-5
    order    = np.argsort(rf_proba)[::-1]
    top5_cls = [rf_classes[i] for i in order[:5]]
    top5_p   = [rf_proba[i]   for i in order[:5]]

    # ----------------------------------------------------------------
    print("\n" + "="*55)
    print("  FAULT SCENARIO")
    print("="*55)
    print(f"  True zone      : {true_zone}")
    print(f"  Fault type     : {row['fault_type']}")
    print(f"  DER level      : {row['scenario_label']}")
    print(f"  K-run          : {int(row['k_run'])}")
    print(f"  Fault bus      : {row['fault_bus']}")

    print("\n  RFI Monitor Readings (current, A):")
    for i, col in enumerate(RFI_COLS, 1):
        val = row[col]
        bar = "#" * min(int(val / 50), 30)
        print(f"    RFI{i:2d}: {val:10.2f}  {bar}")

    print("\n" + "-"*55)
    print("  MODEL PREDICTIONS")
    print("-"*55)

    rf_correct  = "CORRECT" if rf_pred  == true_zone else f"WRONG (true={true_zone})"
    svm_correct = "CORRECT" if svm_pred == true_zone else f"WRONG (true={true_zone})"

    print(f"  Random Forest  → Zone {rf_pred:>2s}  [{rf_correct}]")
    print(f"  SVM (RBF)      → Zone {svm_pred:>2s}  [{svm_correct}]")

    print("\n  RF Top-5 zone probabilities:")
    for cls, p in zip(top5_cls, top5_p):
        bar = "█" * int(p * 40)
        marker = " ←" if cls == true_zone else ""
        print(f"    Zone {cls:>2s}: {p:5.1%}  {bar}{marker}")

    print("="*55 + "\n")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Predict fault zone from a real scenario")
    ap.add_argument("--random",     action="store_true", help="Pick a completely random sample")
    ap.add_argument("--zone",       type=int,            help="Filter by true zone (1–20)")
    ap.add_argument("--fault_type", type=str,            help="SLG_A | SLG_B | SLG_C | LL_AB | 3PH")
    ap.add_argument("--der",        type=str,            help="DER scenario label, e.g. DG_20pct")
    ap.add_argument("--seed",       type=int, default=None, help="Random seed for reproducibility")
    args = ap.parse_args()

    print("Loading data and models...")
    df       = load_data()
    rf, svm  = load_models()

    zone       = None if args.random else args.zone
    fault_type = None if args.random else args.fault_type
    der        = None if args.random else args.der

    row = pick_sample(df, zone=zone, fault_type=fault_type, der=der, random_seed=args.seed)
    run_prediction(row, rf, svm, df)

if __name__ == "__main__":
    main()
