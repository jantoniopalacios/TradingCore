$ErrorActionPreference = "Stop"

Write-Host "== TradingCore verification =="

Write-Host "`n[1/3] Python syntax"
python -m compileall -q .
if ($LASTEXITCODE -ne 0) {
    throw "compileall failed"
}
Write-Host "COMPILE OK"

Write-Host "`n[2/3] Baseline tests"
python -m pytest `
    Utils/test_db_integration.py `
    Utils/test_indicadores.py `
    Utils/test_signals.py `
    tests/web/test_routes.py `
    -q

if ($LASTEXITCODE -ne 0) {
    throw "baseline tests failed"
}

Write-Host "`n[3/3] Git state"
git status --short

Write-Host "`nVERIFY OK"