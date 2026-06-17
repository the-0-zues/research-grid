"""
generate_degraded_datasets.py

Generates degraded versions of the clean 10 k-run simulation dataset by applying:
  1. RFI measurement noise  — IEEE C57.13-2016 Class 0.6 (CT, ±0.6%) combined
                               with ANSI C12.1-2022 Class 0.5 (meter, ±0.7%) via RSS
                               → sigma_RFI = sqrt((0.6/3)^2 + (0.7/3)^2) ≈ 0.307% of reading
  2. Smart meter voltage noise — ANSI C12.20 Class 0.5 (±0.5%)
                               → sigma_SM  = 0.5/3 ≈ 0.1667% of reading
  3. Smart meter dropout      — random per-row mask at increasing rates
                               (5%, 10%, 15%, ... 50%) — dropped meters set to NaN

Output folder structure (mirrors clean k-run structure):
  Degraded_Datasets/
    Dropout_05pct/
      KRun_01/
        Scenario_01_DG_2pct/results_DG_2pct.csv
        ...
        Scenario_25_DG_50pct/results_DG_50pct.csv
      KRun_02/ ...
      ...
      KRun_10/
    Dropout_10pct/ ...
    ...
    Dropout_50pct/

Clean data is never modified. Each degraded version is a fresh independent
perturbation (new RNG seed per dropout level so noise realizations differ).
"""

import os
import numpy as np
import pandas as pd

# ── Config ────────────────────────────────────────────────────────────────────

CLEAN_BASE      = r"C:\EPRI_Ckt7_DER_Project"
OUTPUT_BASE     = r"C:\EPRI_Ckt7_DER_Project\Degraded_Datasets"
N_KRUNS         = 10
N_SCENARIOS     = 25
DROPOUT_RATES   = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

# Noise sigma factors (max_dev / 3, treated as 3-sigma bound)
# RFI: RSS of C57.13 Class 0.6 (0.6%/3) and C12.1 Class 0.5 (0.7%/3)
RFI_SIGMA = np.sqrt((0.006 / 3) ** 2 + (0.007 / 3) ** 2)   # ≈ 0.00307
SM_SIGMA  = 0.005 / 3                                         # ≈ 0.001667

# Label / metadata columns — never perturbed
META_COLS = [
    "k_run", "scenario_id", "scenario_label", "n_dg_buses",
    "fault_id", "zone", "fault_type", "fault_line", "fault_bus", "converged"
]

SCENARIO_LABELS = [
    ("Scenario_01_DG_2pct",  "results_DG_2pct.csv"),
    ("Scenario_02_DG_4pct",  "results_DG_4pct.csv"),
    ("Scenario_03_DG_6pct",  "results_DG_6pct.csv"),
    ("Scenario_04_DG_8pct",  "results_DG_8pct.csv"),
    ("Scenario_05_DG_10pct", "results_DG_10pct.csv"),
    ("Scenario_06_DG_12pct", "results_DG_12pct.csv"),
    ("Scenario_07_DG_14pct", "results_DG_14pct.csv"),
    ("Scenario_08_DG_16pct", "results_DG_16pct.csv"),
    ("Scenario_09_DG_18pct", "results_DG_18pct.csv"),
    ("Scenario_10_DG_20pct", "results_DG_20pct.csv"),
    ("Scenario_11_DG_22pct", "results_DG_22pct.csv"),
    ("Scenario_12_DG_24pct", "results_DG_24pct.csv"),
    ("Scenario_13_DG_26pct", "results_DG_26pct.csv"),
    ("Scenario_14_DG_28pct", "results_DG_28pct.csv"),
    ("Scenario_15_DG_30pct", "results_DG_30pct.csv"),
    ("Scenario_16_DG_32pct", "results_DG_32pct.csv"),
    ("Scenario_17_DG_34pct", "results_DG_34pct.csv"),
    ("Scenario_18_DG_36pct", "results_DG_36pct.csv"),
    ("Scenario_19_DG_38pct", "results_DG_38pct.csv"),
    ("Scenario_20_DG_40pct", "results_DG_40pct.csv"),
    ("Scenario_21_DG_42pct", "results_DG_42pct.csv"),
    ("Scenario_22_DG_44pct", "results_DG_44pct.csv"),
    ("Scenario_23_DG_46pct", "results_DG_46pct.csv"),
    ("Scenario_24_DG_48pct", "results_DG_48pct.csv"),
    ("Scenario_25_DG_50pct", "results_DG_50pct.csv"),
]

