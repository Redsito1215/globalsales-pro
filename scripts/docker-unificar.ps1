# Deja un solo stack Docker en C:\vicuna (apaga el de C:\globtrade si existe).
$ErrorActionPreference = "Continue"

Write-Host "=== 1) Apagar stack antiguo en C:\globtrade (si existe) ===" -ForegroundColor Cyan
if (Test-Path "C:\globtrade\docker-compose.yml") {
    Push-Location "C:\globtrade"
    docker compose down 2>$null
    Pop-Location
    Write-Host "Stack C:\globtrade detenido." -ForegroundColor Green
} else {
    Write-Host "No hay docker-compose en C:\globtrade." -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== 2) Levantar stack en C:\vicuna ===" -ForegroundColor Cyan
Push-Location "C:\vicuna"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Creado .env desde .env.example"
}
docker compose up -d --build
Pop-Location

Write-Host ""
Write-Host "Listo. Dashboard: http://localhost:5000" -ForegroundColor Green
Write-Host "MongoDB (Docker): localhost:27017  |  DB: globtrade_dw" -ForegroundColor Green
Write-Host ""
Write-Host "Opcional: borra la carpeta C:\globtrade si ya no la necesitas." -ForegroundColor Yellow
