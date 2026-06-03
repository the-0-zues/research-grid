"""
train.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Trains Random Forest and SVM classifiers on the preprocessed feature matrix.
Uses 5-fold cross-validation and GridSearchCV for hyperparameter tuning.
Saves trained models to results/ for use in evaluate.py.
"""

import numpy as np
import pandas as pd
import pickle
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Import our preprocessor
import sys
sys.path.append(str(Path(__file__).parent))
from Preprocess import generate_synthetic_data


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

RANDOM_STATE = 42
TEST_SIZE    = 0.20   # 80/20 train-test split (per paper proposal)
N_FOLDS      = 5      # 5-fold cross-validation


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_data(csv_path: str = None):
    """
    Load the feature matrix. Uses synthetic data if no CSV path given.
    When Olt's data is ready, pass the path to the real CSV instead.
    """
    if csv_path and Path(csv_path).exists():
        print(f"Loading real data from {csv_path}")
        df = pd.read_csv(csv_path)
    else:
        print("No data CSV found — using synthetic data for development.")
        df = generate_synthetic_data(n_per_class=50)

    feature_cols = [c for c in df.columns
                    if c not in ("label", "fault_type", "der_level")]

    X = df[feature_cols].values
    y = df["label"].values          # fault zone labels (zone1, zone2, zone3)

    print(f"  X shape: {X.shape}")
    print(f"  Classes: {np.unique(y)}")
    return X, y, feature_cols


# ---------------------------------------------------------------------------
# Train Random Forest
# ---------------------------------------------------------------------------

def train_random_forest(X_train, y_train):
    """
    Train a Random Forest classifier with GridSearchCV hyperparameter tuning.

    RF is chosen because:
      - Robust to noisy and missing data (relevant given our dropout experiments)
      - Provides feature importances (useful for paper discussion)
      - No feature scaling required

    Hyperparameters searched:
      n_estimators : number of trees
      max_depth    : controls overfitting
      min_samples_split : minimum samples to split a node
    """
    print("\n--- Training Random Forest ---")

    param_grid = {
        "n_estimators":     [100, 200, 300],
        "max_depth":        [None, 10, 20],
        "min_samples_split": [2, 5],
    }

    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True,
                         random_state=RANDOM_STATE)

    rf = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)

    grid_search = GridSearchCV(rf, param_grid, cv=cv,
                               scoring="f1_weighted", n_jobs=-1, verbose=1)
    grid_search.fit(X_train, y_train)

    print(f"  Best params: {grid_search.best_params_}")
    print(f"  Best CV F1 (weighted): {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_


# ---------------------------------------------------------------------------
# Train SVM
# ---------------------------------------------------------------------------

def train_svm(X_train, y_train):
    """
    Train an SVM classifier with RBF kernel and GridSearchCV tuning.

    SVM is chosen because:
      - Effective in high-dimensional feature spaces
      - RBF kernel handles nonlinear fault boundaries
      - Shown to be highly accurate for fault detection in distribution networks

    NOTE: SVM requires feature scaling — we wrap it in a Pipeline with
    StandardScaler so scaling is fit on training data only (no data leakage).

    Hyperparameters searched:
      C     : regularization strength
      gamma : RBF kernel width
    """
    print("\n--- Training SVM ---")

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    SVC(kernel="rbf", random_state=RANDOM_STATE,
                       decision_function_shape="ovr")),
    ])

    param_grid = {
        "svm__C":     [0.1, 1, 10, 100],
        "svm__gamma": ["scale", "auto", 0.01, 0.001],
    }

    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True,
                         random_state=RANDOM_STATE)

    grid_search = GridSearchCV(pipeline, param_grid, cv=cv,
                               scoring="f1_weighted", n_jobs=-1, verbose=1)
    grid_search.fit(X_train, y_train)

    print(f"  Best params: {grid_search.best_params_}")
    print(f"  Best CV F1 (weighted): {grid_search.best_score_:.4f}")

    return grid_search.best_estimator_


# ---------------------------------------------------------------------------
# Save models
# ---------------------------------------------------------------------------

def save_model(model, name: str):
    path = RESULTS_DIR / f"{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"  Saved to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Load data
    X, y, feature_cols = load_data(
        csv_path=str(RESULTS_DIR / "synthetic_features.csv")
    )

    # Train/test split — stratified so class balance is preserved
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE,
        random_state=RANDOM_STATE, stratify=y
    )
    print(f"\nTrain: {len(X_train)} samples | Test: {len(X_test)} samples")

    # Train both classifiers
    rf_model  = train_random_forest(X_train, y_train)
    svm_model = train_svm(X_train, y_train)

    # Save for evaluate.py
    print("\nSaving models...")
    save_model(rf_model,  "rf_model")
    save_model(svm_model, "svm_model")

    # Also save the test set so evaluate.py can load it
    np.save(RESULTS_DIR / "X_test.npy", X_test)
    np.save(RESULTS_DIR / "y_test.npy", y_test)
    print("Saved test set.")

    print("\nDone. Run evaluate.py next.")