# ── Noise / dropout helpers ───────────────────────────────────────────────────

def apply_proportional_noise(values: np.ndarray, sigma_factor: float, rng: np.random.Generator) -> np.ndarray:
    """Add N(0, sigma_factor * |value|) noise independently to each element."""
    sigma = sigma_factor * np.abs(values)
    return values + rng.normal(0.0, sigma)

def apply_dropout(df: pd.DataFrame, sm_cols: list, dropout_rate: float, rng: np.random.Generator) -> pd.DataFrame:
    """
    Randomly zero out (NaN) sm_cols entries per row at the given dropout rate.
    Each row gets an independent random mask so dropout pattern varies across faults.
    """
    n_rows = len(df)
    n_sm   = len(sm_cols)
    # Draw a (n_rows x n_sm) uniform matrix; entries < dropout_rate become NaN
    mask = rng.random((n_rows, n_sm)) < dropout_rate
    sm_vals = df[sm_cols].values.copy().astype(float)
    sm_vals[mask] = np.nan
    df = df.copy()
    df[sm_cols] = sm_vals
    return df

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Discover RFI and SM column names from the first clean CSV
    sample_path = os.path.join(
        CLEAN_BASE, "Simulation_Results_KRun1",
        "Scenario_01_DG_2pct", "results_DG_2pct.csv"
    )
    sample = pd.read_csv(sample_path, nrows=1)
    rfi_cols = [c for c in sample.columns if c.startswith("RFI")]
    sm_cols  = [c for c in sample.columns if c.startswith("SM_")]
    print(f"RFI columns: {len(rfi_cols)}   SM columns: {len(sm_cols)}")

    total_files = len(DROPOUT_RATES) * N_KRUNS * N_SCENARIOS
    processed   = 0

    for dropout_rate in DROPOUT_RATES:
        pct_label  = f"{int(round(dropout_rate * 100)):02d}pct"
        dropout_dir = os.path.join(OUTPUT_BASE, f"Dropout_{pct_label}")

        # Seed per dropout level so each level has its own independent noise realization
        base_seed = int(round(dropout_rate * 100)) * 1000
        rng = np.random.default_rng(base_seed)

        print(f"\n=== Dropout {pct_label} (seed={base_seed}) ===")

        for k in range(1, N_KRUNS + 1):
            krun_src_dir = os.path.join(CLEAN_BASE, f"Simulation_Results_KRun{k}")
            krun_out_dir = os.path.join(dropout_dir, f"KRun_{k:02d}")

            for folder, filename in SCENARIO_LABELS:
                src_csv = os.path.join(krun_src_dir, folder, filename)
                out_dir = os.path.join(krun_out_dir, folder)
                out_csv = os.path.join(out_dir, filename)

                if not os.path.exists(src_csv):
                    print(f"  [WARN] Missing: {src_csv}")
                    continue

                os.makedirs(out_dir, exist_ok=True)

                df = pd.read_csv(src_csv)

                # 1. Apply RFI noise (proportional, RSS-combined sigma)
                rfi_vals = df[rfi_cols].values.astype(float)
                df[rfi_cols] = apply_proportional_noise(rfi_vals, RFI_SIGMA, rng)

                # 2. Apply SM voltage noise (proportional, ANSI C12.20 sigma)
                sm_vals = df[sm_cols].values.astype(float)
                df[sm_cols] = apply_proportional_noise(sm_vals, SM_SIGMA, rng)

                # 3. Apply SM dropout (random per-row mask at dropout_rate)
                df = apply_dropout(df, sm_cols, dropout_rate, rng)

                df.to_csv(out_csv, index=False)
                processed += 1

            print(f"  KRun {k:02d} done  ({processed}/{total_files} files total)")

    print(f"\nAll done. {processed} degraded CSV files written to {OUTPUT_BASE}")

if __name__ == "__main__":
    main()
