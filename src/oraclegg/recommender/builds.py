"""Build recommendation engine.

Queries aggregated build data to recommend the best build for a champion
against a specific enemy team composition.
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oraclegg.db.engine import async_session
from oraclegg.db.models import BuildAggregate, Champion, Item

logger = logging.getLogger(__name__)


async def get_item_names(item_ids: list[int]) -> dict[int, str]:
    """Resolve item IDs to names."""
    if not item_ids:
        return {}
    async with async_session() as session:
        result = await session.execute(
            select(Item).where(Item.id.in_(item_ids))
        )
        items = result.scalars().all()
        return {i.id: i.name for i in items}


async def get_champion_info(champion_id: int) -> dict | None:
    async with async_session() as session:
        result = await session.execute(
            select(Champion).where(Champion.id == champion_id)
        )
        champ = result.scalar_one_or_none()
        if champ:
            return {"id": champ.id, "name": champ.name, "key": champ.key}
        return None


async def recommend_build(
    champion_id: int,
    role: str,
    enemy_archetypes: list[str],
) -> dict:
    """Get the best build recommendation for a champion vs enemy comp.

    Fallback chain:
    1. Exact archetype match (first matching archetype)
    2. "balanced" archetype
    3. Highest sample size for this champion+role
    4. Empty recommendation

    Returns dict with build details and metadata.
    """
    async with async_session() as session:
        best_match: BuildAggregate | None = None
        match_type = "none"

        # Try each archetype in priority order
        for archetype in enemy_archetypes:
            result = await session.execute(
                select(BuildAggregate)
                .where(
                    BuildAggregate.champion_id == champion_id,
                    BuildAggregate.role == role,
                    BuildAggregate.enemy_comp_archetype == archetype,
                )
                .order_by(BuildAggregate.sample_size.desc())
                .limit(1)
            )
            match = result.scalar_one_or_none()
            if match:
                best_match = match
                match_type = f"archetype:{archetype}"
                break

        # Fallback: balanced
        if not best_match:
            result = await session.execute(
                select(BuildAggregate)
                .where(
                    BuildAggregate.champion_id == champion_id,
                    BuildAggregate.role == role,
                    BuildAggregate.enemy_comp_archetype == "balanced",
                )
                .order_by(BuildAggregate.sample_size.desc())
                .limit(1)
            )
            best_match = result.scalar_one_or_none()
            if best_match:
                match_type = "fallback:balanced"

        # Fallback: any archetype, highest sample
        if not best_match:
            result = await session.execute(
                select(BuildAggregate)
                .where(
                    BuildAggregate.champion_id == champion_id,
                    BuildAggregate.role == role,
                )
                .order_by(BuildAggregate.sample_size.desc())
                .limit(1)
            )
            best_match = result.scalar_one_or_none()
            if best_match:
                match_type = f"fallback:best_available ({best_match.enemy_comp_archetype})"

        # Fallback: any role
        if not best_match:
            result = await session.execute(
                select(BuildAggregate)
                .where(BuildAggregate.champion_id == champion_id)
                .order_by(BuildAggregate.sample_size.desc())
                .limit(1)
            )
            best_match = result.scalar_one_or_none()
            if best_match:
                match_type = f"fallback:any_role ({best_match.role})"

        if not best_match:
            champ_info = await get_champion_info(champion_id)
            return {
                "champion": champ_info or {"id": champion_id, "name": "Unknown"},
                "role": role,
                "match_type": "none",
                "message": "No build data available. Run the pipeline to collect data.",
            }

        # Resolve item names
        build_ids = json.loads(best_match.item_build_path)
        item_names = await get_item_names(
            build_ids + ([best_match.boots_id] if best_match.boots_id else [])
        )
        champ_info = await get_champion_info(champion_id)

        return {
            "champion": champ_info or {"id": champion_id, "name": "Unknown"},
            "role": role,
            "match_type": match_type,
            "enemy_archetype": best_match.enemy_comp_archetype,
            "win_rate": round(best_match.win_rate * 100, 1),
            "sample_size": best_match.sample_size,
            "build_path": [
                {"id": iid, "name": item_names.get(iid, f"Item {iid}")}
                for iid in build_ids
            ],
            "boots": {
                "id": best_match.boots_id,
                "name": item_names.get(best_match.boots_id, "Unknown"),
            } if best_match.boots_id else None,
            "skill_order": json.loads(best_match.skill_order) if best_match.skill_order else [],
            "skill_max_order": best_match.skill_max_order,
            "summoner_spells": json.loads(best_match.summoner_spells),
            "runes": {
                "primary_tree": best_match.primary_rune_tree,
                "keystone": best_match.primary_keystone,
                "primary": json.loads(best_match.primary_runes),
                "secondary_tree": best_match.secondary_rune_tree,
                "secondary": json.loads(best_match.secondary_runes),
                "shards": json.loads(best_match.stat_shards),
            },
            "patch": best_match.patch,
        }


async def recommend_for_matchup(
    champion_id: int,
    role: str,
    enemy_champion_ids: list[int],
) -> dict:
    """Full recommendation: classify enemy comp, then get build."""
    from oraclegg.scouting.comp import classify_comp_from_ids

    async with async_session() as session:
        archetypes = await classify_comp_from_ids(enemy_champion_ids, session)

    recommendation = await recommend_build(champion_id, role, archetypes)
    recommendation["enemy_archetypes_detected"] = archetypes
    return recommendation
