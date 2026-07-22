$ErrorActionPreference = "Stop"

$venvPython = ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment not found. Run scripts/setup_environment.ps1 first."
}

$dataset = "data/raw/train_test_network.csv"
if (-not (Test-Path $dataset)) {
    Write-Host "Dataset not found: data/raw/train_test_network.csv"
    Write-Host "Please download the TON_IoT / UNSW dataset and place train_test_network.csv inside data/raw/."
    Write-Host "No experiments were executed and no metrics were generated."
    exit 1
}

& $venvPython src/experiments/run_all.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Experiment execution failed with exit code $LASTEXITCODE."
    exit $LASTEXITCODE
}

Write-Host "Generated metrics:"
Get-ChildItem results/metrics -File | Select-Object Name,Length,LastWriteTime
Write-Host "Generated plots:"
Get-ChildItem results/plots -File | Select-Object Name,Length,LastWriteTime
Write-Host "Generated logs:"
Get-ChildItem results/logs -File | Select-Object Name,Length,LastWriteTime
