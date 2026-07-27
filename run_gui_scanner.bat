@echo off
cd /d "%~dp0"
venv\Scripts\python gui_scanner.py %*
pause
