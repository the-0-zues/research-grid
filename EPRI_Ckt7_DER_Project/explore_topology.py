"""
Explore Ckt7 topology: MV buses, RFI lines, zone structure.
"""
import opendssdirect as dss
from collections import defaultdict, deque

MASTER = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_allocated_base.dss"

RFI_LINES = [
    "215299","298366","157115","157152","157168","175038","255473","175060",
    "175064","175085","175087","182907","182915","157127","318388","175042",
    "262345","174952","175054","255389"
]

dss.Basic.Start(0)
dss.Command(f"Compile [{MASTER}]")
dss.Command("Solve")

# --- MV buses (12.47 kV base) ---
mv_buses = []
for bus in dss.Circuit.AllBusNames():
    dss.Circuit.SetActiveBus(bus)
    kv = dss.Bus.kVBase()
    if abs(kv - 7.199) < 0.5 or abs(kv - 12.47/1.732) < 0.5:  # 12.47kV L-N = 7.199
        mv_buses.append(bus.upper())

print(f"MV buses (12.47 kV): {len(mv_buses)}")

# --- Build adjacency from lines only (MV level) ---
# adj[bus] = list of (neighbor_bus, line_name)
adj = defaultdict(list)
line_buses = {}  # line_name -> (bus1, bus2)

dss.Lines.First()
while True:
    name = dss.Lines.Name().upper()
    b1 = dss.Lines.Bus1().split(".")[0].upper()
    b2 = dss.Lines.Bus2().split(".")[0].upper()
    line_buses[name] = (b1, b2)
    if b1 in set(mv_buses) and b2 in set(mv_buses):
        adj[b1].append((b2, name))
        adj[b2].append((b1, name))
    if not dss.Lines.Next():
        break

print(f"MV-to-MV line adjacency entries: {sum(len(v) for v in adj.values())//2} lines")

# --- Verify RFI lines exist ---
mv_bus_set = set(mv_buses)
rfi_line_buses = {}
for rfi_num, ln in enumerate(RFI_LINES, 1):
    ln_up = ln.upper()
    if ln_up in line_buses:
        b1, b2 = line_buses[ln_up]
        rfi_line_buses[f"RFI{rfi_num}"] = (b1, b2, ln_up)
        print(f"  RFI{rfi_num}: Line.{ln} | {b1} -> {b2} | MV: {b1 in mv_bus_set}/{b2 in mv_bus_set}")
    else:
        print(f"  RFI{rfi_num}: Line.{ln} NOT FOUND")

print(f"\nTotal RFI lines found: {len(rfi_line_buses)}/20")
