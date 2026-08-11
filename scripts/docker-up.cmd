@echo off
REM GLOBTRADE S.A. - Levantar stack Docker (un solo compose)
echo.
echo Uso:
echo   scripts\docker-up.cmd           = app (mongo+web+api)
echo   scripts\docker-up.cmd airflow   = app + Airflow ETL (:8080)
echo.
cd /d C:\proyect6softwa

if /I "%~1"=="airflow" (
  echo Arrancando app + Airflow...
  docker compose --profile airflow up -d --build
) else (
  echo Arrancando app (sin Airflow). Para ETL: scripts\docker-up.cmd airflow
  docker compose up -d --build
)

if errorlevel 1 (
  echo ERROR en docker compose. Revisa Docker Desktop.
  pause
  exit /b 1
)
echo.
echo Listo:
echo   Tablero  http://127.0.0.1:5001
echo   API      http://127.0.0.1:8001/health
if /I "%~1"=="airflow" echo   Airflow  http://127.0.0.1:8080  (admin/admin)
echo.
docker compose --profile airflow ps 2>nul
if errorlevel 1 docker compose ps
pause
