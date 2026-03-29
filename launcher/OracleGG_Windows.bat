@echo off
title OracleGG
cd /d "%~dp0.."

REM ============================================================
REM  OracleGG - Native Windows (no WSL needed)
REM ============================================================

REM Check Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install from https://python.org
    pause
    exit /b 1
)

REM Check uv
uv --version > nul 2>&1
if errorlevel 1 (
    echo [..] Installing uv...
    powershell -Command "Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression"
)

REM Install deps if needed
if not exist ".venv" (
    echo [..] Installing dependencies...
    uv sync
)

REM Seed data if needed
if not exist "data\oraclegg.db" (
    echo [..] Downloading champion and item data...
    uv run python scripts/seed_static_data.py
)

REM Start server (no bridge needed on native Windows)
echo.
echo   Starting OracleGG...
echo.
start http://127.0.0.1:8000
uv run uvicorn oraclegg.main:app --host 127.0.0.1 --port 8000
