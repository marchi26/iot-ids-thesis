param(
    [string]$VenvPath = ".venv"
)

$ErrorActionPreference = "Stop"

function Get-PythonCommand {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        try {
            & py -3.11 --version *> $null
            if ($LASTEXITCODE -eq 0) { return @("py", "-3.11") }
        } catch {}
        try {
            & py -3 --version *> $null
            if ($LASTEXITCODE -eq 0) { return @("py", "-3") }
        } catch {}
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        if ($python.Source -notlike "*WindowsApps*") {
            & python --version *> $null
            if ($LASTEXITCODE -eq 0) { return @("python") }
        }
    }

    $knownPaths = @(
        "$env:LocalAppData\Programs\Python\Python311\python.exe",
        "$env:ProgramFiles\Python311\python.exe"
    )
    foreach ($knownPath in $knownPaths) {
        if (Test-Path $knownPath) {
            & $knownPath --version *> $null
            if ($LASTEXITCODE -eq 0) { return @($knownPath) }
        }
    }

    throw "No usable Python interpreter found. If python.exe resolves to the Microsoft Store alias, disable python.exe and python3.exe App Execution Aliases in Windows Settings, restart PowerShell, then rerun this script."
}

function Invoke-SelectedPython {
    param(
        [string[]]$PythonCommand,
        [string[]]$Arguments
    )
    if ($PythonCommand.Length -gt 1) {
        & $PythonCommand[0] @($PythonCommand[1..($PythonCommand.Length - 1)]) @Arguments
    } else {
        & $PythonCommand[0] @Arguments
    }
}

$pythonCommand = Get-PythonCommand
Write-Host "Using Python command: $($pythonCommand -join ' ')"

if (-not (Test-Path $VenvPath)) {
    Invoke-SelectedPython -PythonCommand $pythonCommand -Arguments @("-m", "venv", $VenvPath)
}

$venvPython = Join-Path $VenvPath "Scripts/python.exe"
if (-not (Test-Path $venvPython)) {
    throw "Virtual environment Python was not found at $venvPython"
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

Write-Host "Environment setup completed."
Write-Host "If you need Kaggle downloads, install the optional CLI with:"
Write-Host "$venvPython -m pip install --no-cache-dir kaggle==1.6.17"
