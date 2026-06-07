"""
train_augmented.py
ML-Based Fault Zone Classification — EPRI Ckt7
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Identical to train.py but applies SM dropout augmentation to the training
set before fitting. For each training sample, each SM column is independently
zeroed with probability p, where p ~ Uniform(0, 0.50) per sample.
RFI columns are never touched. Test set is kept clean.

Purpose: teach the models to classify correctly even when smart meters have
lost power during a fault — the physically realistic failure mode identified
in the dropout stress test.
"""

import glob
import pickle
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split, GridSearchCV, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RESULTS_DIR  = Path(__file__).parent.parent / "results"
MODELS_DIR   = RESULTS_DIR / "models"
KRUN_GLOB    = str(Path(__file__).parent.parent / "Simulation_Results_KRun*" / "*" / "results_*.csv")
RESULTS_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

RANDOM_STATE   = 42
TEST_SIZE      = 0.20
N_FOLDS        = 5
N_RFI          = 20          # RFI columns are indices 0–19; SM columns start at 20
MAX_DROPOUT_P  = 0.50        # per-sample p ~ Uniform(0, MAX_DROPOUT_P)

RFI_COLS = [f"RFI{i}" for i in range(1, N_RFI + 1)]


# ---------------------------------------------------------------------------
# Load data  (identical to train.py)
# ---------------------------------------------------------------------------

def load_data():
    files = sorted(glob.glob(KRUN_GLOB))
    if not files:
        raise FileNotFoundError(f"No KRun result files found: {KRUN_GLOB}")
    print(f"  Loading {len(files)} scenario files...")
    df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
    n_before = len(df)
    df = df[df["converged"] == True].reset_index(drop=True)
    print(f"  Dropped {n_before - len(df)} non-converged → {len(df)} samples")
    sm_cols      = [c for c in df.columns if c.startswith("SM_")]
    feature_cols = RFI_COLS + sm_cols
    X = df[feature_cols].values.astype(np.float32)
    y = df["zone"].astype(str).values
    print(f"  X shape: {X.shape}  ({N_RFI} RFI + {len(sm_cols)} SM features)")
    return X, y, feature_cols


# ---------------------------------------------------------------------------
# SM dropout augmentation
# ---------------------------------------------------------------------------

def augment_training_data(X_train: np.ndarray, seed: int = RANDOM_STATE) -> np.ndarray:
    """
    For each training sample i:
      1. Draw p_i ~ Uniform(0, MAX_DROPOUT_P)
      2. Independently zero each SM column with probability p_i
    RFI columns (indices 0 to N_RFI-1) are never modified.
    Returns an augmented copy; X_train is unchanged.
    """
    rng      = np.random.default_rng(seed)
    X_aug    = X_train.copy()
    n        = len(X_aug)
    n_sm     = X_aug.shape[1] - N_RFI

    # p_i per sample, broadcast over SM columns
    p        = rng.uniform(0, MAX_DROPOUT_P, size=(n, 1))
    r        = rng.random(size=(n, n_sm))
    mask     = r < p                                      # True = zero out

    X_aug[:, N_RFI:] = np.where(mask, 0.0, X_aug[:, N_RFI:])

    n_zeroed = mask.sum()
    total_sm = n * n_sm
    print(f"  Augmentation: zeroed {n_zeroed:,} / {total_sm:,} SM entries "
          f"({n_zeroed / total_sm:.1%} of training SM values)")
    return X_aug


# ---------------------------------------------------------------------------
# Train Random Forest  (identical grid to train.py)
# ---------------------------------------------------------------------------

def train_random_forest(X_train, y_train):
    print("\n--- Training Augmented Random Forest ---")
    param_grid = {
        "n_estimators":      [100, 200, 300],
        "max_depth":         [None, 10, 20],
        "min_samples_split": [2, 5],
    }
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    rf = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=-1)
    gs = GridSearchCV(rf, param_grid, cv=cv, scoring="f1_weighted", n_jobs=-1, verbose=1)
    gs.fit(X_train, y_train)
    print(f"  Best params: {gs.best_params_}")
    print(f"  Best CV F1 (weighted): {gs.best_score_:.4f}")
    return gs.best_estimator_


# ---------------------------------------------------------------------------
# Train SVM  (identical grid to train.py)
# ---------------------------------------------------------------------------

def train_svm(X_train, y_train):
    print("\n--- Training Augmented SVM ---")
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("svm",    SVC(kernel="rbf", random_state=RANDOM_STATE,
                       decision_function_shape="ovr")),
    ])
    param_grid = {
        "svm__C":     [1, 10, 100],
        "svm__gamma": ["scale", 0.001],
    }
    cv = StratifiedKFold(n_splits=N_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    gs = GridSearchCV(pipeline, param_grid, cv=cv, scoring="f1_weighted", n_jobs=-1, verbose=1)
    gs.fit(X_train, y_train)
    print(f"  Best params: {gs.best_params_}")
    print(f"  Best CV F1 (weighted): {gs.best_score_:.4f}")
    return gs.best_estimator_


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------

def save_model(model, name: str):
    path = MODELS_DIR / f"{name}.pkl"
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"  Saved → {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    X, y, feature_cols = load_data()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\nTrain: {len(X_train)} samples | Test: {len(X_test)} samples")

    print("\nApplying SM dropout augmentation to training set...")
    X_train_aug = augment_training_data(X_train)

    rf_aug  = train_random_forest(X_train_aug, y_train)
    svm_aug = train_svm(X_train_aug, y_train)

    print("\nSaving augmented models...")
    save_model(rf_aug,  "rf_augmented")
    save_model(svm_aug, "svm_augmented")

    # Same seed → identical test set as train.py; safe to overwrite
    np.save(MODELS_DIR / "X_test.npy", X_test)
    np.save(MODELS_DIR / "y_test.npy", y_test)
    print("Saved test set.")

    print("\nDone. Run stress_test.py with augmented models to compare dropout robustness.")
