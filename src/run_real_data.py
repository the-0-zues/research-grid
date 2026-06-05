"""
run_real_data.py
Run the ML pipeline on real OpenDSS SLG fault data (single-snapshot CSVs).
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Usage:
    python run_real_data.py

Folder structure expected:
    data/rfi_baseline/pre_fault/   ckt7_Mon_rfi1.csv ... rfi20.csv
    data/rfi_baseline/post_fault/  ckt7_Mon_rfi1_1.csv ... rfi20_1.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

_BASE        = Path(__file__).parent.parent
BASELINE_DIR = _BASE / "data" / "rfi_baseline" / "pre_fault"
FAULTED_DIR  = _BASE / "data" / "rfi_baseline" / "post_fault"
RESULTS_DIR  = _BASE / "results"
RESULTS_DIR.mkdir(exist_ok=True)

PU_THRESHOLD = 0.5   # smart meter dropout threshold

# IEEE C57.13-2016 noise (applied as % perturbation on single values)
NOISE_V = 0.003
NOISE_I = 0.006

VOLTAGE_COLS = ["Va_mag", "Vb_mag", "Vc_mag"]
CURRENT_COLS = ["Ia_mag", "Ib_mag", "Ic_mag"]

RAW_COL_MAP = {
    "t(sec)":  "time",
    "V1":      "Va_mag", "VAngle1": "Va_ang",
    "V2":      "Vb_mag", "VAngle2": "Vb_ang",
    "V3":      "Vc_mag", "VAngle3": "Vc_ang",
    "I1":      "Ia_mag", "IAngle1": "Ia_ang",
    "I2":      "Ib_mag", "IAngle2": "Ib_ang",
    "I3":      "Ic_mag", "IAngle3": "Ic_ang",
}

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def load_csv(filepath):
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip()
    if "hour" in df.columns:
        df = df.drop(columns=["hour"])
    df = df.rename(columns={k: v for k, v in RAW_COL_MAP.items() if k in df.columns})
    return df


def inject_noise_single(row, rng):
    """Add IEEE C57.13-bounded noise to a single snapshot row."""
    row = row.copy()
    for col in VOLTAGE_COLS:
        row[col] += rng.normal(0, NOISE_V * abs(row[col]))
    for col in CURRENT_COLS:
        row[col] += rng.normal(0, NOISE_I * abs(row[col]))
    return row


def extract_features(base_row, fault_row):
    """
    Extract features from a matched baseline / post-fault snapshot pair.
    Since each CSV is a single timestep, we use raw values and deltas directly.

    Features per channel (V and I, 3 phases each = 6 channels):
      _base   : baseline value
      _fault  : post-fault value
      _delta  : fault - base  (absolute change)
      _ratio  : fault / base  (fractional change — key fault signature)

    Additional:
      V_unbalance_base   : voltage unbalance before fault
      V_unbalance_fault  : voltage unbalance after fault (rises for SLG/LL)
      I_unbalance_fault  : current unbalance after fault
      Va_ratio           : phase A voltage ratio (drops sharply for SLG on phase A)
    """
    feats = {}

    for col in VOLTAGE_COLS + CURRENT_COLS:
        b = float(base_row[col])
        f = float(fault_row[col])
        feats[f"{col}_base"]  = b
        feats[f"{col}_fault"] = f
        feats[f"{col}_delta"] = f - b
        feats[f"{col}_ratio"] = f / b if abs(b) > 1e-6 else 0.0

    # Voltage unbalance (NEMA approximation)
    v_base  = np.array([float(base_row[c])  for c in VOLTAGE_COLS])
    v_fault = np.array([float(fault_row[c]) for c in VOLTAGE_COLS])

    feats["V_unbalance_base"]  = (np.max(np.abs(v_base  - v_base.mean()))  / v_base.mean()
                                  if v_base.mean()  > 0 else 0.0)
    feats["V_unbalance_fault"] = (np.max(np.abs(v_fault - v_fault.mean())) / v_fault.mean()
                                  if v_fault.mean() > 0 else 0.0)

    # Current unbalance
    i_fault = np.array([float(fault_row[c]) for c in CURRENT_COLS])
    feats["I_unbalance_fault"] = (np.max(np.abs(i_fault - i_fault.mean())) / i_fault.mean()
                                  if i_fault.mean() > 0 else 0.0)

    return feats


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    records      = []
    dropout_log  = []
    rng = np.random.default_rng(42)

    print("Processing real SLG fault data (single-snapshot mode)...\n")

    for rfi_id in range(1, 21):
        base_file  = BASELINE_DIR / f"ckt7_Mon_rfi{rfi_id}.csv"
        fault_file = FAULTED_DIR  / f"ckt7_Mon_rfi{rfi_id}_1.csv"

        if not base_file.exists():
            print(f"  [SKIP] {base_file}")
            continue
        if not fault_file.exists():
            print(f"  [SKIP] {fault_file}")
            continue

        print(f"  RFI {rfi_id:2d} ...", end=" ")

        df_base  = load_csv(base_file)
        df_fault = load_csv(fault_file)

        # Take first data row
        base_row  = df_base.iloc[0]
        fault_row = df_fault.iloc[0]

        # Inject IEEE C57.13 noise
        base_row  = inject_noise_single(base_row,  rng)
        fault_row = inject_noise_single(fault_row, rng)

        # Nominal voltage from baseline (mean of 3 phases)
        nominal_v = np.mean([float(base_row[c]) for c in VOLTAGE_COLS])

        # 0.5 pu dropout check — any phase below threshold?
        threshold_v  = PU_THRESHOLD * nominal_v
        fault_vs     = [float(fault_row[c]) for c in VOLTAGE_COLS]
        meter_offline = any(v < threshold_v for v in fault_vs)
        dropout_frac  = 1.0 if meter_offline else 0.0

        if meter_offline:
            # Mask current readings
            for col in CURRENT_COLS:
                fault_row[col] = np.nan
            print(f"DROPOUT (V={min(fault_vs):.0f} < {threshold_v:.0f})")
        else:
            print(f"no dropout (min V={min(fault_vs):.0f}, threshold={threshold_v:.0f})")

        dropout_log.append({
            "rfi_id":           rfi_id,
            "nominal_v":        round(nominal_v, 1),
            "threshold_v":      round(threshold_v, 1),
            "min_fault_v":      round(min(fault_vs), 1),
            "dropout_fraction": dropout_frac,
            "meter_offline":    meter_offline,
        })

        # Extract features
        feats = extract_features(base_row, fault_row)
        feats["rfi_id"]     = rfi_id
        feats["zone"]       = f"rfi{rfi_id}"
        feats["fault_type"] = "SLG"
        feats["der_level"]  = 0

        records.append(feats)

    # Assemble and save
    df_out     = pd.DataFrame(records)
    df_dropout = pd.DataFrame(dropout_log)

    out_features = RESULTS_DIR / "real_slg_features.csv"
    out_dropout  = RESULTS_DIR / "real_slg_dropout.csv"
    df_out.to_csv(out_features, index=False)
    df_dropout.to_csv(out_dropout, index=False)

    print(f"\nFeature matrix: {df_out.shape[0]} samples × {df_out.shape[1]} columns")
    print(f"Saved: {out_features}")
    print(f"Saved: {out_dropout}")

    print("\nDropout summary:")
    print(df_dropout.to_string(index=False))

    print("\nFeature preview:")
    preview = ["zone", "fault_type",
               "Va_mag_base", "Va_mag_fault", "Va_mag_delta", "Va_mag_ratio",
               "V_unbalance_fault", "I_unbalance_fault"]
    print(df_out[preview].to_string(index=False))


if __name__ == "__main__":
    main()