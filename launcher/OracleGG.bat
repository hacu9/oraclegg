@echo off
title OracleGG
cd /d "%~dp0.."

REM Start the WSL bridge (connects Windows Live Client API to the server)
start /min "OracleGG Bridge" python launcher\bridge.py

REM Wait for bridge
timeout /t 1 /nobreak > nul

REM Start server
start /min "OracleGG Server" uv run uvicorn oraclegg.main:app --host 0.0.0.0 --port 8000

REM Wait for server
timeout /t 4 /nobreak > nul

REM Open browser
start http://127.0.0.1:8000

echo.
echo   OracleGG is running at http://127.0.0.1:8000
echo   Close this window to stop.
echo.

REM Keep alive - when user closes this, cleanup
pause > nul

REM Cleanup
taskkill /fi "WINDOWTITLE eq OracleGG Bridge" /f > nul 2>&1
taskkill /fi "WINDOWTITLE eq OracleGG Server" /f > nul 2>&1
