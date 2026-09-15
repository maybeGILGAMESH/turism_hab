<#
.SYNOPSIS
    Read-only verification of a frozen project folder against its SHA-256 manifest.

.DESCRIPTION
    Recomputes SHA-256 for every file under -BackupRoot and compares the result with
    the sorted manifest (relative_path,size,sha256). Nothing inside the backup is
    written: files are opened with FileAccess.Read and reports go to -ReportPath only
    when it is given explicitly (it must be outside the backup folder).

    Exit codes: 0 - identical; 1 - missing/changed/extra files; 2 - manifest itself
    does not match its recorded aggregate fingerprint or cannot be read.
#>
[CmdletBinding()]
param(
    [string]$BackupRoot = (Join-Path $PSScriptRoot "turism_hab_v2.0.0_2026-09-14"),
    [string]$ManifestPath = (Join-Path $PSScriptRoot "turism_hab_v2.0.0_2026-09-14.sha256.csv"),
    [string]$ManifestHashPath = (Join-Path $PSScriptRoot "turism_hab_v2.0.0_2026-09-14.manifest.sha256"),
    [string]$SourceArchivePath = (Join-Path $PSScriptRoot "turism_hab_v2.0.0_source.zip"),
    [string]$ReportPath = "",
    [int]$ThrottleLimit = 8,
    [int]$ShowLimit = 25
)

$ErrorActionPreference = "Stop"

function Get-Sha256Hex([string]$Path) {
    $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        $sha = [System.Security.Cryptography.SHA256]::Create()
        try { return ([System.BitConverter]::ToString($sha.ComputeHash($stream))).Replace("-", "").ToLowerInvariant() }
        finally { $sha.Dispose() }
    }
    finally { $stream.Dispose() }
}

function Get-RecordedHash([string]$Path) {
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) { return $null }
    return ((Get-Content -LiteralPath $Path -Raw).Trim() -split "\s+")[0].ToLowerInvariant()
}

