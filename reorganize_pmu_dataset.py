"""
reorganize_pmu_dataset.py
=========================
Creates the final PMU_dataset folder structure:

  Realistic_Simulation/PMU_dataset/
    Faulty/
      20_PMUs/results.csv  ...  01_PMUs/results.csv   (fault ablation, noise+dropout)
    Clean/
      20_PMUs/results.csv  ...  01_PMUs/results.csv   (normal-ops ablation, noise only)

Sources:
  Faulty  <- uPMU_only/XX_PMUs/results.csv  (already generated)
  Clean   <- ablated from uPMU_only/Normal_Operations/Degraded_NoiseOnly/results.csv
"""

import os
import shutil
import pandas as pd

BASE      = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation"
SRC_FAULT = os.path.join(BASE, "uPMU_only")
SRC_NORM  = os.path.join(BASE, "uPMU_only", "Normal_Operations",
                         "Degraded_NoiseOnly", "results.csv")
OUT_DIR   = os.path.join(BASE, "PMU_dataset")

PMU_LABELS = [
    "PMU1",  "PMU2",  "PMU3",  "PMU4",  "PMU5",
    "PMU6",  "PMU7",  "PMU8",  "PMU9",  "PMU10",
    "PMU11", "PMU12", "PMU13", "PMU14", "PMU15",
    "PMU16", "PMU17", "PMU18", "PMU19", "PMU20",
]

PMU_FEATURE_SUFFIXES = [
    "_Ia", "_Ib", "_Ic",
    "_Ia_ang", "_Ib_ang", "_Ic_ang",
    "_I0", "_I1", "_I2",
    "_Va", "_Vb", "_Vc",
    "_Va_ang", "_Vb_ang", "_Vc_ang",
    "_V0", "_V1", "_V2",
]

def pmu_cols(label):
    return [label + s for s in PMU_FEATURE_SUFFIXES]


def folder_name(n):
    return f"{n:02d}_PMUs"


# =============================================================================
# 1. Copy fault ablation datasets -> Faulty/
# =============================================================================
print("=" * 60)
print("Building PMU_dataset/Faulty  (fault cases, noise + dropout)")
print("=" * 60)

faulty_dir = os.path.join(OUT_DIR, "Faulty")

for n in range(20, 0, -1):
    name = folder_name(n)
    src  = os.path.join(SRC_FAULT, name, "results.csv")
    dst_dir = os.path.join(faulty_dir, name)
    dst     = os.path.join(dst_dir, "results.csv")
    os.makedirs(dst_dir, exist_ok=True)
    shutil.copy2(src, dst)
    size_kb = os.path.getsize(dst) // 1024
    print(f"  {name}  ->  Faulty/{name}/results.csv  ({size_kb:,} KB)")

print(f"\n  20 fault datasets copied.\n")


# =============================================================================
# 2. Generate normal-ops ablation datasets -> Clean/
# =============================================================================
print("=" * 60)
print("Building PMU_dataset/Clean  (normal ops, noise only, no dropout)")
print("=" * 60)

print(f"\n  Loading {SRC_NORM} ...")
norm_df = pd.read_csv(SRC_NORM, low_memory=False)
print(f"  Loaded: {len(norm_df)} rows x {len(norm_df.columns)} columns")

# Identify meta + SM columns (everything that is not a PMU feature column)
all_pmu_cols = []
for lbl in PMU_LABELS:
    all_pmu_cols.extend(pmu_cols(lbl))
pmu_col_set = set(all_pmu_cols)
meta_sm_cols = [c for c in norm_df.columns if c not in pmu_col_set]

clean_dir = os.path.join(OUT_DIR, "Clean")

# PMU removal order: highest-numbered first (PMU20 removed first)
active_labels = list(PMU_LABELS)   # PMU1 .. PMU20

for n in range(20, 0, -1):
    # Active PMUs for this step: first N labels
    active = PMU_LABELS[:n]
    out_pmu_cols = []
    for lbl in active:
        out_pmu_cols.extend(pmu_cols(lbl))

    out_cols = meta_sm_cols + out_pmu_cols
    # Keep only columns that exist in the dataframe
    out_cols = [c for c in out_cols if c in norm_df.columns]

    subset = norm_df[out_cols]

    name    = folder_name(n)
    dst_dir = os.path.join(clean_dir, name)
    dst     = os.path.join(dst_dir, "results.csv")
    os.makedirs(dst_dir, exist_ok=True)
    subset.to_csv(dst, index=False)

    size_kb = os.path.getsize(dst) // 1024
    print(f"  {name}  ({n*18} PMU features)  ->  Clean/{name}/results.csv  ({size_kb:,} KB)")

print(f"\n  20 clean datasets written.\n")

print("=" * 60)
print("DONE")
print(f"  PMU_dataset/Faulty/  : 20 fault ablation datasets")
print(f"  PMU_dataset/Clean/   : 20 normal-ops ablation datasets")
print(f"  Total                : 40 datasets")
print(f"  Location             : {OUT_DIR}")
print("=" * 60)
