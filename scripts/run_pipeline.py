"""Run the data collection + aggregation pipeline.

Usage:
    uv run python scripts/run_pipeline.py [--players 100] [--platform na1] [--min-sample 10]
"""

import argparse
import asyncio
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from oraclegg.config import settings
from oraclegg.db.engine import init_db
from oraclegg.pipeline.collector import run_collection
from oraclegg.pipeline.aggregator import run_aggregation


def validate_config():
    """Validate configuration before running pipeline."""
    if not settings.api_key_configured:
        print("ERROR: RIOT_API_KEY is not configured.")
        print("  1. Get a free key at https://developer.riotgames.com/")
        print("  2. Edit .env and set RIOT_API_KEY=RGAPI-your-key-here")
        print("  Note: Dev keys expire every 24 hours.")
        sys.exit(1)

    print(f"  API key: ...{settings.riot_api_key[-8:]}")
    print(f"  Region: {settings.riot_region} | Platform: {settings.riot_platform}")


async def main(players: int, platform: str, min_sample: int):
    validate_config()

    try:
        await init_db()
    except Exception as e:
        print(f"ERROR: Failed to initialize database: {e}")
        sys.exit(1)

    # Check if champions are seeded
    from oraclegg.db.engine import async_session
    from oraclegg.db.models import Champion
    from sqlalchemy import select, func
    async with async_session() as session:
        count = (await session.execute(select(func.count()).select_from(Champion))).scalar()
    if count == 0:
        print("\nWARNING: No champion data found. Running seed first...")
        from oraclegg.static_data.manager import seed_all
        await seed_all()

    start = time.time()

    # Step 1: Collect matches
    print(f"\n{'='*60}")
    print(f"  OracleGG Data Pipeline")
    print(f"  Players: {players} | Platform: {platform}")
    print(f"{'='*60}\n")

    collection_stats = await run_collection(
        max_players=players,
        platform=platform,
    )

    if collection_stats["players"] == 0:
        print("\nERROR: No players found. Possible causes:")
        print("  - Invalid or expired API key (dev keys last 24h)")
        print("  - Wrong platform (try --platform na1, euw1, kr, etc.)")
        sys.exit(1)

    # Step 2: Aggregate into build recommendations
    print(f"\n{'='*60}")
    print(f"  Aggregating build data (min sample: {min_sample})")
    print(f"{'='*60}\n")

    agg_stats = await run_aggregation(min_sample_size=min_sample)

    elapsed = time.time() - start

    print(f"\n{'='*60}")
    print(f"  Pipeline Complete ({elapsed:.0f}s)")
    print(f"  Players sampled: {collection_stats['players']}")
    print(f"  Matches collected: {collection_stats['match_ids']}")
    print(f"  Matches fetched: {collection_stats['fetched']}")
    print(f"  Build recommendations: {agg_stats['created']}")
    print(f"  Skipped (low sample): {agg_stats['skipped_low_sample']}")
    print(f"{'='*60}\n")

    if agg_stats['created'] == 0:
        print("  TIP: No builds created? Try lowering --min-sample:")
        print("    uv run python scripts/run_pipeline.py --min-sample 5")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OracleGG data pipeline")
    parser.add_argument("--players", type=int, default=50, help="Number of players to sample")
    parser.add_argument("--platform", type=str, default="na1", help="Platform to collect from")
    parser.add_argument("--min-sample", type=int, default=10, help="Minimum sample size for aggregates")
    args = parser.parse_args()

    asyncio.run(main(args.players, args.platform, args.min_sample))
