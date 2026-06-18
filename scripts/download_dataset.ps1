param(
    [string]$DatasetSlug = "arnobbhowmik/ton-iot-network-dataset"
)

$ErrorActionPreference = "Stop"

$venvPython = ".venv\Scripts\python.exe"
$kaggleExe = ".venv\Scripts\kaggle.exe"

if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run scripts/setup_environment.ps1 first."
}

if (-not (Test-Path $kaggleExe)) {
    & $venvPython -m pip install --no-cache-dir "kaggle==1.6.17"
}

if (-not (Test-Path ".kaggle")) {
    New-Item -ItemType Directory -Force ".kaggle" | Out-Null
}

$env:KAGGLE_CONFIG_DIR = (Resolve-Path ".kaggle").Path

if (-not (Test-Path ".kaggle/kaggle.json")) {
    Write-Host "Kaggle legacy credentials were not found at .kaggle/kaggle.json."
    Write-Host "The installed stable Kaggle CLI uses kaggle.json authentication."
    Write-Host "If you only have a KGAT access token, keep it private and use Kaggle's current client flow manually, or generate/download the legacy kaggle.json if available from your account settings."
    exit 1
}

$downloadDir = "data/raw/kaggle_download"
New-Item -ItemType Directory -Force $downloadDir | Out-Null

& $kaggleExe datasets download -d $DatasetSlug -p $downloadDir --unzip

$candidate = Get-ChildItem $downloadDir -Recurse -File |
    Where-Object { $_.Name -ieq "train_test_network.csv" } |
    Select-Object -First 1

if (-not $candidate) {
    Write-Host "Dataset downloaded, but train_test_network.csv was not found."
    Write-Host "Inspect files under $downloadDir and update config/config.yaml if the dataset schema differs."
    exit 1
}

Copy-Item -LiteralPath $candidate.FullName -Destination "data/raw/train_test_network.csv" -Force
Write-Host "Dataset prepared at data/raw/train_test_network.csv"
