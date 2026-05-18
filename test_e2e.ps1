# Vyper E2E Pipeline Test
Write-Output "=== Vyper E2E Pipeline Test ==="
Write-Output ""

# Step 1: Start audit
Write-Output "=== Step 1: POST /audit ==="
$body = Get-Content -LiteralPath "E:\website\project\sc_auditor\test_e2e_payload.json" -Raw
$response = Invoke-RestMethod -Uri "http://localhost:8009/audit" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 3
$auditId = $response.data.audit_id
Write-Output "`nAudit ID: $auditId"

# Step 2: Poll for results
$maxPolls = 12  # 2 minutes
$pollInterval = 10
for ($i = 0; $i -lt $maxPolls; $i++) {
    Start-Sleep -Seconds $pollInterval
    try {
        $result = Invoke-RestMethod -Uri "http://localhost:8009/audit/$auditId" -Method Get -ErrorAction Stop
        $state = $result.data.state
        $steps = $result.data.steps
        Write-Output "[$($i+1)/$maxPolls] State: $state | Steps completed: $(@($steps | Where-Object { $_.completed_at -ne $null }).Count)/$(@($steps).Count)"

        if ($state -eq "COMPLETED" -or $state -like "*FAILED*" -or $state -eq "TIMEOUT") {
            Write-Output "`n=== FINAL STATE: $state ==="
            $result | ConvertTo-Json -Depth 4
            break
        }
    } catch {
        Write-Output "Poll error: $_"
    }
}

# Step 3: Check orchestrator logs
Write-Output "`n=== Orchestrator Pipeline Log ==="
docker logs sc_auditor-orchestrator-1 --tail 40 2>&1
