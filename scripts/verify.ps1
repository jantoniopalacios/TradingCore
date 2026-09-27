$ErrorActionPreference = "Stop"

Write-Host "== TradingCore verification =="

Write-Host "`n[1/4] Python syntax"
python -m compileall -q scenarios trading_engine scripts tests
if ($LASTEXITCODE -ne 0) {
    throw "compileall failed"
}
Write-Host "COMPILE OK"

Write-Host "`n[2/4] Baseline tests"
python -m pytest `
    tests/integration/test_db_integration.py `
    tests/unit/test_indicadores.py `
    tests/unit/test_signals.py `
    tests/web/test_routes.py `
    -q
if ($LASTEXITCODE -ne 0) {
    throw "baseline tests failed"
}
Write-Host "TESTS OK"

Write-Host "`n[3/4] Web server state"

$listeners = @(
    Get-NetTCPConnection `
        -LocalPort 5000 `
        -State Listen `
        -ErrorAction SilentlyContinue
)

if ($listeners.Count -eq 0) {
    Write-Host "WEB OFF - no listener on port 5000"
}
else {
    $pids = @(
        $listeners |
            Select-Object -ExpandProperty OwningProcess -Unique
    )

    foreach ($webPid in $pids) {
        $process = Get-CimInstance `
            Win32_Process `
            -Filter "ProcessId = $webPid" `
            -ErrorAction SilentlyContinue

        Write-Host "Listener port 5000:"
        Write-Host "  PID:     $webPid"

        if ($process) {
            Write-Host "  Process: $($process.Name)"
            Write-Host "  Command: $($process.CommandLine)"

            if ($process.CommandLine -match 'scenarios\.BacktestWeb\.app') {
                Write-Host "  State:   TradingCore Web detected"
            }
            else {
                Write-Warning "Port 5000 is occupied by a process that does not look like TradingCore Web."
            }
        }
        else {
            Write-Warning "Unable to obtain process information for PID $webPid."
        }
    }

    if ($pids.Count -gt 1) {
        Write-Warning "More than one listening PID was found for port 5000."
    }
}

Write-Host "`n[4/4] Git state"
git status --short

Write-Host "`nVERIFY OK"
