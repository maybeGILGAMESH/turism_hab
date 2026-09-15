$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$python = "$PSScriptRoot\.venv\Scripts\python.exe"
$env:API_BASE_URL = "http://localhost:8100"
Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
Start-Process -FilePath $python -ArgumentList "-m", "streamlit", "run", "frontend.py", "--server.port", "8601" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
Write-Host "API v3: http://localhost:8100  Streamlit v3: http://localhost:8601"
