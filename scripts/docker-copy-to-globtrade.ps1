# OBSOLETO — No copies el proyecto a C:\globtrade.
# Usa directamente C:\vicuna (ruta ASCII, sin ñ):
#
#   cd C:\vicuna
#   docker compose up -d --build
#
# Si aún tienes contenedores del stack antiguo en C:\globtrade:
#   cd C:\globtrade
#   docker compose down
#
# La carpeta C:\globtrade ya no es necesaria; puedes borrarla cuando Docker esté parado.

Write-Host "Este script ya no copia a C:\globtrade." -ForegroundColor Yellow
Write-Host "Usa solo:  cd C:\vicuna  &&  docker compose up -d --build" -ForegroundColor Green
exit 0
