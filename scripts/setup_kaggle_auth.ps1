$ErrorActionPreference = "Stop"

$localKaggleDir = ".kaggle"
if (-not (Test-Path $localKaggleDir)) {
    New-Item -ItemType Directory -Force $localKaggleDir | Out-Null
}

$accessTokenPath = Join-Path $localKaggleDir "access_token"
$legacyJsonPath = Join-Path $localKaggleDir "kaggle.json"

if (Test-Path $legacyJsonPath) {
    Write-Host "Legacy Kaggle credentials found at .kaggle/kaggle.json."
    Write-Host "KAGGLE_CONFIG_DIR should be set to: $((Resolve-Path $localKaggleDir).Path)"
    exit 0
}

if ($env:KAGGLE_API_TOKEN) {
    Set-Content -Path $accessTokenPath -Value $env:KAGGLE_API_TOKEN -NoNewline
    Write-Host "Kaggle access token saved to .kaggle/access_token."
    Write-Host "The .kaggle directory is ignored by Git."
    exit 0
}

Write-Host "No Kaggle credentials were configured."
Write-Host "Use one of these secure local options:"
Write-Host "1. Place Kaggle legacy API JSON at .kaggle/kaggle.json."
Write-Host "2. Set KAGGLE_API_TOKEN in your current shell, then rerun this script."
Write-Host "Do not commit credentials and do not paste tokens into source files."
exit 1
