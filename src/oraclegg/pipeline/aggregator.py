"""Data pipeline: aggregates collected matches into build recommendations.

Processes cached match data to produce per-champion, per-role, per-archetype
build recommendations weighted by win rate.
"""

import json
import logging
from collections import Counter, defaultdict

from sqlalchemy import select, func

from oraclegg.db.engine import async_session
from oraclegg.db.models import BuildAggregate, Champion, MatchHistoryCache
from oraclegg.pipeline.collector import ROLE_MAP
from oraclegg.scouting.comp import classify_comp

logger = logging.getLogger(__name__)

# Completed item threshold (components are cheaper)
COMPLETED_ITEM_MIN_GOLD = 1800

# Boots item IDs (common boots)
BOOTS_IDS = {
    1001,  # Boots
    3006,  # Berserker's Greaves
    3009,  # Boots of Swiftness
    3020,  # Sorcerer's Shoes
    3047,  # Plated Steelcaps
    3111,  # Mercury's Treads
    3117,  # Mobility Boots
    3158,  # Ionian Boots of Lucidity
}

# Starting items to exclude from build path
STARTING_ITEMS = {
    1055, 1054, 1056, 1082,  # Doran's items
    1036, 1058, 1083,  # Long Sword, Needlessly, Cull
    2003, 2031, 2033,  # Potions
    3340, 3364, 3363,  # Trinkets
    1101, 1102, 1103,  # Jungle items
}


def extract_participant_data(match_data: dict, participant: dict) -> dict | None:
    """Extract relevant data from a single participant in a match."""
    info = match_data.get("info", {})
    team_id = participant.get("teamId")

    # If teamId is missing, infer from participant index (first 5 = team 100, last 5 = team 200)
    if team_id is None:
        all_participants = info.get("participants", [])
        idx = next(
            (i for i, p in enumerate(all_participants) if p.get("puuid") == participant.get("puuid")),
            0,
        )
        team_id = 100 if idx < 5 else 200

    # Get enemy team champion IDs
    enemy_champs = []
    for i, p in enumerate(info.get("participants", [])):
        p_team = p.get("teamId")
        if p_team is None:
            p_team = 100 if i < 5 else 200
        if p_team != team_id:
            enemy_champs.append(p.get("championId", 0))

    if len(enemy_champs) != 5:
        return None

    role = ROLE_MAP.get(participant.get("teamPosition", ""), "UNKNOWN")
    if role == "UNKNOWN":
        return None

    # Extract final items (exclude trinket slot item6, starting items, and cheap components)
    items = []
    for i in range(6):  # item0 through item5
        item_id = participant.get(f"item{i}", 0)
        if item_id and item_id not in STARTING_ITEMS and item_id >= 2000:
            items.append(item_id)

    # Separate boots from build path
    boots_id = None
    build_items = []
    for item_id in items:
        if item_id in BOOTS_IDS:
            boots_id = item_id
        else:
            build_items.append(item_id)

    # Extract starting items
    starting = []
    # We infer from common patterns since timeline isn't always available
    # For now, use the first item in the final build as a proxy

    # Extract runes
    perks = participant.get("perks", {})
    primary_style = perks.get("styles", [{}])[0] if perks.get("styles") else {}
    secondary_style = perks.get("styles", [{}])[1] if len(perks.get("styles", [])) > 1 else {}

    primary_selections = [
        s.get("perk", 0) for s in primary_style.get("selections", [])
    ]
    secondary_selections = [
        s.get("perk", 0) for s in secondary_style.get("selections", [])
    ]

    stat_perks = perks.get("statPerks", {})

    return {
        "champion_id": participant.get("championId"),
        "champion_name": participant.get("championName", ""),
        "role": role,
        "win": participant.get("win", False),
        "enemy_champion_ids": enemy_champs,
        "build_items": build_items,
        "boots_id": boots_id,
        "summoner_spells": [
            participant.get("summoner1Id", 0),
            participant.get("summoner2Id", 0),
        ],
        "primary_rune_tree": primary_style.get("style", 0),
        "primary_keystone": primary_selections[0] if primary_selections else 0,
        "primary_runes": primary_selections,
        "secondary_rune_tree": secondary_style.get("style", 0),
        "secondary_runes": secondary_selections,
        "stat_shards": [
            stat_perks.get("offense", 0),
            stat_perks.get("flex", 0),
            stat_perks.get("defense", 0),
        ],
        "patch": info.get("gameVersion", ""),
    }


async def load_champion_lookup() -> dict[int, dict]:
    """Load champion ID -> {key, tags} mapping."""
    async with async_session() as session:
        result = await session.execute(select(Champion))
        champions = result.scalars().all()
        return {
            c.id: {"key": c.key, "tags": json.loads(c.tags)}
            for c in champions
        }


