$ErrorActionPreference = 'Stop'
$python = 'C:\Users\finnj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
try {
    if (-not (Test-Path -LiteralPath $python)) { throw 'Python-vaerktoejet mangler.' }
    & $python (Join-Path $PSScriptRoot 'restore_storage_test.py')
} catch {
    Write-Host 'Scriptet kunne ikke startes. Kontakt fejlsogning.' -ForegroundColor Red
} finally {
    Read-Host 'Tryk Enter for at lukke' | Out-Null
}
