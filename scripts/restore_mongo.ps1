# Restauración protegida de MongoDB. Crea un respaldo previo y exige confirmación exacta.
param([Parameter(Mandatory=$true)][string]$BackupId,[Parameter(Mandatory=$true)][string]$Confirm)
$ErrorActionPreference="Stop"
$projectRoot=Split-Path -Parent $PSScriptRoot
$backupRoot=[IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
$source=[IO.Path]::GetFullPath((Join-Path $backupRoot $BackupId))
if(-not $source.StartsWith($backupRoot,[StringComparison]::OrdinalIgnoreCase)){throw "Respaldo fuera de la carpeta permitida."}
if($Confirm -ne "RESTAURAR-$BackupId"){throw "Confirmación incorrecta. Escribe RESTAURAR-$BackupId"}
$manifestPath=Join-Path $source "manifest.json"
if(-not (Test-Path -LiteralPath $manifestPath)){throw "El respaldo no tiene manifiesto."}
$manifest=Get-Content -Raw -LiteralPath $manifestPath|ConvertFrom-Json
if(-not $manifest.verified){throw "El respaldo no está verificado."}
& (Join-Path $PSScriptRoot "backup_mongo.ps1")
$container="globtrade-saas-mongo"
$tmp="/tmp/altavia-restore-$([Guid]::NewGuid().ToString('N'))"
docker exec $container mkdir -p $tmp
docker cp "$source/." "${container}:$tmp"
foreach($db in $manifest.databases){
  if($db -notmatch '^[A-Za-z0-9_-]+$'){throw "Base inválida en manifiesto."}
  docker exec $container mongorestore --drop --db=$db "$tmp/$db"
}
docker exec $container rm -rf $tmp
Write-Host "Restauración completada desde $BackupId. Se creó un respaldo preventivo."
