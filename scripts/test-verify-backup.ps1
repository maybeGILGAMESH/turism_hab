# Self-test for verify-backup.ps1 on a disposable fixture: intact, changed, missing, extra, tampered manifest.
$ErrorActionPreference = "Stop"
$verify = Join-Path $PSScriptRoot "verify-backup.ps1"
$work = Join-Path ([System.IO.Path]::GetTempPath()) ("verify-backup-selftest-" + [guid]::NewGuid().ToString("N"))
$root = Join-Path $work "фикстура backup"
New-Item -ItemType Directory -Path (Join-Path $root "sub dir") -Force | Out-Null
Set-Content -LiteralPath (Join-Path $root "a.txt") -Value "alpha" -NoNewline
Set-Content -LiteralPath (Join-Path $root "sub dir\b,comma.txt") -Value "beta" -NoNewline
Set-Content -LiteralPath (Join-Path $root "sub dir\c.bin") -Value "gamma" -NoNewline

function New-Manifest {
    $rows = Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object {
        [pscustomobject]@{
            relative_path = $_.FullName.Substring($root.Length + 1).Replace("\", "/")
            size          = $_.Length
            sha256        = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        }
    } | Sort-Object relative_path
    $manifest = Join-Path $work "fixture.sha256.csv"
    $rows | Export-Csv -LiteralPath $manifest -NoTypeInformation -Encoding utf8NoBOM -UseQuotes AsNeeded
    "$((Get-FileHash -LiteralPath $manifest -Algorithm SHA256).Hash.ToLowerInvariant())  fixture.sha256.csv" |
        Set-Content -LiteralPath (Join-Path $work "fixture.manifest.sha256")
}

function Invoke-Verify([string]$Name) {
    $report = Join-Path $work "$Name.json"
    & pwsh -NoProfile -File $verify -BackupRoot $root -ManifestPath (Join-Path $work "fixture.sha256.csv") `
        -ManifestHashPath (Join-Path $work "fixture.manifest.sha256") -SourceArchivePath "" -ReportPath $report *> $null
    return [pscustomobject]@{ Code = $LASTEXITCODE; Report = (Get-Content -LiteralPath $report -Raw | ConvertFrom-Json) }
}

$failures = 0
function Assert([bool]$Condition, [string]$Message) {
    if ($Condition) { Write-Host "PASS  $Message" } else { Write-Host "FAIL  $Message"; $script:failures++ }
}

try {
    New-Manifest
    $r = Invoke-Verify "intact"
    Assert ($r.Code -eq 0) "intact fixture returns exit code 0"

    Set-Content -LiteralPath (Join-Path $root "a.txt") -Value "alphA" -NoNewline      # same size, new content
    Remove-Item -LiteralPath (Join-Path $root "sub dir\c.bin")
    Set-Content -LiteralPath (Join-Path $root "sub dir\new.txt") -Value "delta"
    $r = Invoke-Verify "modified"
    Assert ($r.Code -eq 1) "modified fixture returns exit code 1"
    Assert (@($r.Report.changed) -contains "a.txt") "same-size content change is detected"
    Assert (@($r.Report.missing) -contains "sub dir/c.bin") "deleted file is detected"
    Assert (@($r.Report.extra) -contains "sub dir/new.txt") "added file is detected"
    Assert (@($r.Report.changed).Count -eq 1 -and @($r.Report.missing).Count -eq 1 -and @($r.Report.extra).Count -eq 1) "no false positives"

    Add-Content -LiteralPath (Join-Path $work "fixture.sha256.csv") -Value "evil.txt,1,00"
    $r = Invoke-Verify "tampered"
    Assert ($r.Code -eq 2) "tampered manifest returns exit code 2"
}
finally {
    Remove-Item -LiteralPath $work -Recurse -Force
}
if ($failures) { Write-Host "$failures check(s) failed"; exit 1 }
Write-Host "verify-backup self-test passed"
exit 0