async def run_aggregation(min_sample_size: int = 30) -> dict:
    """Process cached matches into build aggregates.

    Groups by (champion, role, enemy_comp_archetype) and aggregates:
    - Most common build path (win-rate weighted)
    - Most common boots
    - Most common runes
    - Most common summoner spells
    - Win rate
    """
    champion_lookup = await load_champion_lookup()

    # Key: (champion_id, role, archetype)
    # Value: list of participant data dicts
    groups: dict[tuple, list[dict]] = defaultdict(list)

    # Load all cached matches
    async with async_session() as session:
        count_result = await session.execute(
            select(func.count()).select_from(MatchHistoryCache)
        )
        total_matches = count_result.scalar()
        logger.info(f"Processing {total_matches} cached matches...")

        # Process in batches
        batch_size = 500
        offset = 0
        processed = 0

        while offset < total_matches:
            result = await session.execute(
                select(MatchHistoryCache)
                .offset(offset)
                .limit(batch_size)
            )
            matches = result.scalars().all()

            for cache_entry in matches:
                try:
                    match_data = json.loads(cache_entry.data)
                    info = match_data.get("info", {})

                    # Only ranked solo queue
                    if info.get("queueId") != 420:
                        continue

                    for participant in info.get("participants", []):
                        pdata = extract_participant_data(match_data, participant)
                        if not pdata or not pdata["build_items"]:
                            continue

                        # Classify enemy comp
                        enemy_data = []
                        for eid in pdata["enemy_champion_ids"]:
                            if eid in champion_lookup:
                                enemy_data.append(champion_lookup[eid])
                            else:
                                enemy_data.append({"key": "Unknown", "tags": []})

                        archetypes = classify_comp(enemy_data)

                        # Add to each matching archetype group
                        for archetype in archetypes:
                            key = (pdata["champion_id"], pdata["role"], archetype)
                            groups[key].append(pdata)

                    processed += 1
                except (json.JSONDecodeError, KeyError) as e:
                    logger.debug(f"Error processing match {cache_entry.match_id}: {e}")

            offset += batch_size
            if offset % 1000 == 0:
                logger.info(f"Processed {processed} matches, {len(groups)} groups")

    logger.info(f"Processed {processed} matches into {len(groups)} groups")

    # Aggregate each group
    aggregates_created = 0
    aggregates_skipped = 0
    current_patch = ""

    async with async_session() as session:
        # Clear old aggregates
        await session.execute(BuildAggregate.__table__.delete())

        for (champ_id, role, archetype), data_list in groups.items():
            if len(data_list) < min_sample_size:
                aggregates_skipped += 1
                continue

            wins = sum(1 for d in data_list if d["win"])
            win_rate = wins / len(data_list)

            # Most common build path (weighted by wins)
            build_counter: Counter = Counter()
            for d in data_list:
                # Weight wins more: count 2x for wins
                weight = 2 if d["win"] else 1
                build_key = tuple(d["build_items"][:6])  # Cap at 6 items
                build_counter[build_key] += weight
            best_build = list(build_counter.most_common(1)[0][0]) if build_counter else []

            # Most common boots
            boots_counter: Counter = Counter()
            for d in data_list:
                if d["boots_id"]:
                    weight = 2 if d["win"] else 1
                    boots_counter[d["boots_id"]] += weight
            best_boots = boots_counter.most_common(1)[0][0] if boots_counter else None

            # Most common runes
            rune_counter: Counter = Counter()
            for d in data_list:
                rune_key = (
                    d["primary_rune_tree"],
                    d["primary_keystone"],
                    tuple(d["primary_runes"]),
                    d["secondary_rune_tree"],
                    tuple(d["secondary_runes"]),
                    tuple(d["stat_shards"]),
                )
                weight = 2 if d["win"] else 1
                rune_counter[rune_key] += weight

            if rune_counter:
                best_runes = rune_counter.most_common(1)[0][0]
            else:
                best_runes = (0, 0, (), 0, (), ())

            # Most common summoner spells
            spell_counter: Counter = Counter()
            for d in data_list:
                spell_key = tuple(sorted(d["summoner_spells"]))
                weight = 2 if d["win"] else 1
                spell_counter[spell_key] += weight
            best_spells = list(spell_counter.most_common(1)[0][0]) if spell_counter else [4, 14]

            # Use most recent patch
            if not current_patch and data_list:
                current_patch = data_list[-1].get("patch", "unknown")

            # Infer skill max order from champion data if available
            skill_max = ""
            champ_info = champion_lookup.get(champ_id, {})
            champ_tags = champ_info.get("tags", [])
            # Default skill max orders based on common patterns
            # Most champions max Q first; supports/tanks often max different
            if role == "SUPPORT":
                skill_max = "W>Q>E"  # Most supports
            elif "Marksman" in champ_tags:
                skill_max = "Q>W>E"
            elif "Assassin" in champ_tags:
                skill_max = "Q>E>W"
            elif "Mage" in champ_tags:
                skill_max = "Q>W>E"
            else:
                skill_max = "Q>W>E"

            aggregate = BuildAggregate(
                champion_id=champ_id,
                role=role,
                enemy_comp_archetype=archetype,
                sample_size=len(data_list),
                win_rate=win_rate,
                item_build_path=json.dumps(best_build),
                boots_id=best_boots,
                skill_order=json.dumps([]),
                skill_max_order=skill_max,
                starting_items=json.dumps([]),
                summoner_spells=json.dumps(best_spells),
                primary_rune_tree=str(best_runes[0]),
                primary_keystone=best_runes[1],
                primary_runes=json.dumps(list(best_runes[2])),
                secondary_rune_tree=str(best_runes[3]),
                secondary_runes=json.dumps(list(best_runes[4])),
                stat_shards=json.dumps(list(best_runes[5])),
                patch=current_patch[:8] if current_patch else "unknown",
                region="na1",
            )
            session.add(aggregate)
            aggregates_created += 1

        await session.commit()

    stats = {
        "groups": len(groups),
        "created": aggregates_created,
        "skipped_low_sample": aggregates_skipped,
        "min_sample_size": min_sample_size,
    }
    logger.info(f"Aggregation complete: {stats}")
    return stats
