$ErrorActionPreference = "Stop"
. "$PSScriptRoot\scripts\env.ps1"

$downloadDir = Join-Path $PSScriptRoot ".cache\downloads"
New-Item -ItemType Directory -Path $downloadDir -Force | Out-Null

if (-not (Test-Path "$env:JAVA_HOME\bin\java.exe")) {
    $jdkArchive = Join-Path $downloadDir "temurin-jdk17.zip"
    if (-not (Test-Path $jdkArchive)) {
        & curl.exe -L --fail --retry 5 --retry-delay 3 `
            -o $jdkArchive `
            "https://api.adoptium.net/v3/binary/latest/17/ga/windows/x64/jdk/hotspot/normal/eclipse"
        if ($LASTEXITCODE -ne 0) { throw "JDK download failed." }
    }
    $jdkExtract = Join-Path $downloadDir "jdk-extract"
    if (Test-Path $jdkExtract) { Remove-Item -LiteralPath $jdkExtract -Recurse -Force }
    Expand-Archive $jdkArchive $jdkExtract
    $jdkSource = Get-ChildItem $jdkExtract -Directory | Select-Object -First 1
    if (Test-Path $env:JAVA_HOME) { Remove-Item -LiteralPath $env:JAVA_HOME -Recurse -Force }
    Move-Item -LiteralPath $jdkSource.FullName -Destination $env:JAVA_HOME
    Remove-Item -LiteralPath $jdkExtract -Recurse -Force
}

$sdkManager = Join-Path $env:ANDROID_HOME "cmdline-tools\latest\bin\sdkmanager.bat"
if (-not (Test-Path $sdkManager)) {
    $toolsArchive = Join-Path $downloadDir "android-commandline-tools.zip"
    if (-not (Test-Path $toolsArchive)) {
        & curl.exe -L --fail --retry 5 --retry-delay 3 `
            -o $toolsArchive `
            "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
        if ($LASTEXITCODE -ne 0) { throw "Android command-line tools download failed." }
    }
    $toolsExtract = Join-Path $downloadDir "android-tools-extract"
    if (Test-Path $toolsExtract) { Remove-Item -LiteralPath $toolsExtract -Recurse -Force }
    Expand-Archive $toolsArchive $toolsExtract
    $latest = Join-Path $env:ANDROID_HOME "cmdline-tools\latest"
    New-Item -ItemType Directory -Path (Split-Path $latest) -Force | Out-Null
    if (Test-Path $latest) { Remove-Item -LiteralPath $latest -Recurse -Force }
    Move-Item -LiteralPath (Join-Path $toolsExtract "cmdline-tools") -Destination $latest
    Remove-Item -LiteralPath $toolsExtract -Recurse -Force
}

$env:Path = "$env:JAVA_HOME\bin;$env:Path"
$yes = (1..100 | ForEach-Object { "y" }) -join "`n"
$yes | & $sdkManager --sdk_root=$env:ANDROID_HOME --licenses | Out-Host
& $sdkManager --sdk_root=$env:ANDROID_HOME `
    "platform-tools" "emulator" "platforms;android-35" "build-tools;35.0.0" `
    "system-images;android-35;google_apis;x86_64"

$avdManager = Join-Path $env:ANDROID_HOME "cmdline-tools\latest\bin\avdmanager.bat"
if (-not (& $avdManager list avd | Select-String "Name: Khabarovsk_Pixel_7")) {
    "no" | & $avdManager create avd --force --name "Khabarovsk_Pixel_7" `
        --package "system-images;android-35;google_apis;x86_64" --device "pixel_7"
}
Write-Host "Android SDK and Khabarovsk_Pixel_7 are ready on E:."
