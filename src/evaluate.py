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
CLASSES     = ["zone1", "zone2", "zone3"]


# ---------------------------------------------------------------------------
# Load models and test data
# ---------------------------------------------------------------------------

def load_model(name: str):
    path = RESULTS_DIR / f"{name}.pkl"
    with open(path, "rb") as f:
        return pickle.load(f)


def load_test_data():
    X_test = np.load(RESULTS_DIR / "X_test.npy")
    y_test = np.load(RESULTS_DIR / "y_test.npy", allow_pickle=True)
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
    print(classification_report(y_test, y_pred, target_names=CLASSES))

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

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=CLASSES, yticklabels=CLASSES, ax=ax)
    ax.set_xlabel("Predicted Zone")
    ax.set_ylabel("True Zone")
    ax.set_title(f"Confusion Matrix — {model_name}")
    plt.tight_layout()

    out_path = RESULTS_DIR / f"confusion_{model_name.lower().replace(' ', '_')}.png"
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

    fig, ax = plt.subplots(figsize=(7, 5))
    bars1 = ax.bar(x - width/2, rf_f1,  width, label="Random Forest", color="#2c7bb6")
    bars2 = ax.bar(x + width/2, svm_f1, width, label="SVM (RBF)",     color="#d7191c")

    ax.set_xlabel("Fault Zone")
    ax.set_ylabel("F1-Score")
    ax.set_title("Per-Class F1-Score: Random Forest vs SVM")
    ax.set_xticks(x)
    ax.set_xticklabels(CLASSES)
    ax.set_ylim(0, 1.0)
    ax.legend()
    ax.bar_label(bars1, fmt="%.2f", padding=3, fontsize=9)
    ax.bar_label(bars2, fmt="%.2f", padding=3, fontsize=9)
    plt.tight_layout()

    out_path = RESULTS_DIR / "f1_bar_chart.png"
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
        y = df["label"].values

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

    out_path = RESULTS_DIR / "accuracy_vs_der.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved accuracy vs DER chart: {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
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

    # Line chart
    print("\nGenerating accuracy vs DER line chart...")
    plot_accuracy_vs_der(rf_model, svm_model)

    # Summary table
    summary = pd.DataFrame([
        {k: v for k, v in rf_results.items()  if k != "y_pred"},
        {k: v for k, v in svm_results.items() if k != "y_pred"},
    ])
    summary_path = RESULTS_DIR / "metrics_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"\nMetrics summary saved to {summary_path}")
    print("\n" + summary.to_string(index=False))