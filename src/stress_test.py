"""
stress_test.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Stress-tests the trained RF and SVM models across four dimensions:
  1. Fault type  — SLG_A, SLG_B, SLG_C, LL_AB, 3PH
  2. DER level   — 2% through 50% DG penetration (25 scenarios)
  3. Noise       — Gaussian noise at IEEE C57.13 accuracy class levels
  4. SM dropout  — original vs dropout-augmented models side by side
"""

import glob
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.metrics import accuracy_score

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT        = Path(__file__).parent.parent
KRUN_GLOB   = str(ROOT / "Simulation_Results_KRun*" / "*" / "results_*.csv")
MODELS_DIR  = ROOT / "results" / "models"
FIGURES_DIR = ROOT / "results" / "figures"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR.mkdir(exist_ok=True)

RFI_COLS = [f"RFI{i}" for i in range(1, 21)]

# ---------------------------------------------------------------------------
# Load data and models
# ---------------------------------------------------------------------------

def load_all():
    files = sorted(glob.glob(KRUN_GLOB))
    print(f"Loading {len(files)} scenario files...")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    df = df[df["converged"] == True].reset_index(drop=True)
    sm_cols = [c for c in df.columns if c.startswith("SM_")]
    feature_cols = RFI_COLS + sm_cols
    X = df[feature_cols].values.astype(np.float32)
    y = df["zone"].astype(str).values
    print(f"  {len(df)} samples, {len(feature_cols)} features")
    return df, X, y, feature_cols

def load_models():
    with open(MODELS_DIR / "rf_model.pkl",  "rb") as f: rf  = pickle.load(f)
    with open(MODELS_DIR / "svm_model.pkl", "rb") as f: svm = pickle.load(f)
    aug_rf_path  = MODELS_DIR / "rf_augmented.pkl"
    aug_svm_path = MODELS_DIR / "svm_augmented.pkl"
    rf_aug = svm_aug = None
    if aug_rf_path.exists() and aug_svm_path.exists():
        with open(aug_rf_path,  "rb") as f: rf_aug  = pickle.load(f)
        with open(aug_svm_path, "rb") as f: svm_aug = pickle.load(f)
        print("  Augmented models loaded.")
    else:
        print("  Augmented models not found — skipping comparison.")
    return rf, svm, rf_aug, svm_aug

# ---------------------------------------------------------------------------
# 1. Accuracy by fault type
# ---------------------------------------------------------------------------

def stress_fault_type(df, X, y, rf, svm):
    print("\n--- Stress: Fault Type ---")
    rows = []
    for ft in sorted(df["fault_type"].unique()):
        mask = (df["fault_type"] == ft).values
        rf_acc  = accuracy_score(y[mask], rf.predict(X[mask]))
        svm_acc = accuracy_score(y[mask], svm.predict(X[mask]))
        n = mask.sum()
        print(f"  {ft:8s}  n={n:6d}  RF={rf_acc:.4f}  SVM={svm_acc:.4f}")
        rows.append({"slice": "fault_type", "value": ft,
                     "n": n, "rf_acc": rf_acc, "svm_acc": svm_acc})

    fault_types = [r["value"] for r in rows]
    rf_accs     = [r["rf_acc"]  for r in rows]
    svm_accs    = [r["svm_acc"] for r in rows]

    x = np.arange(len(fault_types))
    w = 0.35
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.bar(x - w/2, rf_accs,  w, label="Random Forest", color="#2c7bb6")
    ax.bar(x + w/2, svm_accs, w, label="SVM (RBF)",     color="#d7191c")
    ax.set_xticks(x)
    ax.set_xticklabels(fault_types)
    ax.set_xlabel("Fault Type")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy by Fault Type")
    ax.set_ylim(0.95, 1.005)
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    for i, (ra, sa) in enumerate(zip(rf_accs, svm_accs)):
        ax.text(i - w/2, ra + 0.0003, f"{ra:.4f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + w/2, sa + 0.0003, f"{sa:.4f}", ha="center", va="bottom", fontsize=8)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "stress_fault_type.png", dpi=150)
    plt.close(fig)
    print("  Saved: stress_fault_type.png")
    return rows

# ---------------------------------------------------------------------------
# 2. Accuracy by DER penetration level
# ---------------------------------------------------------------------------

def stress_der_level(df, X, y, rf, svm):
    print("\n--- Stress: DER Penetration Level ---")

    def parse_pct(label):
        return int(label.replace("DG_", "").replace("pct", ""))

    rows = []
    for label in sorted(df["scenario_label"].unique(), key=parse_pct):
        mask = (df["scenario_label"] == label).values
        rf_acc  = accuracy_score(y[mask], rf.predict(X[mask]))
        svm_acc = accuracy_score(y[mask], svm.predict(X[mask]))
        n = mask.sum()
        pct = parse_pct(label)
        print(f"  {label:12s}  n={n:5d}  RF={rf_acc:.4f}  SVM={svm_acc:.4f}")
        rows.append({"slice": "der_level", "value": label,
                     "pct": pct, "n": n, "rf_acc": rf_acc, "svm_acc": svm_acc})

    pcts    = [r["pct"]     for r in rows]
    rf_accs = [r["rf_acc"]  for r in rows]
    svm_accs= [r["svm_acc"] for r in rows]

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(pcts, rf_accs,  marker="o", label="Random Forest", color="#2c7bb6")
    ax.plot(pcts, svm_accs, marker="s", label="SVM (RBF)",     color="#d7191c", linestyle="--")
    ax.set_xlabel("DER Penetration Level (%)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Accuracy vs DER Penetration Level")
    ax.set_xticks(pcts)
    ax.tick_params(axis="x", rotation=45)
    ax.set_ylim(0.95, 1.005)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "stress_der_level.png", dpi=150)
    plt.close(fig)
    print("  Saved: stress_der_level.png")
    return rows

