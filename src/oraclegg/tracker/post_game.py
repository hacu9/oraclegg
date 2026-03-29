"""Post-game analysis.

After a game ends, fetches match data from Riot API and stores personal stats.
"""

import json
import logging
from datetime import datetime

from sqlalchemy import select

from oraclegg.config import settings
from oraclegg.db.engine import async_session
from oraclegg.db.models import PersonalMatch, Champion
from oraclegg.riot.client import RiotClient, RiotAPIError

logger = logging.getLogger(__name__)


async def analyze_post_game(client: RiotClient) -> dict | None:
    """Fetch the most recent match and store personal stats.

    Returns match analysis dict or None if no new match found.
    """
    try:
        # Get our account
        if not settings.summoner_configured:
            logger.warning("Summoner not configured — skipping post-game analysis")
            return None
        name, tag = settings.summoner_riot_id.split("#")
        account = await client.get_account_by_riot_id(name, tag)
        puuid = account.puuid

        # Get most recent match
        match_ids = await client.get_match_ids(puuid, queue=None, count=1)
        if not match_ids:
            return None

        match_id = match_ids[0]

        # Check if we already analyzed this match
        async with async_session() as session:
            existing = await session.execute(
                select(PersonalMatch).where(PersonalMatch.match_id == match_id)
            )
            if existing.scalar_one_or_none():
                return None

        # Fetch match details
        match = await client.get_match(match_id)
        info = match.info

        # Find our participant
        me = None
        for p in info.participants:
            if p.puuid == puuid:
                me = p
                break

        if not me:
            return None

        # Calculate stats
        game_mins = info.gameDuration / 60
        cs = me.totalMinionsKilled + me.neutralMinionsKilled
        cs_per_min = cs / max(game_mins, 1)

        items_final = [
            getattr(me, f"item{i}") for i in range(7)
            if getattr(me, f"item{i}", 0) > 0
        ]

        my_team_id = me.teamId
        enemy_ids = [
            p.championId for p in info.participants
            if p.puuid != puuid and p.teamId != my_team_id
        ]

        # Get champion name
        async with async_session() as session:
            champ_result = await session.execute(
                select(Champion).where(Champion.id == me.championId)
            )
            champ = champ_result.scalar_one_or_none()
            champ_name = champ.name if champ else me.championName

        role = me.teamPosition or "UNKNOWN"
        role_map = {"MIDDLE": "MID", "BOTTOM": "ADC", "UTILITY": "SUPPORT"}
        role = role_map.get(role, role)

        # Store in DB
        personal = PersonalMatch(
            match_id=match_id,
            champion_id=me.championId,
            role=role,
            win=me.win,
            kills=me.kills,
            deaths=me.deaths,
            assists=me.assists,
            cs=cs,
            cs_per_min=round(cs_per_min, 1),
            vision_score=me.visionScore,
            damage_dealt=me.totalDamageDealtToChampions,
            damage_taken=me.totalDamageTaken,
            gold_earned=me.goldEarned,
            game_duration=info.gameDuration,
            items_final=json.dumps(items_final),
            enemy_champion_ids=json.dumps(enemy_ids),
            played_at=datetime.fromtimestamp(info.gameCreation / 1000),
            patch=info.gameVersion[:8],
        )

        async with async_session() as session:
            await session.merge(personal)
            await session.commit()

        result = "WIN" if me.win else "LOSS"
        kda = f"{me.kills}/{me.deaths}/{me.assists}"
        logger.info(f"Post-game: {champ_name} {kda} {result} ({match_id})")

        return {
            "match_id": match_id,
            "champion": champ_name,
            "champion_id": me.championId,
            "role": role,
            "win": me.win,
            "kda": kda,
            "kills": me.kills,
            "deaths": me.deaths,
            "assists": me.assists,
            "cs": cs,
            "cs_per_min": round(cs_per_min, 1),
            "vision_score": me.visionScore,
            "damage_dealt": me.totalDamageDealtToChampions,
            "gold_earned": me.goldEarned,
            "game_duration": info.gameDuration,
            "game_duration_str": f"{int(game_mins)}:{int(info.gameDuration % 60):02d}",
        }

    except (RiotAPIError, Exception) as e:
        logger.error(f"Post-game analysis failed: {e}")
        return None
