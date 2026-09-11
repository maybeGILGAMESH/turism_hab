$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
& "$PSScriptRoot\.venv\Scripts\python.exe" prepare_curated_dataset.py --target-index 12
