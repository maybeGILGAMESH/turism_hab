$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$env:EXPO_PUBLIC_API_BASE_URL = "http://localhost:8000"
Push-Location "$PSScriptRoot\mobile-app"
npm run web
Pop-Location
