$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"
$env:EXPO_PUBLIC_API_BASE_URL = "http://10.0.2.2:8100"
$emulator = Join-Path $env:ANDROID_HOME "emulator\emulator.exe"
if (-not (Test-Path $emulator)) { throw "Android Emulator not installed under $env:ANDROID_HOME. See docs/ANDROID.md" }
$running = & (Join-Path $env:ANDROID_HOME "platform-tools\adb.exe") devices | Select-String "emulator-"
if (-not $running) {
    # The emulator window is intentionally visible: it is the desktop mobile preview.
    Start-Process -FilePath $emulator -ArgumentList `
        "-avd", "Khabarovsk_Pixel_7", "-gpu", "swiftshader_indirect", "-no-metrics"
}
$adb = Join-Path $env:ANDROID_HOME "platform-tools\adb.exe"
& $adb wait-for-device
for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ((& $adb -s emulator-5554 shell getprop sys.boot_completed) -match "1") { break }
    Start-Sleep -Seconds 2
}
$metro = Get-NetTCPConnection -LocalPort 8082 -State Listen -ErrorAction SilentlyContinue
if ($metro) {
    & $adb -s emulator-5554 shell am start -a android.intent.action.VIEW `
        -d "exp://10.0.2.2:8082" host.exp.exponent
    Write-Host "Expo opened in the Android Emulator using the existing Metro server."
    exit 0
}
Push-Location "$PSScriptRoot\mobile-app"
npx expo start --android --port 8082
Pop-Location
