<#
Install OpenCode agents and skills from the repository into the current user's OpenCode config.

Usage:
  powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install-opencode-agents.ps1

This ensures the project-local agents and skills (.opencode/agents and .opencode/skills)
are copied to %USERPROFILE%\.config\opencode so they remain available even if the
global OpenCode installation is updated.
#>

try {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    $projectRoot = Resolve-Path (Join-Path $scriptDir "..")

    $sourceAgents = Join-Path $projectRoot ".opencode\agents"
    $sourceSkills = Join-Path $projectRoot ".opencode\skills"

    $userConfig = Join-Path $env:USERPROFILE ".config\opencode"
    $destAgents = Join-Path $userConfig "agents"
    $destSkills = Join-Path $userConfig "skills"

    if (-not (Test-Path -LiteralPath $userConfig)) {
        New-Item -ItemType Directory -Path $userConfig -Force | Out-Null
        Write-Host "Created user config directory: $userConfig"
    }

    function Copy-IfExists ($src, $dst) {
        if (Test-Path -LiteralPath $src) {
            if (-not (Test-Path -LiteralPath $dst)) {
                New-Item -ItemType Directory -Path $dst -Force | Out-Null
            }
            Write-Host "Copying $src -> $dst"
            Copy-Item -LiteralPath (Join-Path $src "*") -Destination $dst -Recurse -Force -ErrorAction Stop
        }
        else {
            Write-Host "Source not found, skipping: $src"
        }
    }

    Copy-IfExists $sourceAgents $destAgents
    Copy-IfExists $sourceSkills $destSkills

    Write-Host "Install complete. You may need to restart OpenCode/IDE for changes to take effect."
    exit 0
}
catch {
    Write-Error "Failed to install agents: $_"
    exit 2
}
