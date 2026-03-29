"""Data pipeline: collects Master+ match data from Riot API.

Fetches high-elo player lists, their recent matches, and stores raw data.
"""

import asyncio
import json
import logging

from sqlalchemy import select

from oraclegg.config import settings
from oraclegg.db.engine import async_session
from oraclegg.db.models import MatchHistoryCache
from oraclegg.riot.client import RiotClient, RiotAPIError

logger = logging.getLogger(__name__)

# Role normalization: Riot uses MIDDLE/BOTTOM/UTILITY, we use MID/ADC/SUPPORT
ROLE_MAP = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MID",
    "BOTTOM": "ADC",
    "UTILITY": "SUPPORT",
    "": "UNKNOWN",
}


async def collect_high_elo_puuids(
    client: RiotClient,
    platform: str | None = None,
    tiers: list[str] | None = None,
    max_players: int | None = None,
) -> list[str]:
    """Fetch Master+ PUUIDs from League-Exp-V4.

    Returns list of PUUIDs (the API now returns puuid directly).
    """
    platform = platform or settings.pipeline_region
    tiers = tiers or ["CHALLENGER", "GRANDMASTER", "MASTER"]
    max_players = max_players or settings.pipeline_player_sample_size

    puuids = []

    for tier in tiers:
        page = 1
        while len(puuids) < max_players:
            try:
                entries = await client.get_league_exp_entries(
                    tier=tier, page=page, platform=platform
                )
                if not entries:
                    break

                for entry in entries:
                    puuid = entry.get("puuid")
                    if puuid:
                        puuids.append(puuid)

                logger.info(f"{tier} page {page}: {len(entries)} entries (total: {len(puuids)})")
                page += 1

                if len(puuids) >= max_players:
                    break
            except RiotAPIError as e:
                logger.warning(f"Error fetching {tier} page {page}: {e}")
                break

    puuids = puuids[:max_players]
    logger.info(f"Collected {len(puuids)} high-elo PUUIDs")
    return puuids


async def collect_match_ids(
    client: RiotClient,
    puuids: list[str],
    matches_per_player: int | None = None,
) -> list[str]:
    """Fetch recent ranked match IDs for each PUUID. Deduplicates."""
    matches_per_player = matches_per_player or settings.pipeline_matches_per_player
    all_match_ids: set[str] = set()
    errors = 0

    for i, puuid in enumerate(puuids):
        try:
            match_ids = await client.get_match_ids(
                puuid, queue=420, count=matches_per_player
            )
            all_match_ids.update(match_ids)
        except RiotAPIError as e:
            errors += 1
            if e.status_code in (401, 403):
                logger.error("API key invalid or expired. Stopping.")
                break
            if e.status_code == 429:
                await asyncio.sleep(15)
            if errors > 30:
                logger.warning(f"Too many errors ({errors}), stopping match ID collection")
                break

        if (i + 1) % 50 == 0:
            logger.info(
                f"Fetched match IDs for {i + 1}/{len(puuids)} players "
                f"({len(all_match_ids)} unique matches)"
            )

    logger.info(f"Collected {len(all_match_ids)} unique match IDs ({errors} errors)")
    return list(all_match_ids)


async def fetch_and_cache_matches(
    client: RiotClient,
    match_ids: list[str],
) -> int:
    """Fetch match details and cache them. Skips already-cached matches."""
    async with async_session() as session:
        # Check which matches are already cached
        existing = set()
        for batch_start in range(0, len(match_ids), 500):
            batch = match_ids[batch_start:batch_start + 500]
            result = await session.execute(
                select(MatchHistoryCache.match_id).where(
                    MatchHistoryCache.match_id.in_(batch)
                )
            )
            existing.update(r[0] for r in result.all())

    to_fetch = [mid for mid in match_ids if mid not in existing]
    logger.info(f"{len(existing)} matches cached, {len(to_fetch)} to fetch")

    fetched = 0
    errors = 0

    for i, match_id in enumerate(to_fetch):
        try:
            match_data = await client.get_match(match_id)
            async with async_session() as session:
                cache_entry = MatchHistoryCache(
                    match_id=match_id,
                    data=match_data.model_dump_json(),
                )
                await session.merge(cache_entry)
                await session.commit()
            fetched += 1
        except RiotAPIError as e:
            errors += 1
            if e.status_code == 429:
                logger.info("Rate limited — waiting 30s before retrying")
                await asyncio.sleep(30)
            elif e.status_code in (401, 403):
                logger.error("API key invalid or expired. Stopping.")
                break
            if errors > 50:
                logger.warning(f"Too many errors ({errors}), stopping collection early")
                break

        if (i + 1) % 25 == 0:
            logger.info(f"Fetched {fetched}/{len(to_fetch)} matches ({errors} errors)")

    logger.info(f"Fetched and cached {fetched} matches ({errors} errors)")
    return fetched


async def run_collection(
    api_key: str | None = None,
    platform: str | None = None,
    max_players: int | None = None,
) -> dict:
    """Run the full collection pipeline. Returns stats."""
    client = RiotClient(api_key=api_key)

    try:
        # Step 1: Get high-elo PUUIDs directly from League-Exp-V4
        logger.info("Step 1/3: Collecting high-elo PUUIDs...")
        puuids = await collect_high_elo_puuids(
            client, platform=platform, max_players=max_players
        )

        # Step 2: Collect match IDs
        logger.info("Step 2/3: Collecting match IDs...")
        match_ids = await collect_match_ids(client, puuids)

        # Step 3: Fetch and cache match details
        logger.info("Step 3/3: Fetching match details...")
        fetched = await fetch_and_cache_matches(client, match_ids)

        stats = {
            "players": len(puuids),
            "puuids": len(puuids),
            "match_ids": len(match_ids),
            "fetched": fetched,
        }
        logger.info(f"Collection complete: {stats}")
        return stats

    finally:
        await client.close()
