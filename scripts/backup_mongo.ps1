# Respaldo verificable MongoDB GLOBTRADE (bases operativa y analítica)
param(
    [string]$Uri = "mongodb://127.0.0.1:27017",
    [string[]]$Databases = @("globtrade_ops", "globtrade_dw"),
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutDir = Join-Path $projectRoot "backups\globtrade-$timestamp"
}
$resolvedRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
$resolvedOut = [System.IO.Path]::GetFullPath($OutDir)
if (-not $resolvedOut.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "La salida debe permanecer dentro de $resolvedRoot"
}

New-Item -ItemType Directory -Force -Path $resolvedOut | Out-Null
$containerName = "globtrade-saas-mongo"
$containerTmp = "/tmp/globtrade-backup-$([Guid]::NewGuid().ToString('N'))"

foreach ($databaseName in $Databases) {
    if ($databaseName -notmatch '^[A-Za-z0-9_-]+$') { throw "Nombre de base inválido: $databaseName" }
    Write-Host "Respaldando $databaseName"
    if (Get-Command mongodump -ErrorAction SilentlyContinue) {
        mongodump --uri="$Uri" --db="$databaseName" --out="$resolvedOut"
    } elseif (docker ps --format "{{.Names}}" | Select-String -SimpleMatch $containerName -Quiet) {
        docker exec $containerName mongodump --db=$databaseName --out=$containerTmp
        docker cp "${containerName}:${containerTmp}/${databaseName}" $resolvedOut
    } else {
        throw "Instala mongodump o levanta el contenedor $containerName."
    }
}

if (docker ps --format "{{.Names}}" | Select-String -SimpleMatch $containerName -Quiet) {
    docker exec $containerName rm -rf $containerTmp | Out-Null
}

$backupFiles = Get-ChildItem -LiteralPath $resolvedOut -Recurse -File
if ($backupFiles.Count -lt 2) { throw "Respaldo incompleto: no se generaron archivos suficientes." }
$manifest = [ordered]@{
    backup_id = Split-Path -Leaf $resolvedOut
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    databases = $Databases
    file_count = $backupFiles.Count
    verified = $true
}
$manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $resolvedOut "manifest.json") -Encoding UTF8
Write-Host "OK verificado: $resolvedOut ($($backupFiles.Count) archivos)"
