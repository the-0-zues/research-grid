"""
dgsweep_build_6pmu.py
=====================
6-PMU variant of dgsweep_build.py. Adds PMU5 and PMU18 to the measurement set
(PMU2, PMU4, PMU5, PMU8, PMU11, PMU18 -> 6 PMUs, 31 feats each = 186 feats).

Two topology facts drive the change (see build_geometry):
  * PMU5 sits ON the PMU2->PMU11 trunk at km 1.044, between PMU4 (0.841 km)
    and PMU8 (1.907 km). It therefore SPLITS the old PMU4->PMU8 section into
    PMU4->PMU5 and PMU5->PMU8, so the bounding-pair distance chain now has
    4 sections instead of 3 -> finer two-ended fault-location resolution.
  * PMU18 is OFF the trunk (a branch tap in the PMU4..PMU8 region). It adds
    observability features only; it is not a new distance section.

Everything else mirrors dgsweep_build.py: same raws (all 19 PMUs are already
captured), same no-DG CT noise (via module B), same fuse-driven binary smart
meters and dropout sweep. Pure feature rebuild -- no re-simulation.

Layout:
  PMU_dataset_v2/DGsweep_6PMU/{n}DG/{Faulty,Clean}/{010,020,050,080,100}pct/results.csv
0DG: 10/20/50/80 ; 1-3DG: 10/20/50/80/100.
"""
import os, csv, json
import numpy as np
import pandas as pd
import advanced_pmu_fault_simulation as fs
import build_pmu_2_4_8_11_nodg as B          # 31-feat compute_features, geometry, distance; patches no-DG CT
from add_path_distance import topology, make_lateral_run

# ---- promote the 4-PMU module to 6 PMUs (PMU5 splits PMU4->PMU8) ----
B.TARGET = ["PMU2", "PMU4", "PMU5", "PMU8", "PMU11", "PMU18"]
B.PAIRS  = [("PMU2", "PMU4"), ("PMU4", "PMU5"), ("PMU5", "PMU8"), ("PMU8", "PMU11")]

BASE    = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\PMU_dataset_v2\DGsweep_6PMU"
FUSECSV = r"C:\EPRI_Ckt7_DER_Project\fuse_sizing_nodg.csv"
MAPJSON = r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\PMU_dataset_v2\Faulty\lateral_downstream_sm.json"
CANON = ["fault_id","fault_type","fault_line","fault_frac","zone","impedance_type",
         "r_ground","r_phase","load_L1","cap_CP_NR_613","cap_CP_85W_900",
         "chain_attach_km","fault_on_chain","converged"]
DROP = {0:[10,20,50,80], 1:[10,20,50,80,100], 2:[10,20,50,80,100], 3:[10,20,50,80,100]}
MELT_X = 2.0
NOISE_SEED = {"Faulty": 10000, "Clean": 2025000}

RATINGS = {r["line"].upper(): float(r["link"]) for r in csv.DictReader(open(FUSECSV))}
with open(MAPJSON) as f:
    DOWNSTREAM = json.load(f)

print("building geometry...")
PATHS, KM_AT, PARENT, BUS1 = B.build_geometry()
_m, _parent, _kmat, _chain = topology()
RUN_FN = make_lateral_run(_m, _parent, _kmat, _chain)
S24 = KM_AT[BUS1["PMU4"]]
S45 = KM_AT[BUS1["PMU5"]]
S58 = KM_AT[BUS1["PMU8"]]
S811 = KM_AT[BUS1["PMU11"]]
print(f"chain sections: PMU2->PMU4 [0.000,{S24:.3f}]  PMU4->PMU5 [{S24:.3f},{S45:.3f}]  "
      f"PMU5->PMU8 [{S45:.3f},{S58:.3f}]  PMU8->PMU11 [{S58:.3f},{S811:.3f}] km")


