$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path "$PSScriptRoot\.."
$browserProject = Join-Path $projectRoot "wokwi\browser_esp32"

Write-Host "Opening Wokwi ESP32 web project page..."
Start-Process "https://wokwi.com/projects/new/esp32"

Write-Host ""
Write-Host "Use these local files in the Wokwi browser editor:"
Write-Host " - $browserProject\sketch.ino"
Write-Host " - $browserProject\embedded_model.h"
Write-Host " - $browserProject\diagram.json"
Write-Host ""
Write-Host "See $browserProject\README.md for exact steps."
