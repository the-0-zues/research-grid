import opendssdirect as dss

dss.Basic.Start(0)
master = r"C:\EPRI_Ckt7_DER_Project\02_Base_Allocated\Master_ckt7_allocated_base.dss"
dss.run_command(f"Compile [{master}]")
dss.run_command("Solve")
print("Circuit:", dss.Circuit.Name())
print("Num buses:", dss.Circuit.NumBuses())
print("Num elements:", dss.Circuit.NumCktElements())
print("Solve mode:", dss.Solution.ModeID())
print("Converged:", dss.Solution.Converged())
