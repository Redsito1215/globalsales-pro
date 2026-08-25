@echo off
cd /d "%~dp0.."
python scripts\bootstrap_demo.py %*
exit /b %ERRORLEVEL%
