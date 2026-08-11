# Respaldo MongoDB GLOBTRADE (mongodump)
param(
    [string]$Uri = "mongodb://127.0.0.1:27017",
    [string]$Db = "globtrade_dw",
    [string]$OutDir = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
if (-not $OutDir) {
    $ts = Get-Date -Format "yyyyMMdd-HHmmss"
    $OutDir = Join-Path $root "backups\globtrade_dw-$ts"
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Respaldo $Db -> $OutDir"

if (Get-Command mongodump -ErrorAction SilentlyContinue) {
    mongodump --uri="$Uri/$Db" --out="$OutDir"
} elseif (docker ps --format "{{.Names}}" | Select-String -Pattern "globtrade-saas-mongo" -Quiet) {
    docker exec globtrade-saas-mongo mongodump --db=$Db --out="/tmp/backup"
    docker cp "globtrade-saas-mongo:/tmp/backup/$Db" $OutDir
} else {
    Write-Error "Instala mongodump o levanta el contenedor globtrade-saas-mongo."
}

Write-Host "OK: $OutDir"
