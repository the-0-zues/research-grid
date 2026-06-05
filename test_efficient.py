"""Test the efficient structure with 1 scenario and 5 faults."""
import sys, time
sys.path.insert(0, r"C:\EPRI_Ckt7_DER_Project")
import der_fault_simulation as sim
import opendssdirect as dss

dss.Basic.Start(0)
dss.Command(f"Compile [{sim.MASTER}]")
dss.Command("Solve")

mv_buses   = sim.get_3phase_mv_buses()
mv_bus_set = set(mv_buses)
adj, line_endpoints = sim.build_mv_adjacency(mv_bus_set)
line_zone, zone_lines = sim.assign_lines_to_zones(adj, line_endpoints, mv_bus_set)
faults    = sim.select_fault_locations(zone_lines, line_endpoints, mv_bus_set)
sm_list   = sim.load_smart_meters()
scenarios = sim.build_dg_scenarios(mv_buses)

# Add RFI monitors + pre-define faults
dss.Command(f"Redirect [{sim.RFI_DSS}]")
for fault in faults:
    sim.define_fault_disabled(fault)
dss.Command("Solve")

# Add scenario 1 DGs
for bus in scenarios[0]["new_buses"]:
    sim.add_dg(bus)
dss.Command("Solve")
print(f"Base after DGs converged: {dss.Solution.Converged()}")

# Run 5 faults
t0 = time.time()
for fault in faults[:5]:
    sim.enable_fault(fault["fault_name"])
    dss.Command("Solve")
    conv = dss.Solution.Converged()
    rfi  = sim.read_rfi_currents()
    sms  = sim.read_smart_meter_voltages(sm_list)
    sim.disable_fault(fault["fault_name"])
    # Count SM voltages below 0.5 pu (outage detection)
    outages = sum(1 for v in sms.values() if isinstance(v, float) and v < 0.5)
    print(f"  {fault['fault_id']} ({fault['fault_type']:6s}) | conv={conv} | "
          f"RFI1={rfi['RFI1']:8.1f}A | SM outages detected: {outages}/{len(sm_list)}")

elapsed = time.time() - t0
print(f"\n5 faults in {elapsed:.2f}s = {elapsed/5:.2f}s/fault")
print(f"Estimated total for 6000: {6000*(elapsed/5)/60:.1f} minutes")
