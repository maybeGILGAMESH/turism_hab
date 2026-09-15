# Starts the local Ollama server from .runtime\ollama (CPU mode by default).
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\env.ps1"

$exe = Join-Path $env:OLLAMA_BIN_DIR "ollama.exe"
if (-not (Test-Path $exe)) {
    Write-Warning "Ollama is not installed. Run scripts\install-ollama.ps1; the guide will answer from the knowledge base meanwhile."
    return
}
try {
    Invoke-RestMethod "http://$($env:OLLAMA_HOST)/api/version" -TimeoutSec 2 | Out-Null
    Write-Host "Ollama already running on $($env:OLLAMA_HOST)"
    return
}
catch { }

$logs = Join-Path $script:ProjectRoot "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null
Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logs "ollama.out.log") -RedirectStandardError (Join-Path $logs "ollama.err.log")
for ($i = 0; $i -lt 30; $i++) {
    try { Invoke-RestMethod "http://$($env:OLLAMA_HOST)/api/version" -TimeoutSec 2 | Out-Null; Write-Host "Ollama started on $($env:OLLAMA_HOST)"; return }
    catch { Start-Sleep -Seconds 1 }
}
throw "Ollama did not start; see logs\ollama.err.log"
