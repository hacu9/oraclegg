"""Enemy scouting orchestrator.

Scouts all 5 enemies in parallel: resolves accounts, fetches rank, mastery,
match history, and analyzes tendencies.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oraclegg.db.engine import async_session
from oraclegg.db.models import MatchHistoryCache, PlayerCache
from oraclegg.riot.client import RiotClient, RiotAPIError
from oraclegg.scouting.analyzer import analyze_tendencies
from oraclegg.scouting.comp import classify_comp_from_ids

logger = logging.getLogger(__name__)

CACHE_TTL = timedelta(hours=1)


async def scout_player(
    client: RiotClient,
    puuid: str,
    game_name: str | None = None,
    tag_line: str | None = None,
    current_champion_id: int | None = None,
) -> dict:
    """Scout a single player. Returns a scouting report dict."""
    report = {
        "puuid": puuid,
        "game_name": game_name or "Unknown",
        "tag_line": tag_line or "",
        "rank": None,
        "level": None,
        "mastery": [],
        "recent_matches": [],
        "tendencies": {},
        "current_champion_mastery": None,
        "error": None,
    }

    try:
        # Check cache first
        async with async_session() as session:
            cached = await session.execute(
                select(PlayerCache).where(PlayerCache.puuid == puuid)
            )
            player_cache = cached.scalar_one_or_none()
            if player_cache and (datetime.utcnow() - player_cache.last_fetched) < CACHE_TTL:
                cached_data = json.loads(player_cache.data)
                # Update with current champion context
                if current_champion_id:
                    cached_data["tendencies"] = analyze_tendencies(
                        cached_data.get("recent_matches", []),
                        current_champion_id,
                    )
                return cached_data

        # Resolve account if needed
        if not game_name:
            account = await client.get_account_by_puuid(puuid)
            game_name = account.gameName or "Unknown"
            tag_line = account.tagLine or ""
            report["game_name"] = game_name
            report["tag_line"] = tag_line

        # Get summoner data
        try:
            summoner = await client.get_summoner_by_puuid(puuid)
            report["level"] = summoner.summonerLevel

            # Get ranked data
            if summoner.id:
                entries = await client.get_league_entries(summoner.id)
                for entry in entries:
                    if entry.queueType == "RANKED_SOLO_5x5" and entry.tier:
                        report["rank"] = f"{entry.tier} {entry.rank} {entry.leaguePoints}LP"
                        report["rank_wins"] = entry.wins
                        report["rank_losses"] = entry.losses
                        break
        except RiotAPIError:
            pass

        # Get champion mastery
        try:
            mastery = await client.get_champion_mastery(puuid, top=10)
            report["mastery"] = [
                {
                    "champion_id": m.championId,
                    "level": m.championLevel,
                    "points": m.championPoints,
                }
                for m in mastery
            ]
            if current_champion_id:
                for m in mastery:
                    if m.championId == current_champion_id:
                        report["current_champion_mastery"] = {
                            "level": m.championLevel,
                            "points": m.championPoints,
                        }
                        break
        except RiotAPIError:
            pass

        # Get recent match history
        try:
            match_ids = await client.get_match_ids(puuid, queue=420, count=10)
            matches = []
            for mid in match_ids:
                # Check match cache
                async with async_session() as session:
                    cached_match = await session.execute(
                        select(MatchHistoryCache).where(MatchHistoryCache.match_id == mid)
                    )
                    cm = cached_match.scalar_one_or_none()
                    if cm:
                        match_data = json.loads(cm.data)
                    else:
                        try:
                            match_dto = await client.get_match(mid)
                            match_data = match_dto.model_dump()
                            # Cache it
                            async with async_session() as s2:
                                await s2.merge(MatchHistoryCache(
                                    match_id=mid,
                                    data=json.dumps(match_data),
                                ))
                                await s2.commit()
                        except RiotAPIError:
                            continue

                # Extract this player's data
                for p in match_data.get("info", {}).get("participants", []):
                    if p.get("puuid") == puuid:
                        matches.append({
                            "match_id": mid,
                            "champion_id": p.get("championId"),
                            "champion_name": p.get("championName"),
                            "role": p.get("teamPosition", ""),
                            "win": p.get("win", False),
                            "kills": p.get("kills", 0),
                            "deaths": p.get("deaths", 0),
                            "assists": p.get("assists", 0),
                        })
                        break

            report["recent_matches"] = matches
        except RiotAPIError:
            pass

        # Analyze tendencies
        report["tendencies"] = analyze_tendencies(
            report["recent_matches"],
            current_champion_id,
        )

        # Cache the report
        async with async_session() as session:
            await session.merge(PlayerCache(
                puuid=puuid,
                game_name=game_name,
                tag_line=tag_line or "",
                rank_solo=report.get("rank"),
                summoner_level=report.get("level"),
                last_fetched=datetime.utcnow(),
                data=json.dumps(report),
            ))
            await session.commit()

    except Exception as e:
        logger.error(f"Error scouting {game_name}: {e}")
        report["error"] = str(e)

    return report


async def scout_team(
    client: RiotClient,
    enemies: list[dict],
) -> dict:
    """Scout all 5 enemies and classify their team comp.

    Args:
        enemies: list of dicts with 'puuid', 'game_name', 'tag_line', 'champion_id'

    Returns:
        dict with 'players' (list of scouting reports) and 'comp_archetypes'
    """
    # Scout all enemies concurrently (rate limiter handles throttling)
    tasks = [
        scout_player(
            client,
            puuid=e["puuid"],
            game_name=e.get("game_name"),
            tag_line=e.get("tag_line"),
            current_champion_id=e.get("champion_id"),
        )
        for e in enemies
    ]
    reports = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error reports
    player_reports = []
    for i, r in enumerate(reports):
        if isinstance(r, Exception):
            player_reports.append({
                "puuid": enemies[i]["puuid"],
                "game_name": enemies[i].get("game_name", "Unknown"),
                "error": str(r),
            })
        else:
            player_reports.append(r)

    # Classify enemy team composition
    champion_ids = [e.get("champion_id", 0) for e in enemies if e.get("champion_id")]
    comp_archetypes = []
    if len(champion_ids) == 5:
        async with async_session() as session:
            comp_archetypes = await classify_comp_from_ids(champion_ids, session)

    return {
        "players": player_reports,
        "comp_archetypes": comp_archetypes,
    }
