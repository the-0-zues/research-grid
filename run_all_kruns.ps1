cd C:\EPRI_Ckt7_DER_Project
foreach ($k in 4..10) {
    Write-Host "===== Starting K-Run $k =====" 
    python "C:\EPRI_Ckt7_DER_Project\der_fault_simulation_krun$k.py"
    Write-Host "===== Finished K-Run $k ====="
}
Write-Host "ALL DONE"
