@echo off
REM ============================================================
REM  Build OracleGG.exe — run this ON WINDOWS (not WSL)
REM
REM  Prerequisites: Python 3.11+ installed
REM  Output: dist\OracleGG\OracleGG.exe
REM ============================================================
cd /d "%~dp0.."

echo.
echo  Building OracleGG standalone .exe...
echo.

REM Create a venv for building
if not exist "build_venv" (
    echo  [1/4] Creating build environment...
    python -m venv build_venv
)

REM Install deps into the build venv
echo  [2/4] Installing dependencies...
build_venv\Scripts\pip install -q pyinstaller httpx fastapi uvicorn[standard] aiosqlite sqlalchemy pydantic pydantic-settings apscheduler jinja2 python-multipart pywebview

REM Run PyInstaller
echo  [3/4] Building .exe (this takes 1-2 minutes)...
build_venv\Scripts\pyinstaller --noconfirm --name OracleGG --windowed ^
    --add-data "src\oraclegg\ui;oraclegg\ui" ^
    --hidden-import oraclegg.main ^
    --hidden-import oraclegg.api.routes ^
    --hidden-import oraclegg.game_loop.monitor ^
    --hidden-import oraclegg.recommender.tips ^
    --hidden-import oraclegg.recommender.builds ^
    --hidden-import oraclegg.recommender.rules.item_triggers ^
    --hidden-import oraclegg.recommender.rules.objective_rules ^
    --hidden-import oraclegg.recommender.rules.gold_lead_rules ^
    --hidden-import oraclegg.recommender.rules.power_spike_rules ^
    --hidden-import oraclegg.recommender.rules.boots_rules ^
    --hidden-import oraclegg.recommender.rules.dragon_rules ^
    --hidden-import oraclegg.scouting.scout ^
    --hidden-import oraclegg.scouting.comp ^
    --hidden-import oraclegg.scouting.analyzer ^
    --hidden-import oraclegg.tracker.personal ^
    --hidden-import oraclegg.tracker.post_game ^
    --hidden-import oraclegg.tracker.ai_analysis ^
    --hidden-import oraclegg.riot.client ^
    --hidden-import oraclegg.riot.live_client ^
    --hidden-import oraclegg.riot.lcu ^
    --hidden-import oraclegg.static_data.manager ^
    --hidden-import oraclegg.db.engine ^
    --hidden-import oraclegg.db.models ^
    --hidden-import aiosqlite ^
    --hidden-import webview ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import uvicorn.protocols.http.httptools_impl ^
    --hidden-import uvicorn.lifespan.on ^
    --paths src ^
    launcher\oraclegg_entry.py

REM Copy essentials next to the exe
echo  [4/4] Packaging...
copy .env.example dist\OracleGG\.env.example > nul 2>&1
copy launcher\bridge.py dist\OracleGG\bridge.py > nul 2>&1
mkdir dist\OracleGG\scripts > nul 2>&1
copy scripts\seed_static_data.py dist\OracleGG\scripts\ > nul 2>&1

echo.
echo  ============================================================
echo  BUILD COMPLETE
echo  ============================================================
echo.
echo  Output: dist\OracleGG\OracleGG.exe
echo.
echo  To share with friends:
echo    1. Zip the dist\OracleGG folder
echo    2. Send the zip
echo    3. They extract, rename .env.example to .env, set API key
echo    4. Double-click OracleGG.exe
echo.
pause
