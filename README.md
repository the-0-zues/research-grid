# ML-Based Fault Zone Classification in DER-Integrated Distribution Feeders

**Manhattan University — Jasper Summer Research Scholars**  
Theodore Lodge & Olt Lecaj | Advisor: Prof. Mahmoud Amin

## Overview

This repository contains the machine learning pipeline for fault zone classification on the EPRI Ckt7 distribution feeder under degraded sensor conditions. The study evaluates Random Forest (RF) and Support Vector Machine (SVM) classifiers for fault zone identification under varying DER penetration levels (0% and 50%), smart meter dropout (0% and 50%), and measurement noise.

Fault types simulated: Single-Line-to-Ground (SLG), Line-to-Line (LL), and Three-Phase.

## Repository Structure

```
research-grid/
├── data/              # Simulation exports from OpenDSS (not tracked in git)
├── notebooks/         # Jupyter notebooks for exploration and figures
├── src/               # ML pipeline scripts
│   ├── preprocess.py  # Dropout, noise injection, feature engineering
│   ├── train.py       # RF and SVM training with GridSearchCV + 5-fold CV
│   └── evaluate.py    # Metrics: accuracy, F1, confusion matrix
├── results/           # Output figures and metric reports
└── README.md
```

## Division of Work

| Component | Responsible |
|---|---|
| OpenDSS feeder modeling (0% and 50% DER) | Olt Lecaj |
| Fault simulation and data export | Olt Lecaj |
| Python preprocessing pipeline | Theodore Lodge |
| RF and SVM training and evaluation | Theodore Lodge |
| Paper writing and figures | Both |

## Setup

```bash
python3 -m venv ~/ml_env
source ~/ml_env/bin/activate
pip install scikit-learn pandas numpy matplotlib seaborn jupyter
```

## Data

Raw simulation data (Olt's OpenDSS exports) goes in `data/` and is not tracked by git due to file size. See `data/README.md` for expected column format once finalized with Olt.

## References

- Jiang, Y. (2020). Data-driven fault location of electric power distribution systems with distributed generation. *IEEE Transactions on Smart Grid, 11*(1), 129–137.
- Zaben et al. (2024). Machine learning methods for fault diagnosis in AC microgrids. *IEEE Access, 12*, 20260–20298.
- IEEE Std C57.13-2016 (noise bounds for measurement accuracy classes)
