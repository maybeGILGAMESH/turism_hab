$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$device = "auto"
if ($args.Count -gt 0) { $device = $args[0] }
& "$PSScriptRoot\.venv\Scripts\python.exe" build_index.py --device $device
