@echo off
title PMK RC-Car Rally
color 0A

echo.
echo  ============================================
echo   PMK RC-Car Rally  -  App wird gestartet
echo  ============================================
echo.

REM npm installieren falls node_modules fehlt
if not exist "frontend\node_modules" (
    echo  [1/4] Frontend-Pakete werden installiert...
    cd frontend
    call npm install
    cd ..
    echo  [1/4] Fertig.
) else (
    echo  [1/4] Frontend-Pakete bereits installiert.
)

echo  [2/4] Backend wird gestartet...
start "RC Rally - Backend" cmd /k "cd /d "%~dp0backend" && python -m pip install -r requirements.txt -q && python -m uvicorn main:app --reload --port 8000"

echo  [3/4] Frontend wird gestartet...
start "RC Rally - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo  [4/4] Cloudflare Tunnel wird gestartet...
start "RC Rally - Tunnel" powershell -NoExit -ExecutionPolicy Bypass -File "%~dp0start-tunnel.ps1"

echo.
echo  Warte 5 Sekunden bis alles hochgefahren ist...
timeout /t 5 /nobreak >nul

echo.
echo  Lokaler Browser wird geoeffnet...
start http://localhost:5173

echo.
echo  ============================================
echo   App laeuft!
echo.
echo   Lokal:    http://localhost:5173
echo   Admin:    http://localhost:5173/admin
echo.
echo   Oeffentliche URL: wird im Tunnel-Fenster
echo   automatisch im Browser geoeffnet!
echo  ============================================
echo.
echo  Alle 3 schwarzen Fenster offen lassen!
echo  Dieses Fenster kannst du schliessen.
echo.
pause
