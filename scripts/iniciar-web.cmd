@echo off
cd /d C:\proyect6softwa
if not exist .venv\Scripts\python.exe (
  echo Creando entorno virtual...
  python -m venv .venv
  .venv\Scripts\pip install -r requirements.txt
)
set PYTHONPATH=C:\proyect6softwa\backend;C:\proyect6softwa
echo GLOBTRADE S.A. - Tablero Q1
echo MongoDB: localhost:27017 / globtrade_dw
echo Abrir: http://127.0.0.1:5001
.venv\Scripts\python.exe frontend\app.py
pause
