"""
evaluate.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Loads trained RF and SVM models and evaluates them on the held-out test set.
Outputs:
  - Classification accuracy and weighted F1-score
  - Per-class F1-scores
  - Confusion matrices (saved as PNG figures)
  - Summary CSV for easy comparison across experimental conditions
"""

import numpy as np
import pandas as pd
import pickle
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent.parent / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
MODELS_DIR  = RESULTS_DIR / "models"
CLASSES     = [str(i) for i in range(1, 21)]


# ---------------------------------------------------------------------------
# Load models and test data
# ---------------------------------------------------------------------------

def load_model(name: str):
    path = MODELS_DIR / f"{name}.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)


def load_test_data():
    X_test = np.load(MODELS_DIR / "X_test.npy")
    y_test = np.load(MODELS_DIR / "y_test.npy", allow_pickle=True)
    return X_test, y_test


# ---------------------------------------------------------------------------
# Evaluate one model
# ---------------------------------------------------------------------------

def evaluate_model(model, X_test, y_test, model_name: str) -> dict:
    """
    Evaluate a trained model on the test set.
    Returns a dict of metrics and prints a full report.
    """
    y_pred = model.predict(X_test)

    acc        = accuracy_score(y_test, y_pred)
    f1_weighted = f1_score(y_test, y_pred, average="weighted")
    f1_per_class = f1_score(y_test, y_pred, average=None, labels=CLASSES)

    print(f"\n{'='*50}")
    print(f"  {model_name}")
    print(f"{'='*50}")
    print(f"  Accuracy:          {acc:.4f}")
    print(f"  F1 (weighted):     {f1_weighted:.4f}")
    print(f"\n  Per-class F1:")
    for cls, score in zip(CLASSES, f1_per_class):
        print(f"    {cls}: {score:.4f}")
    print(f"\n  Full classification report:")
    display_names = [f"Zone {c}" for c in CLASSES]
    print(classification_report(y_test, y_pred, labels=CLASSES, target_names=display_names))

    return {
        "model":        model_name,
        "accuracy":     acc,
        "f1_weighted":  f1_weighted,
        **{f"f1_{cls}": s for cls, s in zip(CLASSES, f1_per_class)},
        "y_pred":       y_pred,
    }


# ---------------------------------------------------------------------------
# Confusion matrix plot
# ---------------------------------------------------------------------------

def plot_confusion_matrix(y_test, y_pred, model_name: str):
    """
    Save a confusion matrix heatmap to results/.

    Confusion matrices are reported in the paper to show per-zone
    classification performance — not just aggregate accuracy.
    """
    cm = confusion_matrix(y_test, y_pred, labels=CLASSES)

    fig, ax = plt.subplots(figsize=(14, 12))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASSES, yticklabels=CLASSES, ax=ax)
    ax.set_xlabel("Predicted Zone")
    ax.set_ylabel("True Zone")
    ax.set_title(f"Confusion Matrix — {model_name}")
    plt.tight_layout()

    out_path = FIGURES_DIR /f"confusion_{model_name.lower().replace(' ', '_')}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved confusion matrix: {out_path}")


# ---------------------------------------------------------------------------
# Bar chart — per-class F1 scores for RF vs SVM side by side
# ---------------------------------------------------------------------------

def plot_f1_bar_chart(rf_results: dict, svm_results: dict):
    """
    Bar chart comparing per-class F1-scores for RF vs SVM.
    This is easier to read at a glance than a confusion matrix
    and is suitable for inclusion in the paper.
    """
    x = np.arange(len(CLASSES))
    width = 0.35

    rf_f1  = [rf_results[f"f1_{c}"]  for c in CLASSES]
    svm_f1 = [svm_results[f"f1_{c}"] for c in CLASSES]

    fig, ax = plt.subplots(figsize=(16, 5))
    bars1 = ax.bar(x - width/2, rf_f1,  width, label="Random Forest", color="#2c7bb6")
    bars2 = ax.bar(x + width/2, svm_f1, width, label="SVM (RBF)",     color="#d7191c")

    ax.set_xlabel("Fault Zone")
    ax.set_ylabel("F1-Score")
    ax.set_title("Per-Class F1-Score: Random Forest vs SVM")
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES)
    ax.tick_params(axis='x', rotation=45)
    ax.set_ylim(0, 1.0)
    ax.legend()
    ax.bar_label(bars1, fmt="%.2f", padding=3, fontsize=9)
    ax.bar_label(bars2, fmt="%.2f", padding=3, fontsize=9)
    plt.tight_layout()

    out_path = FIGURES_DIR /"f1_bar_chart.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved F1 bar chart: {out_path}")


