@echo off
echo Starting ARB_bot dashboard...
echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo API docs: http://localhost:8000/docs
echo.
start "ARB_bot API" cmd /k "cd /d "%~dp0" && python -m uvicorn api.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
start "ARB_bot Web" cmd /k "cd /d "%~dp0web" && npm run dev"
timeout /t 4 /nobreak >nul
start http://localhost:3000
