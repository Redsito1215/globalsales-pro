# Copia dataset y parquet desde vicuna (misma BD, archivos locales en este proyecto)
$src = "C:\vicuna\data"
$dst = "C:\proyect6softwa\data"
if (-not (Test-Path $src)) { Write-Error "No existe $src"; exit 1 }
New-Item -ItemType Directory -Force -Path $dst, "$dst\parquet", "$dst\raw" | Out-Null
Copy-Item "$src\sales.csv" $dst -Force -ErrorAction SilentlyContinue
Copy-Item "$src\parquet\*" "$dst\parquet\" -Force -ErrorAction SilentlyContinue
Write-Host "Listo. Archivos en $dst"
