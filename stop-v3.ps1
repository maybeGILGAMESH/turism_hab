# Stops only the processes listening on the v3 ports (never the stable 8000/8501/8081).
foreach ($port in 8100, 8601, 8082) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Host "Stopped port $port (pid $($_.OwningProcess))" }
}
if ($args -contains "-Ollama") {
    Get-Process ollama -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*turism_hab_v3*" } | Stop-Process -Force
}
