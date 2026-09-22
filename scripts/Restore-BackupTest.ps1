# Dedicated first-stage restore for the explicitly selected disposable test project.
# Requires the locally prepared PostgreSQL tools, TOC plan and verified backup.
$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$toolsFolder = Join-Path $workspace 'tmp\restore-tools'
$psql = Join-Path $toolsFolder 'pgsql\bin\psql.exe'
$restore = Join-Path $toolsFolder 'pgsql\bin\pg_restore.exe'
$backupFolder = 'C:\Users\finnj\Downloads\backup-test\hammerknuden-2026-foer-20260920T165647Z-3b103ddd'
$dump = Join-Path $backupFolder 'database.dump'
$plan = Join-Path $toolsFolder 'public-restore.list'
$targetRef = 'ycasinssaffzpsyhgzgf'
$savedEnv = @{}
$envNames = @('PGHOST','PGPORT','PGUSER','PGDATABASE','PGPASSWORD','PGSSLMODE','PGCONNECT_TIMEOUT','PGOPTIONS','PGSERVICE','PGSERVICEFILE')
foreach ($name in $envNames) { $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    foreach ($file in @($psql, $restore, $dump, $plan)) {
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Mangler lokal fil: $file" }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $backupFolder 'manifest.json') -Raw | ConvertFrom-Json
    $dumpEntry = @($manifest.files | Where-Object path -eq 'database.dump')
    if ($dumpEntry.Count -ne 1 -or (Get-FileHash -LiteralPath $dump -Algorithm SHA256).Hash -ne $dumpEntry[0].sha256) {
        throw 'Backupfilens kontrolsum er forkert.'
    }
    Write-Host "Gendanner kun appens otte tabeller til TESTPROJEKT $targetRef."
    Write-Host 'Produktionsdatabasen kontaktes ikke. Storage og Auth gendannes i et senere trin.'
    $env:PGHOST = 'aws-1-eu-west-1.pooler.supabase.com'
    $env:PGPORT = '5432'
    $env:PGUSER = "postgres.$targetRef"
    $env:PGDATABASE = 'postgres'
    $env:PGSSLMODE = 'require'
    $env:PGCONNECT_TIMEOUT = '20'
    $env:PGOPTIONS = '-c statement_timeout=120000'
    $env:PGSERVICE = $null
    $env:PGSERVICEFILE = $null
    $password = Read-Host 'Indtast TESTPROJEKTETS databaseadgangskode (vises ikke)' -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($password)
    try { $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr); $password.Dispose() }
    $existing = & $psql -X -w -A -t -v ON_ERROR_STOP=1 -c "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','f');"
    if ($LASTEXITCODE -ne 0) { throw 'Kunne ikke kontrollere testprojektet. Intet er gendannet.' }
    if (($existing -join '').Trim() -ne '0') { throw 'Testprojektet indeholder allerede tabeller eller views. Stopper uden at overskrive noget.' }
    Write-Host 'Gendanner apptabeller, funktioner, data og adgangspolitikker i en samlet transaktion ...'
    & $restore --dbname=postgres --no-password --no-owner --single-transaction --exit-on-error --use-list=$plan $dump
    if ($LASTEXITCODE -ne 0) { throw 'Gendannelsen fejlede. Transaktionen er rullet tilbage. Gem fejlbeskeden til fejlsogning.' }
    $expected = Get-Content -LiteralPath (Join-Path $toolsFolder 'row-counts.json') -Raw | ConvertFrom-Json
    $results = @()
    foreach ($property in $expected.PSObject.Properties) {
        if ($property.Name -notmatch '^public\.("Events"|bookin_pace|breakfast_notes|high_season|historie_new|hk_dtb|optimizer_plan_receipts|statistik_historik)$') { continue }
        $table = $property.Name
        $actual = "SELECT count(*) FROM $table;" | & $psql -X -w -A -t -v ON_ERROR_STOP=1
        if ($LASTEXITCODE -ne 0) { throw "Gendannet, men kontrol af $table fejlede." }
        $number = [long](($actual -join '').Trim())
        $results += [PSCustomObject]@{Table=$table;Expected=[long]$property.Value;Actual=$number;Match=($number -eq [long]$property.Value)}
    }
    $results | Format-Table -AutoSize
    $report = Join-Path $toolsFolder 'restore-public-result.json'
    [PSCustomObject]@{Target=$targetRef;CheckedAt=(Get-Date -Format o);Tables=$results;Scope='public only; Auth and Storage not restored'} | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $report -Encoding UTF8
    if ($results.Count -ne 8 -or @($results | Where-Object { -not $_.Match }).Count -gt 0) { throw 'Gendannet, men raekketallene stemmer ikke. Se kontrolrapporten.' }
    Write-Host 'OK: Alle otte apptabeller er gendannet med korrekte raekkeantal.' -ForegroundColor Green
    Write-Host 'Dette er forste trin. Auth, Storage og funktionstest mangler stadig.'
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
} finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], 'Process') }
    Read-Host 'Tryk Enter for at lukke' | Out-Null
}
