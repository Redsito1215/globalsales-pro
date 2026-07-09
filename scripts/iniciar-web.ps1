Set-Location C:\proyect6softwa
if (-not (Test-Path .venv\Scripts\python.exe)) {
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
}
$env:PYTHONPATH = "C:\proyect6softwa\backend;C:\proyect6softwa"
Write-Host "GLOBTRADE S.A. - Tablero Q1 -> http://127.0.0.1:5001"
.\.venv\Scripts\python.exe frontend\app.py
