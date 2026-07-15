$ErrorActionPreference = "Continue"

function Test-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "Project check"
Write-Host "============="
Write-Host "Location: $(Get-Location)"
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"
Write-Host "Git available: $(Test-Command git)"
if (Test-Command git) {
    git --version
    git status *> $null
    if ($LASTEXITCODE -eq 0) {
        git status
    } else {
        Write-Host "Git repository: invalid or not initialized"
    }
}

$pythonCandidates = @()
if (Test-Command py) { $pythonCandidates += "py -3.11"; $pythonCandidates += "py -3" }
if (Test-Command python) { $pythonCandidates += "python" }
$knownPython = "$env:LocalAppData\Programs\Python\Python311\python.exe"
if (Test-Path $knownPython) { $pythonCandidates += $knownPython }

$usablePython = $null
foreach ($candidate in $pythonCandidates) {
    $parts = $candidate.Split(" ")
    try {
        if ($parts.Length -gt 1) {
            & $parts[0] @($parts[1..($parts.Length - 1)]) --version *> $null
        } else {
            & $parts[0] --version *> $null
        }
        if ($LASTEXITCODE -eq 0) {
            $usablePython = $candidate
            break
        }
    } catch {}
}

Write-Host "Usable Python: $usablePython"
if (Test-Path ".venv\Scripts\python.exe") {
    Write-Host "Virtual environment Python:"
    & ".venv\Scripts\python.exe" --version
    Write-Host "Virtual environment pip:"
    & ".venv\Scripts\python.exe" -m pip --version
}

$ghPath = $null
if (Test-Command gh) {
    $ghPath = "gh"
} elseif (Test-Path "C:\Program Files\GitHub CLI\gh.exe") {
    $ghPath = "C:\Program Files\GitHub CLI\gh.exe"
}
if ($ghPath) {
    Write-Host "GitHub CLI:"
    & $ghPath --version | Select-Object -First 1
    & $ghPath auth status
} else {
    Write-Host "GitHub CLI: not installed or not on PATH"
}

if (Test-Path ".venv\Scripts\kaggle.exe") {
    Write-Host "Kaggle CLI:"
    if (-not (Test-Path ".kaggle")) {
        New-Item -ItemType Directory -Force ".kaggle" | Out-Null
    }
    $env:KAGGLE_CONFIG_DIR = (Resolve-Path ".kaggle").Path
    & ".venv\Scripts\kaggle.exe" --version
    Write-Host "Kaggle credentials present: $(Test-Path .kaggle/kaggle.json)"
} else {
    Write-Host "Kaggle CLI: not installed in .venv"
}

Write-Host "Dataset present: $(Test-Path data/raw/train_test_network.csv)"

$required = @(
    "README.md","requirements.txt",".gitignore","config/config.yaml",
    "data","data/raw","data/raw/.gitkeep","data/processed","data/processed/.gitkeep","data/README.md",
    "src","src/data","src/models","src/experiments","src/visualization","src/simulation","src/utils",
    "results","results/metrics","results/metrics/.gitkeep","results/plots","results/plots/.gitkeep",
    "results/models","results/models/.gitkeep","results/logs","results/logs/.gitkeep",
    "thesis","scripts","docker-compose.yml"
)

$missing = @()
foreach ($path in $required) {
    if (-not (Test-Path $path)) { $missing += $path }
}

if ($missing.Count -gt 0) {
    Write-Host "Missing required paths:"
    $missing | ForEach-Object { Write-Host " - $_" }
} else {
    Write-Host "Required structure: OK"
}

$unexpectedOutputs = Get-ChildItem results/metrics,results/plots -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -ne ".gitkeep" }
if ($unexpectedOutputs) {
    Write-Host "Result outputs present:"
    $unexpectedOutputs | Select-Object FullName,Length,LastWriteTime
} else {
    Write-Host "No generated metrics or plots found."
}

if ($usablePython) {
    $parts = $usablePython.Split(" ")
    if ($parts.Length -gt 1) {
        & $parts[0] @($parts[1..($parts.Length - 1)]) scripts/check_project.py
    } else {
        & $parts[0] scripts/check_project.py
    }
} else {
    Write-Host "Python validation skipped because no usable Python interpreter was found."
}
