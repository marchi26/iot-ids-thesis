param(
    [string]$CommitMessage = "Initial thesis IDS project structure"
)

$ErrorActionPreference = "Stop"

$gitValid = $false
try {
    git status *> $null
    $gitValid = ($LASTEXITCODE -eq 0)
} catch {
    $gitValid = $false
}

if ((Test-Path ".git") -and -not $gitValid) {
    $answer = Read-Host ".git exists but is not a valid repository. Delete .git and reinitialize? Type YES to continue"
    if ($answer -ne "YES") {
        Write-Host "Aborted. No files were deleted."
        exit 1
    }
    Remove-Item -Recurse -Force .git
}

if (-not (Test-Path ".git")) {
    git init
    git branch -M main
}

git add .
$staged = git diff --cached --name-only
$blocked = $staged | Where-Object {
    $_ -eq "data/raw/train_test_network.csv" -or
    $_ -like ".venv/*" -or
    $_ -like "venv/*" -or
    $_ -like "*.pkl" -or
    $_ -like "*.joblib" -or
    $_ -like "*kaggle.json" -or
    $_ -like "results/models/*" -or
    $_ -like "results/logs/*"
}

if ($blocked) {
    Write-Host "Blocked files are staged and must not be committed:"
    $blocked | ForEach-Object { Write-Host $_ }
    exit 1
}

git status
git commit -m $CommitMessage

Write-Host "Git repository initialized and committed."
Write-Host "To push later:"
Write-Host "git remote add origin <YOUR_GITHUB_REPOSITORY_URL>"
Write-Host "git push -u origin main"