def prep(branch, n_dg):
    d = os.path.join(r"C:\EPRI_Ckt7_DER_Project\Realistic_Simulation\PMU_dataset_v2\DGsweep",
                     f"{n_dg}DG", branch)
    raw = pd.read_csv(os.path.join(d, "raw", "results.csv"), low_memory=False)
    if "sample_id" in raw.columns:
        raw = raw.rename(columns={"sample_id": "fault_id"})
    for c in CANON:
        if c not in raw.columns:
            raw[c] = np.nan
    sm_ids = [c[4:] for c in raw.columns if c.startswith("pre_SM")]
    all_labels = [l for l, _ in fs.PMU_LINES]

    noisy, _ = fs.apply_noise_to_raw(raw, all_labels, sm_ids, NOISE_SEED[branch])
    feats = B.compute_features(noisy, B.TARGET)

    dist  = pd.DataFrame(np.nan, index=raw.index, columns=[f"d_{a}_{b}_km" for a, b in B.PAIRS])
    truth = np.full(len(raw), np.nan)
    lat   = np.full(len(raw), np.nan)
    if branch == "Faulty":
        akm = pd.to_numeric(raw["chain_attach_km"], errors="coerce").to_numpy()
        bounds = {("PMU2","PMU4"): (0.0, S24), ("PMU4","PMU5"): (S24, S45),
                  ("PMU5","PMU8"): (S45, S58), ("PMU8","PMU11"): (S58, S811)}
        for pi, (a, b) in enumerate(B.PAIRS):
            lo, hi = bounds[(a, b)]
            sel = (~np.isnan(akm)) & ((akm >= lo) if pi == 0 else (akm > lo)) & (akm <= hi)
            if not sel.any():
                continue
            km, R, X = B.cum_profile(PATHS[(a, b)]); Zt = R[-1] + 1j*X[-1]
            sub = noisy.loc[sel]
            Va, Ia = B.seq1(sub, a, "V"), B.seq1(sub, a, "I")
            Vb, Ib = B.seq1(sub, b, "V"), B.seq1(sub, b, "I")
            den = Ia + Ib; bad = np.abs(den) < 1e-6
            Za = np.where(bad, np.nan, (Va - Vb + Zt*Ib) / np.where(bad, 1.0, den))
            dist.loc[sel, f"d_{a}_{b}_km"] = B.x_to_km(np.imag(Za), km, X)
            truth[sel] = akm[sel] - lo
        fl = raw["fault_line"].values; ff = pd.to_numeric(raw["fault_frac"], errors="coerce").values
        latv = np.array([RUN_FN(l, f) for l, f in zip(fl, ff)])
        lat = np.where(np.isnan(truth), np.nan, latv)
    true_path = truth + lat

    # base binary SM outage (0/1), pre-dropout
    sm_base = np.zeros((len(raw), len(sm_ids)), dtype=float)
    if branch == "Faulty":
        idx = {s: j for j, s in enumerate(sm_ids)}
        lc = pd.read_csv(os.path.join(d, "lateral_currents.csv")).set_index("fault_id").reindex(raw["fault_id"].values)
        for ln, rate in RATINGS.items():
            blown = pd.to_numeric(lc[ln], errors="coerce").to_numpy() > MELT_X*rate
            cols = [idx[s] for s in DOWNSTREAM.get(ln, []) if s in idx]
            if cols:
                sm_base[np.ix_(blown, cols)] = 1.0

    bad = ~raw["converged"].astype(bool).values
    feats.iloc[bad, :] = np.nan; dist.iloc[bad, :] = np.nan
    truth[bad] = np.nan; lat[bad] = np.nan; true_path[bad] = np.nan; sm_base[bad, :] = np.nan
    return raw[CANON].reset_index(drop=True), feats.reset_index(drop=True), dist.reset_index(drop=True), \
           truth, lat, true_path, sm_base, sm_ids


def write(n_dg, branch, dpct, prepped):
    meta, feats, dist, truth, lat, true_path, sm_base, sm_ids = prepped
    rng = np.random.default_rng(dpct*1000 + (1 if branch == "Faulty" else 2))
    sm = sm_base.copy()
    if dpct > 0:
        sm[rng.random(sm.shape) < dpct/100.0] = np.nan
    labels = pd.DataFrame({"true_dist_km": truth, "lateral_run_km": lat, "true_path_km": true_path})
    sm_df = pd.DataFrame(sm, columns=[f"{s}_outage" for s in sm_ids])
    full = pd.concat([meta, feats, dist.reset_index(drop=True), labels,
                      sm_df.reset_index(drop=True)], axis=1)
    out = os.path.join(BASE, f"{n_dg}DG", branch, f"{dpct:03d}pct")
    os.makedirs(out, exist_ok=True)
    full.to_csv(os.path.join(out, "results.csv"), index=False)
    return len(full.columns)


if __name__ == "__main__":
    for n in (0, 1, 2, 3):
        for branch in ("Faulty", "Clean"):
            p = prep(branch, n)
            # Faulty: full dropout sweep. Clean (normal ops): only the realistic
            # 10% meter dropout; higher rates are unphysical with no outage.
            levels = DROP[n] if branch == "Faulty" else [10]
            ncols = 0
            for dpct in levels:
                ncols = write(n, branch, dpct, p)
            print(f"{n}DG {branch}: {len(p[0])} rows x {ncols} cols  -> {len(levels)} dropout level(s)", flush=True)
    print("\nDONE")
