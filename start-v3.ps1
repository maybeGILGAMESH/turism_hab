# One command for version 3.0: Ollama (if installed) + API :8100 + Streamlit :8601 [+ Expo Web :8082].
param([switch]$WithExpo)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"

$python = "$PSScriptRoot\.venv\Scripts\python.exe"
$logs = Join-Path $PSScriptRoot "logs"
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Test-Port([int]$Port) { [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) }

& "$PSScriptRoot\scripts\start-ollama.ps1"

if (Test-Port 8100) { Write-Host "Port 8100 is already in use - API not started" }
else {
    Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100" `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
        -RedirectStandardOutput "$logs\api-v3.out.log" -RedirectStandardError "$logs\api-v3.err.log"
}
if (Test-Port 8601) { Write-Host "Port 8601 is already in use - Streamlit not started" }
else {
    $env:API_BASE_URL = "http://localhost:8100"
    Start-Process -FilePath $python -ArgumentList "-m", "streamlit", "run", "frontend.py", "--server.port", "8601", "--server.headless", "true" `
        -WorkingDirectory $PSScriptRoot -WindowStyle Hidden `
        -RedirectStandardOutput "$logs\streamlit-v3.out.log" -RedirectStandardError "$logs\streamlit-v3.err.log"
}
if ($WithExpo) {
    $env:EXPO_PUBLIC_API_BASE_URL = "http://localhost:8100"
    Start-Process -FilePath "npx.cmd" -ArgumentList "expo", "start", "--web", "--port", "8082" `
        -WorkingDirectory "$PSScriptRoot\mobile-app" -WindowStyle Hidden `
        -RedirectStandardOutput "$logs\expo-v3.out.log" -RedirectStandardError "$logs\expo-v3.err.log"
}

for ($i = 0; $i -lt 90; $i++) {
    try { $health = Invoke-RestMethod "http://localhost:8100/health" -TimeoutSec 3; break } catch { Start-Sleep -Seconds 2 }
}
if (-not $health) { throw "API v3 did not become healthy; see logs\api-v3.err.log" }
Write-Host ("API v3 {0}: status={1}, knowledge base {2}, local LLM={3}" -f $health.version, $health.status, $health.knowledge_base.version, $health.assistant.llm_available)
Write-Host "Web:       http://localhost:8100"
Write-Host "OpenAPI:   http://localhost:8100/docs"
Write-Host "Streamlit: http://localhost:8601"
if ($WithExpo) { Write-Host "Expo Web:  http://localhost:8082" }
