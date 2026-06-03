"""
Investigate MV bus count to reconcile with Jiang's ~200-203 primary nodes.
"""
import opendssdirect as dss
from collections import defaultdict

MASTER = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_allocated_base.dss"

dss.Basic.Start(0)
dss.Command(f"Compile [{MASTER}]")
dss.Command("Solve")

all_buses = dss.Circuit.AllBusNames()
print(f"Total buses in circuit: {len(all_buses)}")

# Collect kVBase for all buses
bus_kv = {}
for bus in all_buses:
    dss.Circuit.SetActiveBus(bus)
    bus_kv[bus.upper()] = dss.Bus.kVBase()

# Count by voltage level
from collections import Counter
kv_rounded = Counter(round(v, 2) for v in bus_kv.values())
print("\nBus count by kVBase (rounded):")
for kv, cnt in sorted(kv_rounded.items()):
    print(f"  {kv:.3f} kV : {cnt} buses")

# MV buses = nominally 7.2 kV (= 12.47/sqrt(3))
MV_KV = 12470 / 1.7321 / 1000  # 7.199 kV
mv_buses = [b.upper() for b, kv in bus_kv.items() if abs(kv - MV_KV) < 0.5]
print(f"\nMV buses (7.2 kV L-N, i.e. 12.47 kV L-L): {len(mv_buses)}")

# Find which buses are connected to at least one LINE (not just transformers)
# These are the true "primary node" buses
buses_with_line = set()
dss.Lines.First()
while True:
    b1 = dss.Lines.Bus1().split(".")[0].upper()
    b2 = dss.Lines.Bus2().split(".")[0].upper()
    if b1 in set(mv_buses):
        buses_with_line.add(b1)
    if b2 in set(mv_buses):
        buses_with_line.add(b2)
    if not dss.Lines.Next():
        break

print(f"MV buses connected to at least one line: {len(buses_with_line)}")

# Further filter: exclude buses that are ONLY transformer terminal nodes
# (i.e., connected to lines AND not just regulator/transformer internal buses)
# Check buses connected to lines but NOT to any load transformer secondary
# by looking at transformer winding buses
xfmr_winding_buses = set()
dss.Transformers.First()
while True:
    name = dss.Transformers.Name()
    n_windings = dss.Transformers.NumWindings()
    for w in range(1, n_windings + 1):
        dss.Transformers.Wdg(w)
        bus = dss.CktElement.BusNames()[w-1].split(".")[0].upper()
        xfmr_winding_buses.add(bus)
    if not dss.Transformers.Next():
        break

# Buses connected to lines but not exclusively transformer winding buses
# (some may be both - that's fine, they're real nodes)
line_only_mv = buses_with_line  # all line-connected MV buses

# Check: how many are ALSO transformer winding buses vs. not
both = buses_with_line & xfmr_winding_buses
line_only = buses_with_line - xfmr_winding_buses
print(f"  Of these: {len(line_only)} are NOT transformer winding buses (pure line nodes)")
print(f"  Of these: {len(both)} are ALSO transformer winding buses")
print(f"\nBest estimate of Jiang's primary nodes: {len(buses_with_line)}")
print(f"(Jiang reported ~200-203 for EPRI Ckt7)")
