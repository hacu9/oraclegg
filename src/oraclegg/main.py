import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from oraclegg.config import settings
from oraclegg.db.engine import init_db


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

    # Start background game monitor
    from oraclegg.game_loop.monitor import game_monitor_loop
    monitor_task = asyncio.create_task(game_monitor_loop())

    print(f"\n  OracleGG running at http://{settings.host}:{settings.port}")
    print(f"  Game monitor active (polling every {settings.live_client_poll_interval}s)\n")
    yield

    monitor_task.cancel()
    print("OracleGG shutting down")


app = FastAPI(title="OracleGG", version="0.1.0", lifespan=lifespan)

from pathlib import Path as _Path

_static_dir = _Path(__file__).parent / "ui" / "static"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

from oraclegg.api.routes import router  # noqa: E402

app.include_router(router)
