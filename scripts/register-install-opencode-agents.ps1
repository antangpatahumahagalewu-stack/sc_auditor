<#
Register a Scheduled Task that runs the repository's install-opencode-agents.ps1 at user logon.

This script is idempotent: it will recreate the task if it already exists, and will
run the installer once immediately after creation.

No elevated privileges should be required — the task is created for the current user.
#>

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $projectRoot = Resolve-Path (Join-Path $scriptDir "..")
    $installScript = Join-Path $projectRoot "scripts\install-opencode-agents.ps1"

    if (-not (Test-Path -LiteralPath $installScript)) {
        Write-Error ("Install script not found at: " + $installScript)
        exit 2
    }

    $taskName = "OpenCode Install Agents"

    # Build the action to run the installer via powershell.exe
    $quotedInstall = '"' + $installScript + '"'
    $action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File $quotedInstall"

    # If a task with the same name exists, delete it so we recreate cleanly
    $exists = $false
    try {
        schtasks.exe /Query /TN $taskName 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) { $exists = $true }
    } catch {
        $exists = $false
    }

    if ($exists) {
        Write-Host ("Task '" + $taskName + "' already exists - deleting to recreate.")
        schtasks.exe /Delete /TN $taskName /F | Out-Null
    }

    Write-Host ("Creating scheduled task '" + $taskName + "' to run at user logon.")
    # Build a single quoted argument string so schtasks.exe receives the TR value intact
    $argString = "/Create /SC ONLOGON /TN `"$taskName`" /TR `"$action`" /F"
    $p = Start-Process -FilePath schtasks.exe -ArgumentList $argString -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
    if ($p -and $p.ExitCode -eq 0) {
        Write-Host "Scheduled task created."
        Write-Host "Running installer once now."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript
        Write-Host "Installer run finished."
        exit 0
    }
    else {
        Write-Warning "Failed to create scheduled task (falling back to HKCU Run key)."
        # Fallback: create a Run registry key so the installer runs at user logon
        $runKey = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run'
        $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$installScript`""
        Set-ItemProperty -Path $runKey -Name 'OpenCodeInstallAgents' -Value $cmd -Force
        Write-Host "HKCU Run key set. Running installer once now."
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $installScript
        Write-Host "Installer run finished."
        exit 0
    }
}
catch {
    Write-Error ("Failed to register scheduled task: " + $_.ToString())
    exit 2
}
