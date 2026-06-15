@echo off
echo.
echo  ====================================
echo   PMK RC-Rally - Entwicklungsmodus
echo  ====================================
echo.
echo  Backend:  http://localhost:8000
echo  Frontend: http://localhost:5173
echo  API-Docs: http://localhost:8000/docs
echo.

REM Start backend
start "PMK Rally - Backend" cmd /k "cd backend && pip install -r requirements.txt && uvicorn main:app --reload --port 8000"

REM Wait a moment then start frontend
timeout /t 3 /nobreak >nul
start "PMK Rally - Frontend" cmd /k "cd frontend && npm install && npm run dev"

echo.
echo  Beide Server starten sich gerade...
echo  [Backend]  http://localhost:8000
echo  [Frontend] http://localhost:5173
echo.
pause