# ---------------------------------------------------------------------------
# 3. Accuracy under noise injection
# ---------------------------------------------------------------------------

def stress_noise(X, y, rf, svm, feature_cols):
    print("\n--- Stress: Noise Injection (IEEE C57.13) ---")
    rng = np.random.default_rng(42)
    # C57.13 accuracy classes: noise σ = class% of each feature's mean rated value
    means = np.abs(X.mean(axis=0))
    c5713_classes = [
        (0.000, "Clean"),
        (0.003, "Class 0.3"),
        (0.006, "Class 0.6"),
        (0.012, "Class 1.2"),
        (0.024, "Class 2.4"),
    ]
    rows = []

    for sigma, label in c5713_classes:
        if sigma == 0.0:
            X_noisy = X
        else:
            noise   = rng.normal(0, sigma * means, size=X.shape).astype(np.float32)
            X_noisy = X + noise

        rf_acc  = accuracy_score(y, rf.predict(X_noisy))
        svm_acc = accuracy_score(y, svm.predict(X_noisy))
        print(f"  {label:10s}  RF={rf_acc:.4f}  SVM={svm_acc:.4f}")
        rows.append({"slice": "noise", "value": label,
                     "sigma": sigma, "rf_acc": rf_acc, "svm_acc": svm_acc})

    labels   = [r["value"]   for r in rows]
    rf_accs  = [r["rf_acc"]  for r in rows]
    svm_accs = [r["svm_acc"] for r in rows]
    x        = np.arange(len(labels))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, rf_accs,  marker="o", label="Random Forest", color="#2c7bb6")
    ax.plot(x, svm_accs, marker="s", label="SVM (RBF)",     color="#d7191c", linestyle="--")
    ax.set_xlabel("IEEE C57.13 Accuracy Class (% of rated value)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Model Robustness to Measurement Noise\n(IEEE C57.13 Accuracy Classes)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0.95, 1.005)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    for xi, (ra, sa) in enumerate(zip(rf_accs, svm_accs)):
        ax.annotate(f"{ra:.4f}", (xi, ra), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=8, color="#2c7bb6")
        ax.annotate(f"{sa:.4f}", (xi, sa), textcoords="offset points", xytext=(0, -13),
                    ha="center", fontsize=8, color="#d7191c")
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "stress_noise.png", dpi=150)
    plt.close(fig)
    print("  Saved: stress_noise.png")
    return rows

# ---------------------------------------------------------------------------
# 4. Accuracy under smart meter dropout
# ---------------------------------------------------------------------------

