@echo off
REM GLOBTRADE S.A. - Levantar web + API en Docker (proyect6softwa)
echo.
echo [1/2] Comprueba que MongoDB este activo (globtrade-mongo en puerto 27017).
echo       Si no: cd C:\vicuna  y  docker compose up -d mongo
echo.
echo [2/2] Construye y arranca la aplicacion nueva...
cd /d C:\proyect6softwa
docker compose up -d --build
if errorlevel 1 (
  echo ERROR en docker compose. Revisa Docker Desktop.
  pause
  exit /b 1
)
echo.
echo Listo:
echo   Tablero  http://127.0.0.1:5001
echo   API      http://127.0.0.1:8001/health
echo.
docker compose ps
pause