# ---------------------------------------------------------------------------
# Line chart — accuracy vs DER penetration level (simulated)
# ---------------------------------------------------------------------------

def plot_accuracy_vs_der(rf_model, svm_model):
    """
    Line chart showing how classifier accuracy changes across DER penetration levels.

    Until real multi-DER simulation data is available, this uses the synthetic
    generator to produce test sets at 0%, 25%, and 50% DER penetration.
    The DER level affects current magnitude in the synthetic model (see preprocess.py).

    In the final paper, replace synthetic_at_der() with real OpenDSS exports.
    """
    import sys
    sys.path.append(str(Path(__file__).parent))
    from Preprocess import generate_synthetic_data
    from sklearn.preprocessing import StandardScaler

    der_levels = [0, 25, 50]
    rf_accs, svm_accs = [], []

    for der in der_levels:
        # Generate a test set at this DER level only
        df = generate_synthetic_data(n_per_class=50, seed=der)
        df = df[df["der_level"].isin([0, 50])]  # use available levels as proxy

        feature_cols = [c for c in df.columns
                        if c not in ("label", "fault_type", "der_level")]
        X = df[feature_cols].values
        y = df["rfi_id"].astype(str).values

        rf_accs.append(accuracy_score(y, rf_model.predict(X)))
        svm_accs.append(accuracy_score(y, svm_model.predict(X)))

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(der_levels, rf_accs,  marker="o", label="Random Forest", color="#2c7bb6")
    ax.plot(der_levels, svm_accs, marker="s", label="SVM (RBF)",     color="#d7191c",
            linestyle="--")

    ax.set_xlabel("DER Penetration Level (%)")
    ax.set_ylabel("Accuracy")
    ax.set_title("Classifier Accuracy vs DER Penetration Level")
    ax.set_xticks(der_levels)
    ax.set_ylim(0, 1.0)
    ax.legend()
    ax.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()

    out_path = FIGURES_DIR /"accuracy_vs_der.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved accuracy vs DER chart: {out_path}")


# ---------------------------------------------------------------------------
# Helper — recover feature column names the same way train.py does
# ---------------------------------------------------------------------------

def _get_feature_cols():
    base = Path(__file__).parent.parent / "data" / "rfi_simulation"
    df = pd.read_csv(base / "der000" / "ckt7_alert_log_der000.csv", nrows=1)
    drop = {"fault_bus", "fault_type", "fault_R_ohm", "monitor_bus", "der_pct", "rfi_id"}
    return [c for c in df.columns if c not in drop]


# ---------------------------------------------------------------------------
# Diagnostic 1 — zone accuracy heatmap (RF vs SVM, side by side)
# ---------------------------------------------------------------------------

def plot_zone_accuracy_heatmap(rf_results: dict, svm_results: dict):
    data = np.array([
        [rf_results[f"f1_{c}"]  for c in CLASSES],
        [svm_results[f"f1_{c}"] for c in CLASSES],
    ])

    fig, ax = plt.subplots(figsize=(18, 2.5))
    sns.heatmap(
        data, ax=ax,
        cmap="RdYlGn", vmin=0, vmax=1,
        annot=True, fmt=".2f", annot_kws={"size": 8},
        linewidths=0.5, linecolor="white",
        xticklabels=[f"Z{c}" for c in CLASSES],
        yticklabels=["Random Forest", "SVM (RBF)"],
        cbar_kws={"shrink": 0.6, "label": "F1-Score"},
    )
    ax.set_title("Per-Zone F1-Score: Random Forest vs SVM (green = high, red = low)")
    ax.set_xlabel("Fault Zone")
    ax.tick_params(axis="x", rotation=0)
    plt.tight_layout()

    out_path = FIGURES_DIR /"zone_accuracy_heatmap.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved zone accuracy heatmap: {out_path}")


# ---------------------------------------------------------------------------
# Diagnostic 2 — RFI monitor dropout map
# ---------------------------------------------------------------------------

