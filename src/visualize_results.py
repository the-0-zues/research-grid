"""
visualize_results.py
Generate figures for the Ckt7 SLG fault analysis.
Theodore Lodge | Manhattan University Jasper Summer Research Scholars

Usage:
    python visualize_results.py

Reads:  results/real_slg_features.csv
        results/real_slg_dropout.csv
Saves:  results/figures/
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

FEATURES_CSV = Path("results/real_slg_features.csv")
DROPOUT_CSV  = Path("results/real_slg_dropout.csv")
FIG_DIR      = Path("results/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)

# Consistent style
plt.rcParams.update({
    "font.family":   "sans-serif",
    "font.size":     11,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":    150,
})

BLUE   = "#185FA5"
RED    = "#E24B4A"
TEAL   = "#0F6E56"
AMBER  = "#BA7517"
GRAY   = "#888780"

# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------

df  = pd.read_csv(FEATURES_CSV)
dro = pd.read_csv(DROPOUT_CSV)

rfi_ids = df["rfi_id"].values
labels  = [f"RFI{i}" for i in rfi_ids]

# ---------------------------------------------------------------------------
# FIGURE 1 — Phase A voltage: baseline vs post-fault across all 20 monitors
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 4))

x = np.arange(len(rfi_ids))
w = 0.35

bars_base  = ax.bar(x - w/2, df["Va_mag_base"],  w, label="Baseline",   color=BLUE,  alpha=0.85)
bars_fault = ax.bar(x + w/2, df["Va_mag_fault"], w, label="Post-fault (SLG)", color=RED, alpha=0.85)

# Threshold line
threshold = dro["threshold_v"].mean()
ax.axhline(threshold, color=AMBER, linewidth=1.2, linestyle="--", label=f"0.5 pu threshold ({threshold:.0f} V)")

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("Phase A voltage magnitude (V)")
ax.set_title("Phase A voltage — baseline vs. post-fault SLG across 20 RFI monitors")
ax.legend()
ax.set_ylim(0, 8500)

plt.tight_layout()
plt.savefig(FIG_DIR / "fig1_voltage_baseline_vs_fault.png")
plt.close()
print("Saved: fig1_voltage_baseline_vs_fault.png")

# ---------------------------------------------------------------------------
# FIGURE 2 — Voltage ratio (fault/base) — shows fault severity gradient
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 4))

colors = [RED if v < 0.5 else TEAL for v in df["Va_mag_ratio"]]
ax.bar(labels, df["Va_mag_ratio"], color=colors, alpha=0.85, edgecolor="white")
ax.axhline(0.5, color=AMBER, linewidth=1.2, linestyle="--", label="0.5 pu threshold")

ax.set_ylabel("Va fault / Va baseline (ratio)")
ax.set_title("Phase A voltage ratio — fault severity gradient across feeder")
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
ax.set_ylim(0, 1.1)

dropout_patch = mpatches.Patch(color=RED,  label="Meter offline (V < 0.5 pu)")
online_patch  = mpatches.Patch(color=TEAL, label="Meter online")
ax.legend(handles=[dropout_patch, online_patch, 
                   plt.Line2D([0],[0], color=AMBER, linestyle="--", label="0.5 pu threshold")])

plt.tight_layout()
plt.savefig(FIG_DIR / "fig2_voltage_ratio.png")
plt.close()
print("Saved: fig2_voltage_ratio.png")

# ---------------------------------------------------------------------------
# FIGURE 3 — Voltage unbalance post-fault (key SLG signature)
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 4))

colors = [RED if m else TEAL for m in dro["meter_offline"]]
ax.bar(labels, df["V_unbalance_fault"], color=colors, alpha=0.85, edgecolor="white")

ax.set_ylabel("Voltage unbalance (NEMA ratio)")
ax.set_title("Post-fault voltage unbalance — SLG fault signature across feeder")
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

dropout_patch = mpatches.Patch(color=RED,  label="Meter offline")
online_patch  = mpatches.Patch(color=TEAL, label="Meter online")
ax.legend(handles=[dropout_patch, online_patch])

plt.tight_layout()
plt.savefig(FIG_DIR / "fig3_voltage_unbalance.png")
plt.close()
print("Saved: fig3_voltage_unbalance.png")

# ---------------------------------------------------------------------------
# FIGURE 4 — Dropout summary: which monitors went offline
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 3))

online  = [not m for m in dro["meter_offline"]]
offline = dro["meter_offline"].values

ax.bar(labels, [1]*20, color=[RED if o else TEAL for o in offline],
       alpha=0.85, edgecolor="white")

ax.set_yticks([])
ax.set_title("Smart meter dropout — SLG fault at bus 165487 (Phase A)")
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

n_offline = sum(offline)
n_online  = 20 - n_offline
dropout_patch = mpatches.Patch(color=RED,  label=f"Offline ({n_offline}/20)")
online_patch  = mpatches.Patch(color=TEAL, label=f"Online  ({n_online}/20)")
ax.legend(handles=[dropout_patch, online_patch])

# Annotate min voltage on each bar
for i, (label, row) in enumerate(dro.iterrows()):
    v = row["min_fault_v"]
    txt = f"{v:.0f}V" if v > 100 else f"{v:.0f}V"
    ax.text(i, 0.5, txt, ha="center", va="center",
            fontsize=7, color="white", fontweight="bold")

plt.tight_layout()
plt.savefig(FIG_DIR / "fig4_dropout_map.png")
plt.close()
print("Saved: fig4_dropout_map.png")

# ---------------------------------------------------------------------------
# FIGURE 5 — Delta voltage (absolute change) per monitor
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 4))

colors = [RED if m else TEAL for m in dro["meter_offline"]]
ax.bar(labels, df["Va_mag_delta"].abs(), color=colors, alpha=0.85, edgecolor="white")

ax.set_ylabel("|ΔVa| = |V_fault − V_base| (V)")
ax.set_title("Absolute Phase A voltage drop — SLG fault")
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)

dropout_patch = mpatches.Patch(color=RED,  label="Meter offline")
online_patch  = mpatches.Patch(color=TEAL, label="Meter online")
ax.legend(handles=[dropout_patch, online_patch])

plt.tight_layout()
plt.savefig(FIG_DIR / "fig5_voltage_delta.png")
plt.close()
print("Saved: fig5_voltage_delta.png")

# ---------------------------------------------------------------------------
# FIGURE 6 — All 3 phase voltage ratios (shows which phase faulted)
# ---------------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 5))

x = np.arange(len(rfi_ids))
w = 0.25

ax.bar(x - w,   df["Va_mag_ratio"], w, label="Phase A (faulted)", color=RED,   alpha=0.85)
ax.bar(x,       df["Vb_mag_ratio"], w, label="Phase B",           color=BLUE,  alpha=0.85)
ax.bar(x + w,   df["Vc_mag_ratio"], w, label="Phase C",           color=TEAL,  alpha=0.85)

ax.axhline(1.0, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.5)
ax.axhline(0.5, color=AMBER, linewidth=1.2, linestyle="--", label="0.5 pu")

ax.set_xticks(x)
ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
ax.set_ylabel("V_fault / V_base (ratio)")
ax.set_title("Three-phase voltage ratio — SLG Phase A fault signature")
ax.legend()
ax.set_ylim(0, 1.4)

plt.tight_layout()
plt.savefig(FIG_DIR / "fig6_three_phase_ratio.png")
plt.close()
print("Saved: fig6_three_phase_ratio.png")

print(f"\nAll figures saved to: {FIG_DIR.resolve()}")