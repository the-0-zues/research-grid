"""
dgsweep.py  -- shared setup for the DG-penetration sweep datasets.

  * new fault mix with BOLTED ground faults:
      SLG  500 wet / 500 dry / 400 bolted   (1400)
      LLG   75 wet /  75 dry /  50 bolted   ( 200)
      LL   300 arc                          ( 300)
      3PH  100 arc                          ( 100)
  * Cat 3520 DG model (real datasheet 1586422):
      pre-fault  -> Generator, 1600 kW / 2000 kVA / 0.8 pf  (correct dispatch)
      during-fault -> Vsource behind subtransient Z'' = Ra + jX''d, EMF 1.04 pu
      interconnection transformer: delta (gen) / grounded-wye (feeder), 5.75% Z
    Toggled per event so the DG dispatches normally, then contributes real
    fault current (an OpenDSS Generator alone contributes ~0 in snapshot).
"""
import random
import numpy as np
import opendssdirect as dss
import advanced_pmu_fault_simulation as fs

R_WET, R_DRY, R_BOLTED, R_ARC = 144.0, 288.0, 0.5, 2.0

# --- Cat 3520, arrangement 1586422 (2000 kVA, 480 V base; Z_base = 0.1152 ohm) ---
DG_KW, DG_KVA, DG_PF = 1600.0, 2000.0, 0.8
DG_KV_LV, DG_KV_HV = 0.48, 12.47
DG_RA_OHM  = 0.0019      # stator resistance
DG_XDPP_OHM = 0.0180     # subtransient X''d  (0.1563 pu)
DG_X0_OHM  = 0.0062      # zero sequence X0   (0.0538 pu)
DG_EMF_PU  = 1.04        # internal EMF behind Z'' during the fault
DG_XFMR_Z  = 5.75        # interconnection transformer %Z
DG_SITES   = ["181991", "181935", "181980"]   # 1001577, 1001933, 1000764 (MV buses)


_A = np.exp(1j * 2 * np.pi / 3)
def _seq1(v):
    return (v[0] + _A * v[1] + _A**2 * v[2]) / 3.0


def add_dgs(n):
    """Place n DGs on the biggest customers. Grounded-wye/grounded-wye
    interconnection (converges + makes the DG a feeder ground source).
    Generator (active) does pre-fault dispatch; Vsource (idle) is the
    subtransient fault source, its EMF set per event by dg_fault_mode."""
    for i in range(n):
        b, lv = DG_SITES[i], f"DGLV{i}"
        dss.Command(f"New Transformer.TDG{i} phases=3 windings=2 "
                    f"buses=[{b}.1.2.3, {lv}.1.2.3] kVs=[{DG_KV_HV},{DG_KV_LV}] "
                    f"kVAs=[{DG_KVA},{DG_KVA}] XHL={DG_XFMR_Z}")
        dss.Command(f"New Generator.GDG{i} bus1={lv}.1.2.3 kV={DG_KV_LV} "
                    f"kW={DG_KW} kVA={DG_KVA} pf=1.0 conn=wye model=1 status=fixed")
        dss.Command(f"New Vsource.VDG{i} bus1={lv}.1.2.3 basekv={DG_KV_LV} "
                    f"pu=1.0 phases=3 R1={DG_RA_OHM} X1={DG_XDPP_OHM} "
                    f"R0={DG_RA_OHM} X0={DG_X0_OHM} enabled=false")


def _eprime(i):
    """Internal subtransient EMF E'' = V1 + I1*Z'' for DG i, from the current
    (pre-fault) solve. I1 from the generator's power; V1 from its terminal bus
    read in actual volts (the LV bus has no assigned voltage base)."""
    dss.Circuit.SetActiveElement(f"Generator.GDG{i}")
    pw = dss.CktElement.Powers()
    P = -sum(pw[0:6:2]) * 1000.0
    Q = -sum(pw[1:6:2]) * 1000.0
    dss.Circuit.SetActiveBus(f"DGLV{i}")
    vm = dss.Bus.VMagAngle()
    V = [vm[2*k] * np.exp(1j * np.radians(vm[2*k+1])) for k in range(3)]
    V1 = _seq1(V)
    I1 = np.conj((P + 1j * Q) / (3.0 * V1))
    Epp = V1 + I1 * (DG_RA_OHM + 1j * DG_XDPP_OHM)
    return abs(Epp) * np.sqrt(3) / (DG_KV_LV * 1000), np.degrees(np.angle(Epp))


def dg_fault_mode(n):
    """Call AFTER the pre-fault solve: compute each DG's E'' from that operating
    point, then swap Generator -> Vsource(E'') for the during-fault solve."""
    for i in range(n):
        pu, ang = _eprime(i)
        dss.Command(f"Edit Generator.GDG{i} enabled=false")
        dss.Command(f"Edit Vsource.VDG{i} pu={pu:.5f} angle={ang:.3f} enabled=true")


def dg_normal_mode(n):
    """Pre-fault / normal ops: generator on, source off."""
    for i in range(n):
        dss.Command(f"Edit Generator.GDG{i} enabled=true")
        dss.Command(f"Edit Vsource.VDG{i} enabled=false")


def build_fault_list_bolted(mv_buses, bus_zone, seed=fs.FAULT_SEED):
    """2000 faults with the bolted-inclusive mix (types + impedances only;
    the mid-line line/frac is assigned later by the raw script)."""
    rng = random.Random(seed)
    faults = []

    def add(ftype, imp, rg, rp, n):
        for _ in range(n):
            bus = rng.choice(mv_buses)
            faults.append({"fault_type": ftype, "fault_bus": bus,
                           "zone": bus_zone.get(bus, 0), "impedance_type": imp,
                           "r_ground": rg, "r_phase": rp})

    # SLG: 500 wet / 500 dry / 400 bolted, round-robin across phases A/B/C
    slg = [("wet_grass", R_WET, 500), ("dry_grass", R_DRY, 500), ("bolted", R_BOLTED, 400)]
    for imp, rg, tot in slg:
        for k in range(tot):
            ph = "ABC"[k % 3]
            add(f"SLG_{ph}", imp, rg, "", 1)

    # LLG: 75 wet / 75 dry / 50 bolted, round-robin across phase pairs
    llg = [("wet_grass", R_WET, 75), ("dry_grass", R_DRY, 75), ("bolted", R_BOLTED, 50)]
    pairs = ["AB", "BC", "AC"]
    for imp, rg, tot in llg:
        for k in range(tot):
            add(f"LLG_{pairs[k % 3]}G", imp, rg, R_ARC, 1)

    # LL: 300 arc, 3PH: 100 arc
    for pp in ("AB", "BC", "CA"):
        add(f"LL_{pp}", "arc", "", R_ARC, 100)
    add("3PH", "arc", "", R_ARC, 100)

    rng.shuffle(faults)
    for i, f in enumerate(faults):
        f["fault_id"] = f"F{i + 1:04d}"
    return faults
