$script:ProjectRoot = Split-Path -Parent $PSScriptRoot
$script:RuntimeRoot = Join-Path $script:ProjectRoot ".runtime"
# v3 uses its own ASCII alias so it never touches the stable version's runtime.
$script:RuntimeAlias = "$(Split-Path -Qualifier $script:ProjectRoot)\turism_hab_v3_runtime"
if (-not (Test-Path $script:RuntimeAlias)) {
    # Android Emulator 37 can fail to boot when its AVD path contains Cyrillic characters.
    New-Item -ItemType Junction -Path $script:RuntimeAlias -Target $script:RuntimeRoot | Out-Null
}
$env:RUNTIME_ALIAS_DIR = $script:RuntimeAlias
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

# Local Ollama lives entirely on this drive; CPU mode until the NVIDIA driver is upgraded.
$env:OLLAMA_BIN_DIR = Join-Path $script:RuntimeAlias "ollama\bin"
$env:OLLAMA_MODELS = Join-Path $script:RuntimeAlias "ollama\models"
$env:OLLAMA_HOST = "127.0.0.1:11434"
$env:OLLAMA_KEEP_ALIVE = "30m"
if ($env:KHAB_OLLAMA_GPU -ne "1") { $env:CUDA_VISIBLE_DEVICES = "-1" }

$env:Path = "$(Join-Path $script:ProjectRoot '.runtime\bin');$(Join-Path $script:ProjectRoot '.venv\Scripts');$($env:OLLAMA_BIN_DIR);$($env:JAVA_HOME)\bin;$($env:ANDROID_HOME)\platform-tools;$($env:ANDROID_HOME)\emulator;$env:Path"

foreach ($path in @($env:UV_INSTALL_DIR, $env:UV_PYTHON_INSTALL_DIR, $env:UV_PYTHON_BIN_DIR,
    $env:UV_CACHE_DIR, $env:PIP_CACHE_DIR, $env:HF_HOME, $env:TORCH_HOME,
    $env:npm_config_cache, $env:JAVA_HOME, $env:ANDROID_HOME, $env:ANDROID_USER_HOME,
    $env:ANDROID_AVD_HOME, $env:GRADLE_USER_HOME, $env:OLLAMA_BIN_DIR, $env:OLLAMA_MODELS)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
}
