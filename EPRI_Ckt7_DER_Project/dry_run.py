"""Quick dry run: topology, zone assignment, fault selection, scenario list only."""
import sys
sys.path.insert(0, r"C:\EPRI_Ckt7_DER_Project")
import der_fault_simulation as sim

sim.load_base_circuit()
mv_buses   = sim.get_3phase_mv_buses()
mv_bus_set = set(mv_buses)
print(f"3-phase MV buses: {len(mv_buses)}")

adj, line_endpoints = sim.build_mv_adjacency(mv_bus_set)
line_zone, zone_lines = sim.assign_lines_to_zones(adj, line_endpoints, mv_bus_set)

print("\nZone line counts:")
for z in range(sim.N_ZONES):
    lines = zone_lines.get(z, [])
    print(f"  Zone {z+1:2d} (RFI{z+1}): {len(lines)} lines")

faults = sim.select_fault_locations(zone_lines, line_endpoints, mv_bus_set)
print(f"\nTotal faults selected: {len(faults)}")
from collections import Counter
for ft, cnt in Counter(f['fault_type'] for f in faults).items():
    print(f"  {ft}: {cnt}")

print("\nFault sample (first 5):")
for f in faults[:5]:
    print(f"  {f}")

scenarios = sim.build_dg_scenarios(mv_buses)
print(f"\nScenarios: {len(scenarios)}")
for s in scenarios:
    print(f"  Scenario {s['scenario_id']:2d} | {s['label']:12s} | {len(s['all_buses'])} buses cumulative")

# Test one fault run
print("\nTest: running 1 fault (Scenario 1, Fault 1)...")
r = sim.run_one_fault(scenarios[0]["all_buses"], faults[0])
if r:
    print("  Converged. RFI readings:")
    for k, v in list(r.items())[:5]:
        print(f"    {k}: {v:.2f} A")
else:
    print("  DID NOT CONVERGE")
