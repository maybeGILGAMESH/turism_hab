$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:RuntimeRoot = Join-Path $script:ProjectRoot ".runtime"
$script:RuntimeAlias = "$(Split-Path -Qualifier $script:ProjectRoot)\turism_hab_runtime"
if (-not (Test-Path $script:RuntimeAlias)) {
    # Android Emulator 37 can fail to boot when its AVD path contains Cyrillic characters.
    New-Item -ItemType Junction -Path $script:RuntimeAlias -Target $script:RuntimeRoot | Out-Null
}
$env:UV_INSTALL_DIR = Join-Path $script:ProjectRoot ".runtime\bin"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $script:ProjectRoot ".runtime\python"
$env:UV_PYTHON_BIN_DIR = Join-Path $script:ProjectRoot ".runtime\python-bin"
$env:UV_CACHE_DIR = Join-Path $script:ProjectRoot ".cache\uv"
$env:PIP_CACHE_DIR = Join-Path $script:ProjectRoot ".cache\pip"
$env:HF_HOME = Join-Path $script:ProjectRoot "artifacts\model_cache"
$env:HF_HUB_DISABLE_XET = "1"
$env:TORCH_HOME = Join-Path $script:ProjectRoot "artifacts\model_cache\torch"
$env:npm_config_cache = Join-Path $script:ProjectRoot ".cache\npm"
$env:JAVA_HOME = Join-Path $script:RuntimeAlias "jdk"
$env:ANDROID_HOME = Join-Path $script:RuntimeAlias "android\sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:ANDROID_USER_HOME = Join-Path $script:RuntimeAlias "android\user"
$env:ANDROID_AVD_HOME = Join-Path $env:ANDROID_USER_HOME "avd"
$env:GRADLE_USER_HOME = Join-Path $script:ProjectRoot ".cache\gradle"
$env:Path = "$(Join-Path $script:ProjectRoot '.runtime\bin');$(Join-Path $script:ProjectRoot '.venv\Scripts');$($env:JAVA_HOME)\bin;$($env:ANDROID_HOME)\platform-tools;$($env:ANDROID_HOME)\emulator;$env:Path"

foreach ($path in @($env:UV_INSTALL_DIR, $env:UV_PYTHON_INSTALL_DIR, $env:UV_PYTHON_BIN_DIR,
    $env:UV_CACHE_DIR, $env:PIP_CACHE_DIR, $env:HF_HOME, $env:TORCH_HOME,
    $env:npm_config_cache, $env:JAVA_HOME, $env:ANDROID_HOME, $env:ANDROID_USER_HOME,
    $env:ANDROID_AVD_HOME, $env:GRADLE_USER_HOME)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}
