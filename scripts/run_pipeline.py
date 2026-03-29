"""Run the data collection + aggregation pipeline.

Usage:
    uv run python scripts/run_pipeline.py [--players 100] [--platform na1] [--min-sample 10]
"""

import argparse
import asyncio
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

from oraclegg.db.engine import init_db
from oraclegg.pipeline.collector import run_collection
from oraclegg.pipeline.aggregator import run_aggregation


async def main(players: int, platform: str, min_sample: int):
    await init_db()

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run OracleGG data pipeline")
    parser.add_argument("--players", type=int, default=50, help="Number of players to sample")
    parser.add_argument("--platform", type=str, default="na1", help="Platform to collect from")
    parser.add_argument("--min-sample", type=int, default=10, help="Minimum sample size for aggregates")
    args = parser.parse_args()

    asyncio.run(main(args.players, args.platform, args.min_sample))
