"""Personal performance tracking and trends."""

import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import Integer, select, func, desc

from oraclegg.db.engine import async_session
from oraclegg.db.models import PersonalMatch, Champion

logger = logging.getLogger(__name__)


async def get_recent_matches(limit: int = 20) -> list[dict]:
    """Get recent personal match history."""
    async with async_session() as session:
        result = await session.execute(
            select(PersonalMatch)
            .order_by(desc(PersonalMatch.played_at))
            .limit(limit)
        )
        matches = result.scalars().all()

        # Batch-fetch all champion data upfront (avoid N+1)
        champ_ids = {m.champion_id for m in matches}
        champ_result = await session.execute(
            select(Champion).where(Champion.id.in_(champ_ids))
        )
        champ_map = {c.id: c for c in champ_result.scalars().all()}

        output = []
        for m in matches:
            champ = champ_map.get(m.champion_id)
            output.append({
                "match_id": m.match_id,
                "champion": champ.name if champ else f"ID:{m.champion_id}",
                "champion_id": m.champion_id,
                "champion_key": champ.key if champ else "",
                "role": m.role,
                "win": m.win,
                "kills": m.kills,
                "deaths": m.deaths,
                "assists": m.assists,
                "kda": f"{m.kills}/{m.deaths}/{m.assists}",
                "kda_ratio": round((m.kills + m.assists) / max(m.deaths, 1), 1),
                "cs": m.cs,
                "cs_per_min": m.cs_per_min,
                "vision_score": m.vision_score,
                "damage_dealt": m.damage_dealt,
                "gold_earned": m.gold_earned,
                "game_duration": m.game_duration,
                "played_at": m.played_at.isoformat() if m.played_at else "",
            })
        return output


async def get_champion_stats() -> list[dict]:
    """Get per-champion performance stats."""
    async with async_session() as session:
        # Group by champion
        result = await session.execute(
            select(
                PersonalMatch.champion_id,
                func.count().label("games"),
                func.sum(func.cast(PersonalMatch.win, Integer)).label("wins"),
                func.avg(PersonalMatch.kills).label("avg_kills"),
                func.avg(PersonalMatch.deaths).label("avg_deaths"),
                func.avg(PersonalMatch.assists).label("avg_assists"),
                func.avg(PersonalMatch.cs_per_min).label("avg_cs_min"),
                func.avg(PersonalMatch.vision_score).label("avg_vision"),
            )
            .group_by(PersonalMatch.champion_id)
            .having(func.count() >= 1)
            .order_by(func.count().desc())
        )
        rows = result.all()

        # Batch-fetch champion data (avoid N+1)
        champ_ids = {row.champion_id for row in rows}
        champ_result = await session.execute(
            select(Champion).where(Champion.id.in_(champ_ids))
        )
        champ_map = {c.id: c for c in champ_result.scalars().all()}

        output = []
        for row in rows:
            champ = champ_map.get(row.champion_id)
            games = row.games
            wins = row.wins or 0
            output.append({
                "champion": champ.name if champ else f"ID:{row.champion_id}",
                "champion_id": row.champion_id,
                "champion_key": champ.key if champ else "",
                "games": games,
                "wins": wins,
                "losses": games - wins,
                "win_rate": round(wins / games * 100, 1) if games else 0,
                "avg_kda": round(
                    ((row.avg_kills or 0) + (row.avg_assists or 0))
                    / max(row.avg_deaths or 1, 1), 1
                ),
                "avg_cs_min": round(row.avg_cs_min or 0, 1),
                "avg_vision": round(row.avg_vision or 0, 0),
            })
        return output


async def get_overall_stats() -> dict:
    """Get overall performance summary."""
    async with async_session() as session:
        result = await session.execute(
            select(
                func.count().label("total_games"),
                func.sum(func.cast(PersonalMatch.win, Integer)).label("total_wins"),
                func.avg(PersonalMatch.kills).label("avg_kills"),
                func.avg(PersonalMatch.deaths).label("avg_deaths"),
                func.avg(PersonalMatch.assists).label("avg_assists"),
                func.avg(PersonalMatch.cs_per_min).label("avg_cs_min"),
                func.avg(PersonalMatch.vision_score).label("avg_vision"),
            )
        )
        row = result.one()

        total = row.total_games or 0
        wins = row.total_wins or 0

        return {
            "total_games": total,
            "wins": wins,
            "losses": total - wins,
            "win_rate": round(wins / total * 100, 1) if total else 0,
            "avg_kda": round(
                ((row.avg_kills or 0) + (row.avg_assists or 0))
                / max(row.avg_deaths or 1, 1), 1
            ),
            "avg_cs_min": round(row.avg_cs_min or 0, 1),
            "avg_vision": round(row.avg_vision or 0, 0),
        }
