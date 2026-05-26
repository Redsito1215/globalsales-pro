# Copia el proyecto a C:\globtrade (ruta ASCII) para evitar fallos de Docker con "vicuña"
$src = "C:\vicuña"
$dst = "C:\globtrade"

if (-not (Test-Path $src)) {
    Write-Error "No existe $src"
    exit 1
}

Write-Host "Copiando $src -> $dst ..."
robocopy $src $dst /E /XD .venv node_modules __pycache__ .git /NFL /NDL /NJH /NJS /nc /ns /np
if ($LASTEXITCODE -ge 8) { exit $LASTEXITCODE }

if (-not (Test-Path "$dst\.env")) {
    Copy-Item "$dst\.env.example" "$dst\.env" -ErrorAction SilentlyContinue
    if (-not (Test-Path "$dst\.env")) {
        @"
POCKETBASE_URL=http://pocketbase:8090
POCKETBASE_ADMIN_EMAIL=admin@globtrade.local
POCKETBASE_ADMIN_PASSWORD=changeme
MONGO_URI=mongodb://mongo:27017
MONGO_DB=globtrade_dw
CSV_SOURCE=/app/data/sales.csv
"@ | Set-Content "$dst\.env" -Encoding UTF8
    }
}

Write-Host ""
Write-Host "Listo. Ejecuta:"
Write-Host "  cd C:\globtrade"
Write-Host "  docker compose up -d --build"
