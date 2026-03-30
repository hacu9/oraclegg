"""Fetch and cache champion/item data from Data Dragon + Meraki Analytics."""

import json
import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oraclegg.db.engine import async_session
from oraclegg.db.models import Champion, Item, Rune

logger = logging.getLogger(__name__)

DDRAGON_VERSIONS_URL = "https://ddragon.leagueoflegends.com/api/versions.json"
DDRAGON_BASE = "https://ddragon.leagueoflegends.com/cdn"
MERAKI_CHAMPIONS_URL = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/champions.json"
MERAKI_ITEMS_URL = "https://cdn.merakianalytics.com/riot/lol/resources/latest/en-US/items.json"


async def get_latest_patch() -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(DDRAGON_VERSIONS_URL)
        resp.raise_for_status()
        versions = resp.json()
        if not versions:
            raise RuntimeError("DDragon returned empty version list")
        return versions[0]


async def fetch_ddragon_champions(patch: str) -> dict:
    url = f"{DDRAGON_BASE}/{patch}/data/en_US/champion.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data:
            raise RuntimeError(f"Unexpected DDragon champion response for patch {patch}")
        return data["data"]


async def fetch_ddragon_items(patch: str) -> dict:
    url = f"{DDRAGON_BASE}/{patch}/data/en_US/item.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        if "data" not in data:
            raise RuntimeError(f"Unexpected DDragon item response for patch {patch}")
        return data["data"]


async def fetch_meraki_champions() -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(MERAKI_CHAMPIONS_URL)
        resp.raise_for_status()
        return resp.json()


async def fetch_meraki_items() -> dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(MERAKI_ITEMS_URL)
        resp.raise_for_status()
        return resp.json()


async def seed_champions(session: AsyncSession, patch: str):
    """Fetch champion data from DDragon + Meraki, store in DB."""
    logger.info("Fetching champion data...")

    dd_champs = await fetch_ddragon_champions(patch)
    try:
        meraki_champs = await fetch_meraki_champions()
    except Exception as e:
        logger.warning(f"Meraki champions fetch failed, using DDragon only: {e}")
        meraki_champs = {}

    count = 0
    for key, dd in dd_champs.items():
        champ_id = int(dd["key"])
        meraki = meraki_champs.get(key, {})

        champ = Champion(
            id=champ_id,
            name=dd["name"],
            key=key,
            tags=json.dumps(dd.get("tags", [])),
            stats=json.dumps(meraki.get("stats", dd.get("stats", {}))),
            abilities=json.dumps(meraki.get("abilities", {})),
            patch=patch,
        )
        await session.merge(champ)
        count += 1

    await session.commit()
    logger.info(f"Seeded {count} champions")


async def seed_items(session: AsyncSession, patch: str):
    """Fetch item data from DDragon + Meraki, store in DB."""
    logger.info("Fetching item data...")

    dd_items = await fetch_ddragon_items(patch)
    try:
        meraki_items = await fetch_meraki_items()
    except Exception as e:
        logger.warning(f"Meraki items fetch failed, using DDragon only: {e}")
        meraki_items = {}

    count = 0
    for item_id_str, dd in dd_items.items():
        item_id = int(item_id_str)
        meraki = meraki_items.get(item_id_str, {})

        item = Item(
            id=item_id,
            name=dd["name"],
            stats=json.dumps(meraki.get("stats", dd.get("stats", {}))),
            tags=json.dumps(dd.get("tags", [])),
            gold_total=dd["gold"]["total"],
            gold_base=dd["gold"]["base"],
            builds_from=json.dumps(dd.get("from", [])),
            builds_into=json.dumps(dd.get("into", [])),
            patch=patch,
        )
        await session.merge(item)
        count += 1

    await session.commit()
    logger.info(f"Seeded {count} items")


async def fetch_ddragon_runes(patch: str) -> list:
    url = f"{DDRAGON_BASE}/{patch}/data/en_US/runesReforged.json"
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def seed_runes(session: AsyncSession, patch: str):
    """Fetch rune data from DDragon and store in DB."""
    logger.info("Fetching rune data...")

    try:
        trees = await fetch_ddragon_runes(patch)
    except Exception as e:
        logger.warning(f"Rune fetch failed: {e}")
        return

    count = 0
    for tree in trees:
        tree_id = tree.get("id", 0)
        tree_name = tree.get("name", "")
        tree_icon = tree.get("icon", "")

        for slot_idx, slot in enumerate(tree.get("slots", [])):
            for rune_data in slot.get("runes", []):
                rune = Rune(
                    id=rune_data["id"],
                    name=rune_data["name"],
                    tree_id=tree_id,
                    tree_name=tree_name,
                    slot=slot_idx,
                    icon=rune_data.get("icon", ""),
                    patch=patch,
                )
                await session.merge(rune)
                count += 1

    await session.commit()
    logger.info(f"Seeded {count} runes")


async def seed_all():
    """Seed all static data."""
    patch = await get_latest_patch()
    logger.info(f"Current patch: {patch}")

    async with async_session() as session:
        await seed_champions(session, patch)
        await seed_items(session, patch)
        await seed_runes(session, patch)

    logger.info("Static data seeding complete")


async def get_champion_name(champion_id: int) -> str | None:
    async with async_session() as session:
        result = await session.execute(select(Champion).where(Champion.id == champion_id))
        champ = result.scalar_one_or_none()
        return champ.name if champ else None


async def get_champion_tags(champion_id: int) -> list[str]:
    async with async_session() as session:
        result = await session.execute(select(Champion).where(Champion.id == champion_id))
        champ = result.scalar_one_or_none()
        return json.loads(champ.tags) if champ else []


async def get_item_name(item_id: int) -> str | None:
    async with async_session() as session:
        result = await session.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        return item.name if item else None
