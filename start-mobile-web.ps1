$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$env:EXPO_PUBLIC_API_BASE_URL = "http://localhost:8100"
Push-Location "$PSScriptRoot\mobile-app"
npx expo start --web --port 8082
Pop-Location