def plot_rfi_dropout_map():
    base = Path(__file__).parent.parent / "data" / "rfi_simulation"
    df = pd.concat([
        pd.read_csv(base / "der000" / "ckt7_alert_log_der000.csv"),
        pd.read_csv(base / "der050" / "ckt7_alert_log_der050.csv"),
    ], ignore_index=True)

    df["dropout"] = (df["Va_mag_pu"] < 0.5).astype(int)

    # Encode fault_bus as an ordered zone index (sorted so zone ordering is consistent)
    fault_buses = sorted(df["fault_bus"].unique())
    bus_to_idx  = {b: i + 1 for i, b in enumerate(fault_buses)}
    df["fault_zone_idx"] = df["fault_bus"].map(bus_to_idx)

    pivot = (
        df.groupby(["rfi_id", "fault_zone_idx"])["dropout"]
        .mean()
        .unstack(fill_value=0)
    )
    # Ensure full 20×20 grid
    pivot = pivot.reindex(index=range(1, 21), columns=range(1, 21), fill_value=0)

    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(
        pivot, ax=ax,
        cmap="YlOrRd", vmin=0, vmax=1,
        annot=False, linewidths=0.3, linecolor="lightgray",
        cbar_kws={"label": "Dropout Rate (Va < 0.5 pu)"},
    )
    ax.set_title("RFI Monitor Dropout Map\n(dark = monitor offline for that fault location)")
    ax.set_xlabel("Fault Bus Zone Index (1 = nearest substation)")
    ax.set_ylabel("RFI Monitor ID")
    plt.tight_layout()

    out_path = FIGURES_DIR /"rfi_dropout_map.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved RFI dropout map: {out_path}")


# ---------------------------------------------------------------------------
# Diagnostic 3 — feeder geography accuracy (zone 1→20 as feeder position proxy)
# ---------------------------------------------------------------------------

def plot_feeder_geography_accuracy(rf_results: dict, svm_results: dict):
    zones  = [int(c) for c in CLASSES]
    rf_f1  = [rf_results[f"f1_{c}"]  for c in CLASSES]
    svm_f1 = [svm_results[f"f1_{c}"] for c in CLASSES]

    fig, ax = plt.subplots(figsize=(14, 5))

    # Performance band backgrounds
    ax.axhspan(0.0, 0.4, alpha=0.08, color="red",    label="_bg_red")
    ax.axhspan(0.4, 0.7, alpha=0.08, color="orange", label="_bg_orange")
    ax.axhspan(0.7, 1.0, alpha=0.08, color="green",  label="_bg_green")

    ax.plot(zones, rf_f1,  marker="o", linewidth=2,   color="#1a9641", label="Random Forest")
    ax.plot(zones, svm_f1, marker="s", linewidth=2,   color="#d7191c", label="SVM (RBF)",
            linestyle="--")

    ax.axhline(0.7, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)
    ax.axhline(0.4, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)

    ax.set_xlabel("Zone ID  (1 = near substation  →  20 = far end of feeder)")
    ax.set_ylabel("F1-Score")
    ax.set_title("Feeder Geography Accuracy: RF vs SVM by Zone")
    ax.set_xticks(zones)
    ax.set_xlim(0.5, 20.5)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="lower left")
    ax.grid(True, linestyle="--", alpha=0.3)

    # Zone label annotations for poor performers (F1 < 0.3)
    for z, f in zip(zones, rf_f1):
        if f < 0.3:
            ax.annotate(f"Z{z}", (z, f), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=7, color="#1a9641")

    plt.tight_layout()

    out_path = FIGURES_DIR /"feeder_geography_accuracy.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved feeder geography accuracy: {out_path}")


# ---------------------------------------------------------------------------
# Diagnostic 4 — misclassification patterns (off-diagonal CM + distance histogram)
# ---------------------------------------------------------------------------

def plot_misclassification_patterns(y_test, rf_pred, svm_pred):
    int_labels = [int(c) for c in CLASSES]

    fig, axes = plt.subplots(1, 2, figsize=(18, 7))

    # --- Left: RF off-diagonal confusion heatmap ---
    cm_rf = confusion_matrix(y_test, rf_pred, labels=CLASSES, normalize="true")
    np.fill_diagonal(cm_rf, 0)   # blank correct predictions to highlight errors
    sns.heatmap(
        cm_rf, ax=axes[0],
        cmap="Blues", vmin=0, vmax=0.5,
        xticklabels=CLASSES, yticklabels=CLASSES,
        cbar_kws={"label": "Misclassification Rate"},
        linewidths=0.3, linecolor="lightgray",
    )
    axes[0].set_title("RF Misclassification Heatmap\n(diagonal blanked — errors only)")
    axes[0].set_xlabel("Predicted Zone")
    axes[0].set_ylabel("True Zone")

    # --- Right: confusion distance histogram for RF and SVM ---
    def confusion_distances(y_true, y_pred_arr):
        mask = np.array(y_true) != np.array(y_pred_arr)
        true_int = np.array([int(v) for v in y_true])[mask]
        pred_int = np.array([int(v) for v in y_pred_arr])[mask]
        return np.abs(true_int - pred_int)

    rf_dists  = confusion_distances(y_test, rf_pred)
    svm_dists = confusion_distances(y_test, svm_pred)
    max_dist  = max(rf_dists.max(), svm_dists.max()) if len(rf_dists) and len(svm_dists) else 19
    bins = np.arange(1, max_dist + 2) - 0.5

    axes[1].hist(rf_dists,  bins=bins, alpha=0.7, color="#2c7bb6", label="Random Forest",
                 edgecolor="white", density=True)
    axes[1].hist(svm_dists, bins=bins, alpha=0.7, color="#d7191c", label="SVM (RBF)",
                 edgecolor="white", density=True)
    axes[1].set_xlabel("|True Zone − Predicted Zone|  (1 = adjacent zone error)")
    axes[1].set_ylabel("Density of Misclassifications")
    axes[1].set_title("Confusion Distance Distribution\n(left-skewed = errors stay nearby)")
    axes[1].legend()
    axes[1].grid(True, linestyle="--", alpha=0.3)

    plt.tight_layout()

    out_path = FIGURES_DIR /"misclassification_patterns.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved misclassification patterns: {out_path}")


