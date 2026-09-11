$ErrorActionPreference = "Stop"
. "$PSScriptRoot\env.ps1"
$target = Join-Path $env:HF_HOME "ViT-B-16.pt"
$url = "https://openaipublic.azureedge.net/clip/models/5806e77cd80f8b59890b7e101eabd078d9fb84e6937f9e85e4ecb61988df416f/ViT-B-16.pt"
$expected = "5806e77cd80f8b59890b7e101eabd078d9fb84e6937f9e85e4ecb61988df416f"
New-Item -ItemType Directory -Path $env:HF_HOME -Force | Out-Null
if (-not (Test-Path -LiteralPath $target) -or (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
    & curl.exe -L --fail --retry 5 --retry-all-errors -C - -o $target $url
}
$actual = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "CLIP checkpoint checksum mismatch: $actual" }
Write-Host "CLIP checkpoint ready: $target"
