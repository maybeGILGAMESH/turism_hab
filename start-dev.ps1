$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$python = "$PSScriptRoot\.venv\Scripts\python.exe"
Start-Process -FilePath $python -ArgumentList "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
Start-Process -FilePath $python -ArgumentList "-m", "streamlit", "run", "frontend.py", "--server.port", "8501" -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
Write-Host "API: http://localhost:8000  Streamlit: http://localhost:8501"
