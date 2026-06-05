import opendssdirect as dss

MASTER = r"C:\EPRI_Ckt7_DER_Project\electricdss-code-r4133-trunk-Distrib-EPRITestCircuits-ckt7\ckt7\Master.dss"

dss.Basic.Start(0)
dss.Command(f"Compile [{MASTER}]")
dss.Command("Solve")

all_buses = dss.Circuit.AllBusNames()
MV_KV = 12470 / 1.7321 / 1000
mv_buses = []
for bus in all_buses:
    dss.Circuit.SetActiveBus(bus)
    if abs(dss.Bus.kVBase() - MV_KV) < 0.5:
        mv_buses.append(bus.upper())

print(f"Original ckt7 - Total buses: {len(all_buses)}, MV buses: {len(mv_buses)}")
print(f"Num elements: {dss.Circuit.NumCktElements()}")