# ---------------------------------------------------------------------------
# Diagnostic 5 — RF feature importance (physics check)
# ---------------------------------------------------------------------------

def plot_rfi_feature_importance(rf_model):
    feature_cols  = _get_feature_cols()
    importances   = rf_model.feature_importances_
    order         = np.argsort(importances)[::-1]
    sorted_feats  = [feature_cols[i] for i in order]
    sorted_imps   = importances[order]

    # Color by signal type
    def feat_color(name):
        if "mag" in name and name.startswith("V"):  return "#2166ac"   # V magnitude
        if "ang" in name and name.startswith("V"):  return "#74add1"   # V angle
        if "mag" in name and name.startswith("I"):  return "#d73027"   # I magnitude
        return "#f4a582"                                                # I angle

    colors = [feat_color(f) for f in sorted_feats]

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(sorted_feats[::-1], sorted_imps[::-1], color=colors[::-1])
    ax.set_xlabel("Feature Importance (mean decrease in impurity)")
    ax.set_title("Random Forest Feature Importance\n(physics check: current magnitude should dominate)")
    ax.set_xlim(0, sorted_imps[0] * 1.15)

    # Legend patches
    from matplotlib.patches import Patch
    legend_items = [
        Patch(color="#d73027", label="Current magnitude (Ia/Ib/Ic_mag_A)"),
        Patch(color="#f4a582", label="Current angle (Ia/Ib/Ic_ang_deg)"),
        Patch(color="#2166ac", label="Voltage magnitude (Va/Vb/Vc_mag_pu)"),
        Patch(color="#74add1", label="Voltage angle (Va/Vb/Vc_ang_deg)"),
    ]
    ax.legend(handles=legend_items, loc="lower right", fontsize=9)
    ax.grid(True, axis="x", linestyle="--", alpha=0.3)
    plt.tight_layout()

    out_path = FIGURES_DIR /"rfi_feature_importance.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved RFI feature importance: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    FIGURES_DIR.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)

    print("Loading test data and models...")
    X_test, y_test = load_test_data()
    rf_model  = load_model("rf_model")
    svm_model = load_model("svm_model")

    # Evaluate both
    rf_results  = evaluate_model(rf_model,  X_test, y_test, "Random Forest")
    svm_results = evaluate_model(svm_model, X_test, y_test, "SVM (RBF)")

    # Confusion matrices
    print("\nGenerating confusion matrices...")
    plot_confusion_matrix(y_test, rf_results["y_pred"],  "Random Forest")
    plot_confusion_matrix(y_test, svm_results["y_pred"], "SVM RBF")

    # Bar chart
    print("\nGenerating F1 bar chart...")
    plot_f1_bar_chart(rf_results, svm_results)

    # Line chart (placeholder — requires real multi-DER simulation data)
    print("\nGenerating accuracy vs DER line chart...")
    try:
        plot_accuracy_vs_der(rf_model, svm_model)
    except Exception as e:
        print(f"  Skipped (synthetic data schema mismatch): {e}")

    # Diagnostic visualizations
    print("\nGenerating diagnostic plots...")
    plot_zone_accuracy_heatmap(rf_results, svm_results)
    plot_rfi_dropout_map()
    plot_feeder_geography_accuracy(rf_results, svm_results)
    plot_misclassification_patterns(y_test, rf_results["y_pred"], svm_results["y_pred"])
    plot_rfi_feature_importance(rf_model)

    # Summary table
    summary = pd.DataFrame([
        {k: v for k, v in rf_results.items()  if k != "y_pred"},
        {k: v for k, v in svm_results.items() if k != "y_pred"},
    ])
    summary_path = RESULTS_DIR / "metrics_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nMetrics summary saved to {summary_path}")
    print("\n" + summary.to_string(index=False))