$BackupRoot = (Resolve-Path -LiteralPath $BackupRoot).Path.TrimEnd("\")
$ManifestPath = (Resolve-Path -LiteralPath $ManifestPath).Path
if ($ReportPath) {
    $fullReport = [System.IO.Path]::GetFullPath($ReportPath)
    if ($fullReport.StartsWith($BackupRoot + "\", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "ReportPath must be outside the verified folder, otherwise it changes the fingerprint."
    }
}

$started = Get-Date
Write-Host "Backup:   $BackupRoot"
Write-Host "Manifest: $ManifestPath"

# 1. Aggregate fingerprint of the manifest itself.
$manifestHash = Get-Sha256Hex $ManifestPath
$recordedManifestHash = Get-RecordedHash $ManifestHashPath
$manifestOk = $true
if ($recordedManifestHash) {
    $manifestOk = $manifestHash -eq $recordedManifestHash
    Write-Host ("Manifest fingerprint: {0} ({1})" -f $manifestHash, $(if ($manifestOk) { "OK" } else { "MISMATCH, recorded $recordedManifestHash" }))
}
else {
    Write-Host "Manifest fingerprint: $manifestHash (no recorded value to compare)"
}

$archiveStatus = "not checked"
if ($SourceArchivePath -and (Test-Path -LiteralPath $SourceArchivePath)) {
    $recordedArchive = Get-RecordedHash "$SourceArchivePath.sha256"
    if ($recordedArchive) {
        $archiveStatus = if ((Get-Sha256Hex $SourceArchivePath) -eq $recordedArchive) { "OK" } else { "MISMATCH" }
        Write-Host "Source archive: $archiveStatus"
    }
}

# 2. Load expected entries.
$expected = [System.Collections.Generic.Dictionary[string, object]]::new([System.StringComparer]::Ordinal)
foreach ($row in (Import-Csv -LiteralPath $ManifestPath -Encoding UTF8)) {
    $expected[$row.relative_path] = [pscustomobject]@{ Size = [int64]$row.size; Sha256 = $row.sha256.ToLowerInvariant() }
}

# 3. Enumerate actual files without following junctions or symbolic links.
$actual = [System.Collections.Generic.List[object]]::new()
$reparsePoints = [System.Collections.Generic.List[string]]::new()
$stack = [System.Collections.Generic.Stack[System.IO.DirectoryInfo]]::new()
$stack.Push([System.IO.DirectoryInfo]::new($BackupRoot))
$prefixLength = $BackupRoot.Length + 1
while ($stack.Count -gt 0) {
    $directory = $stack.Pop()
    foreach ($entry in $directory.EnumerateFileSystemInfos()) {
        $relative = $entry.FullName.Substring($prefixLength).Replace("\", "/")
        if ($entry.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
            $reparsePoints.Add($relative)
            continue
        }
        if ($entry -is [System.IO.DirectoryInfo]) { $stack.Push($entry) }
        else { $actual.Add([pscustomobject]@{ Path = $relative; FullName = $entry.FullName; Size = $entry.Length }) }
    }
}

$extra = [System.Collections.Generic.List[string]]::new()
$toHash = [System.Collections.Generic.List[object]]::new()
$sizeChanged = [System.Collections.Generic.List[string]]::new()
$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::Ordinal)
foreach ($file in $actual) {
    [void]$seen.Add($file.Path)
    if (-not $expected.ContainsKey($file.Path)) { $extra.Add($file.Path); continue }
    if ($expected[$file.Path].Size -ne $file.Size) { $sizeChanged.Add($file.Path); continue }
    $toHash.Add($file)
}
$missing = @($expected.Keys | Where-Object { -not $seen.Contains($_) })

# 4. Hash files whose sizes match (parallel on PowerShell 7+).
Write-Host ("Hashing {0} files..." -f $toHash.Count)
$hashFunction = ${function:Get-Sha256Hex}.ToString()
if ($PSVersionTable.PSVersion.Major -ge 7) {
    $hashed = $toHash | ForEach-Object -ThrottleLimit $ThrottleLimit -Parallel {
        ${function:Get-Sha256Hex} = $using:hashFunction
        try { [pscustomobject]@{ Path = $_.Path; Sha256 = Get-Sha256Hex $_.FullName; Error = "" } }
        catch { [pscustomobject]@{ Path = $_.Path; Sha256 = ""; Error = $_.Exception.Message } }
    }
}
else {
    $hashed = foreach ($file in $toHash) {
        try { [pscustomobject]@{ Path = $file.Path; Sha256 = Get-Sha256Hex $file.FullName; Error = "" } }
        catch { [pscustomobject]@{ Path = $file.Path; Sha256 = ""; Error = $_.Exception.Message } }
    }
}

$changed = [System.Collections.Generic.List[string]]::new()
foreach ($path in $sizeChanged) { $changed.Add($path) }
$unreadable = [System.Collections.Generic.List[string]]::new()
foreach ($item in $hashed) {
    if ($item.Error) { $unreadable.Add("$($item.Path): $($item.Error)"); continue }
    if ($item.Sha256 -ne $expected[$item.Path].Sha256) { $changed.Add($item.Path) }
}

$result = [ordered]@{
    verified_at        = (Get-Date).ToString("o")
    backup_root        = $BackupRoot
    manifest_sha256    = $manifestHash
    manifest_ok        = $manifestOk
    source_archive     = $archiveStatus
    expected_files     = $expected.Count
    actual_files       = $actual.Count
    missing            = @($missing | Sort-Object)
    changed            = @($changed | Sort-Object)
    extra              = @($extra | Sort-Object)
    unreadable         = @($unreadable)
    skipped_reparse    = @($reparsePoints)
    duration_seconds   = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)
}

function Show-List([string]$Title, $Items) {
    Write-Host ("{0}: {1}" -f $Title, @($Items).Count)
    @($Items) | Select-Object -First $ShowLimit | ForEach-Object { Write-Host "  $_" }
    if (@($Items).Count -gt $ShowLimit) { Write-Host "  ..." }
}

Write-Host ""
Write-Host ("Expected files: {0}; found: {1}" -f $result.expected_files, $result.actual_files)
Show-List "Missing" $result.missing
Show-List "Changed" $result.changed
Show-List "Extra" $result.extra
if ($unreadable.Count) { Show-List "Unreadable" $result.unreadable }
if ($reparsePoints.Count) { Show-List "Skipped junctions/symlinks" $result.skipped_reparse }
Write-Host ("Duration: {0}s" -f $result.duration_seconds)

if ($ReportPath) {
    $result | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $ReportPath -Encoding UTF8
    Write-Host "Report: $ReportPath"
}

if (-not $manifestOk) { Write-Host "RESULT: MANIFEST TAMPERED"; exit 2 }
if ($missing.Count -or $changed.Count -or $extra.Count -or $unreadable.Count -or $archiveStatus -eq "MISMATCH") {
    Write-Host "RESULT: DIFFERENCES FOUND"
    exit 1
}
Write-Host "RESULT: BACKUP INTACT"
exit 0
