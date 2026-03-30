"""Background pipeline runner.

Manages pipeline execution as a background task, tracks progress,
and auto-triggers on startup when builds are missing.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, func

from oraclegg.config import settings
from oraclegg.db.engine import async_session
from oraclegg.db.models import BuildAggregate, Champion

logger = logging.getLogger(__name__)

# Pipeline state — accessible from API routes
pipeline_state = {
    "running": False,
    "status": "idle",  # idle, collecting, aggregating, complete, error
    "progress": "",
    "started_at": None,
    "finished_at": None,
    "last_result": None,
    "error": None,
}


async def _run_pipeline(max_players: int = 50, min_sample: int = 5):
    """Execute the full pipeline (collection + aggregation)."""
    from oraclegg.pipeline.collector import run_collection
    from oraclegg.pipeline.aggregator import run_aggregation

    pipeline_state["running"] = True
    pipeline_state["status"] = "collecting"
    pipeline_state["progress"] = "Collecting high-elo match data..."
    pipeline_state["started_at"] = datetime.utcnow().isoformat()
    pipeline_state["error"] = None

    try:
        # Step 1: Collect matches
        logger.info(f"Pipeline: collecting data ({max_players} players)...")
        collection_stats = await run_collection(max_players=max_players)

        pipeline_state["status"] = "aggregating"
        pipeline_state["progress"] = (
            f"Collected {collection_stats['fetched']} matches. "
            f"Generating build recommendations..."
        )

        # Step 2: Aggregate into builds
        logger.info("Pipeline: aggregating builds...")
        agg_stats = await run_aggregation(min_sample_size=min_sample)

        pipeline_state["status"] = "complete"
        pipeline_state["progress"] = (
            f"Done — {agg_stats['created']} builds from "
            f"{collection_stats['fetched']} matches"
        )
        pipeline_state["last_result"] = {
            "players": collection_stats["players"],
            "matches_collected": collection_stats["match_ids"],
            "matches_fetched": collection_stats["fetched"],
            "builds_created": agg_stats["created"],
            "skipped_low_sample": agg_stats["skipped_low_sample"],
        }
        pipeline_state["finished_at"] = datetime.utcnow().isoformat()

        logger.info(
            f"Pipeline complete: {agg_stats['created']} builds "
            f"from {collection_stats['fetched']} matches"
        )

    except Exception as e:
        pipeline_state["status"] = "error"
        pipeline_state["error"] = str(e)
        pipeline_state["progress"] = f"Pipeline failed: {e}"
        logger.error(f"Pipeline error: {e}")

    finally:
        pipeline_state["running"] = False
        pipeline_state["finished_at"] = datetime.utcnow().isoformat()


def trigger_pipeline(max_players: int = 50, min_sample: int = 5) -> bool:
    """Trigger pipeline as a background task. Returns False if already running."""
    if pipeline_state["running"]:
        return False

    task = asyncio.create_task(_run_pipeline(max_players, min_sample))

    def _on_done(t):
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.error(f"Pipeline task failed: {exc}")
            pipeline_state["status"] = "error"
            pipeline_state["error"] = str(exc)
            pipeline_state["running"] = False

    task.add_done_callback(_on_done)
    return True


async def auto_pipeline_if_needed():
    """Check if pipeline should auto-run on startup.

    Runs if:
    - API key is configured
    - Champions are seeded (DB has data)
    - No build aggregates exist yet
    """
    if not settings.api_key_configured:
        logger.info("Pipeline: skipping auto-run (no API key configured)")
        return

    async with async_session() as session:
        champ_count = (await session.execute(
            select(func.count()).select_from(Champion)
        )).scalar()
        build_count = (await session.execute(
            select(func.count()).select_from(BuildAggregate)
        )).scalar()

    if champ_count == 0:
        logger.info("Pipeline: skipping auto-run (no champion data — run seed first)")
        return

    if build_count > 0:
        logger.info(f"Pipeline: {build_count} builds already exist, skipping auto-run")
        return

    logger.info("Pipeline: no builds found, auto-running pipeline...")
    trigger_pipeline(max_players=50, min_sample=5)
