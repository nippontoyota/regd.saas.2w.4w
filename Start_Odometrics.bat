@echo off
cd /d "%~dp0"
echo Starting Odometrics on http://localhost:8000 ...
start "" http://localhost:8000
python -m uvicorn app.main:app --port 8000
pause