def stress_dropout(df, X, y, rf, svm, feature_cols, rf_aug=None, svm_aug=None):
    print("\n--- Stress: Smart Meter Dropout ---")
    rng = np.random.default_rng(42)

    n_sm     = len([c for c in feature_cols if c.startswith("SM_")])
    sm_start = len(RFI_COLS)
    dropout_rates = [0.10, 0.25, 0.50, 0.75]
    has_aug = rf_aug is not None and svm_aug is not None
    rows = []

    for rate in dropout_rates:
        X_drop = X.copy()
        mask = rng.random(size=(len(X), n_sm)) < rate
        X_drop[:, sm_start:] = np.where(mask, 0.0, X_drop[:, sm_start:])

        rf_acc  = accuracy_score(y, rf.predict(X_drop))
        svm_acc = accuracy_score(y, svm.predict(X_drop))
        label   = f"{int(rate*100)}%"
        row = {"slice": "dropout", "value": label, "rate": rate,
               "rf_acc": rf_acc, "svm_acc": svm_acc}

        if has_aug:
            rf_aug_acc  = accuracy_score(y, rf_aug.predict(X_drop))
            svm_aug_acc = accuracy_score(y, svm_aug.predict(X_drop))
            row["rf_aug_acc"]  = rf_aug_acc
            row["svm_aug_acc"] = svm_aug_acc
            print(f"  {label} dropout  RF={rf_acc:.4f}  SVM={svm_acc:.4f}  "
                  f"RF_aug={rf_aug_acc:.4f}  SVM_aug={svm_aug_acc:.4f}")
        else:
            print(f"  {label} dropout  RF={rf_acc:.4f}  SVM={svm_acc:.4f}")
        rows.append(row)

    labels    = [r["value"]   for r in rows]
    rf_accs   = [r["rf_acc"]  for r in rows]
    svm_accs  = [r["svm_acc"] for r in rows]
    x = np.arange(len(labels))

    if has_aug:
        rf_aug_accs  = [r["rf_aug_acc"]  for r in rows]
        svm_aug_accs = [r["svm_aug_acc"] for r in rows]
        w = 0.20
        fig, ax = plt.subplots(figsize=(12, 6))
        b1 = ax.bar(x - 1.5*w, rf_accs,      w, label="RF (original)",   color="#2c7bb6")
        b2 = ax.bar(x - 0.5*w, svm_accs,     w, label="SVM (original)",  color="#d7191c")
        b3 = ax.bar(x + 0.5*w, rf_aug_accs,  w, label="RF (augmented)",  color="#1a9641")
        b4 = ax.bar(x + 1.5*w, svm_aug_accs, w, label="SVM (augmented)", color="#fdae61")
        for bars, vals, col in [(b1, rf_accs, "#2c7bb6"), (b2, svm_accs, "#d7191c"),
                                 (b3, rf_aug_accs, "#1a9641"), (b4, svm_aug_accs, "#fdae61")]:
            for bar, val in zip(bars, vals):
                ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                        f"{val:.3f}", ha="center", va="bottom", fontsize=7, color=col)
        ax.set_title("SM Dropout Robustness: Original vs Dropout-Augmented Models\n"
                     "(RFI monitors unaffected; green/orange = trained with augmentation)")
    else:
        w = 0.35
        fig, ax = plt.subplots(figsize=(9, 5))
        b1 = ax.bar(x - w/2, rf_accs,  w, label="Random Forest", color="#2c7bb6")
        b2 = ax.bar(x + w/2, svm_accs, w, label="SVM (RBF)",     color="#d7191c")
        for bar, val in zip(b1, rf_accs):
            ax.text(bar.get_x()+bar.get_width()/2, val+0.01, f"{val:.4f}",
                    ha="center", va="bottom", fontsize=8, color="#2c7bb6")
        for bar, val in zip(b2, svm_accs):
            ax.text(bar.get_x()+bar.get_width()/2, val+0.01, f"{val:.4f}",
                    ha="center", va="bottom", fontsize=8, color="#d7191c")
        ax.set_title("Accuracy vs Smart Meter Dropout\n"
                     "(physically realistic: meters lose power, RFI stays online)")

    ax.set_xlabel("Smart Meter Dropout Rate")
    ax.set_ylabel("Accuracy")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r}" for r in labels])
    ax.set_ylim(0, 1.10)
    ax.legend()
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    fig.savefig(FIGURES_DIR / "stress_dropout.png", dpi=150)
    plt.close(fig)
    print("  Saved: stress_dropout.png")
    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    df, X, y, feature_cols = load_all()
    rf, svm, rf_aug, svm_aug = load_models()
    print("Models loaded.")

    all_rows = []
    all_rows += stress_fault_type(df, X, y, rf, svm)
    all_rows += stress_der_level(df, X, y, rf, svm)
    all_rows += stress_noise(X, y, rf, svm, feature_cols)
    all_rows += stress_dropout(df, X, y, rf, svm, feature_cols, rf_aug, svm_aug)

    out = pd.DataFrame(all_rows)
    out.to_csv(RESULTS_DIR / "stress_test_results.csv", index=False)
    print(f"\nFull results saved to results/stress_test_results.csv")
