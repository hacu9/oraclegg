"""Pipeline scheduler.

Runs data collection + aggregation automatically on a weekly schedule.
Also checks for new patches and re-seeds static data when detected.
"""

import asyncio
import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from oraclegg.config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def weekly_pipeline_job():
    """Run the data collection + aggregation pipeline."""
    logger.info("Starting weekly pipeline run...")
    try:
        from oraclegg.pipeline.collector import run_collection
        from oraclegg.pipeline.aggregator import run_aggregation

        stats = await run_collection(
            max_players=settings.pipeline_player_sample_size,
            platform=settings.pipeline_region,
        )
        logger.info(f"Collection: {stats}")

        agg = await run_aggregation(min_sample_size=settings.pipeline_min_sample_size)
        logger.info(f"Aggregation: {agg}")

    except Exception as e:
        logger.error(f"Pipeline job failed: {e}")


async def patch_check_job():
    """Check for new game patches and re-seed static data if needed."""
    logger.info("Checking for patch updates...")
    try:
        from oraclegg.static_data.manager import get_latest_patch, seed_all
        from oraclegg.db.engine import async_session
        from oraclegg.db.models import Champion
        from sqlalchemy import select

        latest = await get_latest_patch()

        async with async_session() as session:
            result = await session.execute(select(Champion).limit(1))
            champ = result.scalar_one_or_none()
            current = champ.patch if champ else None

        if current != latest:
            logger.info(f"New patch detected: {current} -> {latest}. Re-seeding static data...")
            await seed_all()
            logger.info("Static data updated")
        else:
            logger.info(f"Patch {latest} is current")

    except Exception as e:
        logger.error(f"Patch check failed: {e}")


def start_scheduler():
    """Start the background scheduler."""
    # Weekly pipeline: Sunday 3 AM
    scheduler.add_job(
        weekly_pipeline_job,
        CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="weekly_pipeline",
        replace_existing=True,
    )

    # Patch check: daily at 6 AM (patches usually drop Tuesday/Wednesday)
    scheduler.add_job(
        patch_check_job,
        CronTrigger(hour=6, minute=0),
        id="patch_check",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started (pipeline: Sun 3AM, patch check: daily 6AM)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
