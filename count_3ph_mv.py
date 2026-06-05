import opendssdirect as dss

MASTER = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_allocated_base.dss"
dss.Basic.Start(0)
dss.Command(f"Compile [{MASTER}]")
dss.Command("Solve")

MV_KV = 12470 / 1.7321 / 1000

three_phase_mv = []
for bus in dss.Circuit.AllBusNames():
    dss.Circuit.SetActiveBus(bus)
    kv = dss.Bus.kVBase()
    nphases = dss.Bus.NumNodes()
    if abs(kv - MV_KV) < 0.5 and nphases >= 3:
        three_phase_mv.append(bus.upper())

print(f"3-phase MV buses: {len(three_phase_mv)}")
print("Sample:", three_phase_mv[:10])

# Check the 4 existing DG buses
existing = {"253842","165476","165448","283954"}
for b in existing:
    print(f"  Existing DG bus {b} in 3-phase MV set: {b in set(three_phase_mv)}")
