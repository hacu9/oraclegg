import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from oraclegg.config import settings
from oraclegg.db.engine import init_db

# Configure logging for all oraclegg modules.
# When running as a PyInstaller --windowed app, sys.stderr is None so the
# default StreamHandler would crash. Use a file handler in that case.
if sys.stderr is None:
    _log_dir = os.path.dirname(os.environ.get("DB_PATH", "oraclegg.db"))
    os.makedirs(_log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(os.path.join(_log_dir, "oraclegg.log"))],
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    # Fetch latest DDragon patch version
    try:
        from oraclegg.static_data.manager import get_latest_patch
        patch = await get_latest_patch()
        settings.ddragon_version = patch
        print(f"  DDragon version: {patch}")
    except Exception:
        print(f"  DDragon version: {settings.ddragon_version} (default, fetch failed)")

    # Auto-seed if DB is empty (first run from .exe)
    from sqlalchemy import select, func
    from oraclegg.db.engine import async_session
    from oraclegg.db.models import Champion
    async with async_session() as session:
        champ_count = (await session.execute(
            select(func.count()).select_from(Champion)
        )).scalar()
    if champ_count == 0:
        print("  First run — seeding champion and item data...")
        try:
            from oraclegg.static_data.manager import seed_all
            await seed_all()
            print("  Seed complete.")
        except Exception as e:
            print(f"  Seed failed: {e} (you can retry from Settings)")

    # Start background game monitor + LCU champ select monitor
    from oraclegg.game_loop.monitor import game_monitor_loop, lcu_monitor_loop
    monitor_task = asyncio.create_task(game_monitor_loop())
    lcu_task = asyncio.create_task(lcu_monitor_loop())

    # Auto-run pipeline if API key is set but no builds exist
    from oraclegg.pipeline.runner import auto_pipeline_if_needed
    asyncio.create_task(auto_pipeline_if_needed())

    # Start weekly scheduler
    try:
        from oraclegg.pipeline.scheduler import start_scheduler
        start_scheduler()
    except Exception as e:
        print(f"  Scheduler failed to start: {e} (non-critical)")

    print(f"\n  OracleGG running at http://{settings.host}:{settings.port}")
    print(f"  Game monitor active (polling every {settings.live_client_poll_interval}s)")
    if not settings.api_key_configured:
        print("  WARNING: Riot API key not configured — set it in Settings or .env")
    if not settings.summoner_configured:
        print("  WARNING: Summoner not configured — set it in Settings for post-game tracking")
    print()
    yield

    monitor_task.cancel()
    lcu_task.cancel()
    print("OracleGG shutting down")


app = FastAPI(title="OracleGG", version="0.1.0", lifespan=lifespan)

from pathlib import Path as _Path

_static_dir = _Path(__file__).parent / "ui" / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

from oraclegg.api.routes import router  # noqa: E402

app.include_router(router)
