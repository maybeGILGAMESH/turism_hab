$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"

if (-not (Test-Path "$env:UV_INSTALL_DIR\uv.exe")) {
    Write-Host "Installing uv on E:"
    powershell -ExecutionPolicy ByPass -Command "`$env:UV_INSTALL_DIR='$env:UV_INSTALL_DIR'; `$env:UV_NO_MODIFY_PATH='1'; irm https://astral.sh/uv/install.ps1 | iex"
}

& "$env:UV_INSTALL_DIR\uv.exe" python install 3.11.16 --install-dir "$env:UV_PYTHON_INSTALL_DIR"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & "$env:UV_INSTALL_DIR\uv.exe" venv --python 3.11.16 --managed-python .venv
}
& "$env:UV_INSTALL_DIR\uv.exe" sync --extra data --extra ui --group dev
& "$PSScriptRoot\scripts\cache-model.ps1"

if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if (-not (Test-Path "dataset\manifest.csv")) {
    & ".venv\Scripts\python.exe" data_pipeline.py report
}

Push-Location mobile-app
npm install --cache "$env:npm_config_cache"
Pop-Location
Write-Host "Bootstrap complete. Activate with: . .\scripts\env.ps1; . .\.venv\Scripts\Activate.ps1"
