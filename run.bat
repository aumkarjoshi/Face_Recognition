@echo off
cd /d "%~dp0"
venv\Scripts\python face_match.py %*
pause
