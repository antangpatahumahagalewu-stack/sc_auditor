# Script untuk rename direktori services dengan prefix angka
# Jalankan di root project: powershell -ExecutionPolicy Bypass -File rename_services.ps1

Set-Location $PSScriptRoot

$renames = @(
    @{ Old = "config";          New = "01-config" }
    @{ Old = "immunefi";        New = "02-immunefi" }
    @{ Old = "source";          New = "03-source" }
    @{ Old = "scanner";         New = "04-scanner" }
    @{ Old = "scanner-mythril"; New = "05-scanner-mythril" }
    @{ Old = "ai";              New = "06-ai" }
    @{ Old = "classifier";      New = "07-classifier" }
    @{ Old = "exploit";         New = "08-exploit" }
    @{ Old = "reporter";        New = "09-reporter" }
    @{ Old = "notifier";        New = "10-notifier" }
    @{ Old = "orchestrator";    New = "11-orchestrator" }
    @{ Old = "webhook";         New = "12-webhook" }
    @{ Old = "upkeep";          New = "13-upkeep" }
    @{ Old = "agent";           New = "14-agent" }
    @{ Old = "dashboard";       New = "15-dashboard" }
)

$servicesDir = Join-Path $PSScriptRoot "services"

foreach ($r in $renames) {
    $oldPath = Join-Path $servicesDir $r.Old
    $newPath = Join-Path $servicesDir $r.New

    if (Test-Path $oldPath) {
        Rename-Item -Path $oldPath -NewName $r.New -Force
        Write-Host "Renamed: $($r.Old) -> $($r.New)" -ForegroundColor Green
    } else {
        Write-Host "Skipped (not found): $($r.Old)" -ForegroundColor Yellow
    }
}

Write-Host "`nDone! Direktori services telah di-rename." -ForegroundColor Cyan
