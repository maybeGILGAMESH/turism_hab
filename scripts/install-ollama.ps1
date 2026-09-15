# Installs Ollama for Windows into .runtime\ollama (no system-wide install) and pulls the guide model.
param(
    [string]$Version = "latest",
    [string]$Model = "qwen2.5:1.5b-instruct"
)
$ErrorActionPreference = "Stop"
. "$PSScriptRoot\env.ps1"

$downloads = Join-Path $script:RuntimeRoot "ollama\downloads"
New-Item -ItemType Directory -Path $downloads -Force | Out-Null
$base = if ($Version -eq "latest") { "https://github.com/ollama/ollama/releases/latest/download" } else { "https://github.com/ollama/ollama/releases/download/v$Version" }
$zip = Join-Path $downloads "ollama-windows-amd64.zip"
$sums = Join-Path $downloads "sha256sum.txt"

& curl.exe -L --fail --retry 5 -o $sums "$base/sha256sum.txt"
$expected = ((Get-Content $sums | Where-Object { $_ -match "ollama-windows-amd64\.zip$" }) -split "\s+")[0].ToLowerInvariant()
if (-not $expected) { throw "Checksum for ollama-windows-amd64.zip not found in release" }
if (-not (Test-Path $zip) -or (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    & curl.exe -L --fail --retry 5 --retry-all-errors -C - -o $zip "$base/ollama-windows-amd64.zip"
}
$actual = (Get-FileHash $zip -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "Ollama archive checksum mismatch: $actual" }

Expand-Archive -LiteralPath $zip -DestinationPath $env:OLLAMA_BIN_DIR -Force
& (Join-Path $env:OLLAMA_BIN_DIR "ollama.exe") --version

& "$PSScriptRoot\start-ollama.ps1"
& (Join-Path $env:OLLAMA_BIN_DIR "ollama.exe") pull $Model
& (Join-Path $env:OLLAMA_BIN_DIR "ollama.exe") list
Write-Host "Ollama ready: models in $env:OLLAMA_MODELS"
