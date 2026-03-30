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

# Curated skill max order for popular champions (champion_key -> order)
_SKILL_MAX_ORDER = {
    # Top
    "Aatrox": "Q>E>W", "Camille": "Q>E>W", "Darius": "Q>E>W", "Fiora": "Q>E>W",
    "Garen": "E>Q>W", "Gnar": "Q>W>E", "Gwen": "Q>E>W", "Illaoi": "Q>E>W",
    "Irelia": "Q>E>W", "Jax": "W>Q>E", "Jayce": "Q>E>W", "Kayle": "E>Q>W",
    "Kennen": "Q>W>E", "Kled": "Q>W>E", "Malphite": "Q>E>W", "Mordekaiser": "Q>E>W",
    "Nasus": "Q>E>W", "Ornn": "W>Q>E", "Renekton": "Q>E>W", "Riven": "Q>E>W",
    "Sett": "Q>W>E", "Shen": "Q>E>W", "Singed": "Q>E>W", "Teemo": "Q>E>W",
    "Tryndamere": "Q>E>W", "Urgot": "W>Q>E", "Volibear": "Q>W>E", "Yorick": "Q>E>W",
    # Jungle
    "Amumu": "W>Q>E", "Belveth": "Q>E>W", "Briar": "Q>W>E", "Diana": "Q>W>E",
    "Ekko": "Q>E>W", "Elise": "Q>W>E", "Evelynn": "Q>E>W", "Graves": "Q>E>W",
    "Hecarim": "Q>W>E", "JarvanIV": "Q>E>W", "Karthus": "Q>E>W", "Kayn": "Q>W>E",
    "Khazix": "Q>W>E", "Kindred": "Q>W>E", "LeeSin": "Q>W>E", "Lillia": "Q>W>E",
    "MasterYi": "Q>E>W", "Nidalee": "Q>E>W", "Nocturne": "Q>W>E", "Nunu": "Q>E>W",
    "RekSai": "Q>E>W", "Rengar": "Q>W>E", "Sejuani": "W>Q>E", "Shaco": "Q>E>W",
    "Shyvana": "W>E>Q", "Udyr": "Q>R>W", "Viego": "Q>W>E", "Warwick": "Q>W>E",
    "XinZhao": "Q>W>E", "Zac": "E>W>Q",
    # Mid
    "Ahri": "Q>W>E", "Akali": "Q>E>W", "Akshan": "Q>E>W", "Anivia": "Q>E>W",
    "Annie": "Q>W>E", "AurelionSol": "Q>W>E", "Azir": "W>Q>E", "Cassiopeia": "Q>E>W",
    "Fizz": "E>Q>W", "Galio": "Q>W>E", "Kassadin": "Q>E>W", "Katarina": "Q>E>W",
    "Leblanc": "Q>W>E", "Lissandra": "Q>W>E", "Lux": "E>Q>W", "Malzahar": "E>Q>W",
    "Orianna": "Q>W>E", "Qiyana": "Q>E>W", "Ryze": "Q>E>W", "Syndra": "Q>E>W",
    "Talon": "W>Q>E", "TwistedFate": "Q>W>E", "Veigar": "Q>W>E", "Vex": "Q>W>E",
    "Viktor": "Q>E>W", "Vladimir": "Q>E>W", "Xerath": "Q>W>E", "Yasuo": "Q>E>W",
    "Yone": "Q>W>E", "Zed": "Q>E>W", "Ziggs": "Q>E>W", "Zoe": "Q>E>W",
    # ADC
    "Aphelios": "Q>W>E", "Ashe": "W>Q>E", "Caitlyn": "Q>W>E", "Draven": "Q>W>E",
    "Ezreal": "Q>E>W", "Jhin": "Q>W>E", "Jinx": "Q>W>E", "Kaisa": "Q>E>W",
    "KogMaw": "W>Q>E", "Lucian": "Q>E>W", "MissFortune": "Q>W>E", "Samira": "Q>E>W",
    "Sivir": "Q>W>E", "Tristana": "E>Q>W", "Twitch": "E>Q>W", "Vayne": "Q>W>E",
    "Xayah": "Q>E>W", "Zeri": "Q>E>W",
    # Support
    "Bard": "Q>W>E", "Blitzcrank": "Q>W>E", "Brand": "W>Q>E", "Braum": "Q>W>E",
    "Janna": "W>E>Q", "Karma": "Q>E>W", "Leona": "W>E>Q", "Lulu": "E>W>Q",
    "Milio": "W>Q>E", "Morgana": "W>Q>E", "Nami": "W>E>Q", "Nautilus": "E>Q>W",
    "Pyke": "Q>E>W", "Rakan": "W>Q>E", "Rell": "W>E>Q", "Senna": "Q>W>E",
    "Seraphine": "Q>W>E", "Sona": "Q>W>E", "Soraka": "W>Q>E", "Thresh": "E>Q>W",
    "Yuumi": "E>Q>W", "Zyra": "Q>E>W",
}

# Matchup-aware skill max overrides: (champion_key, enemy_archetype) -> order
# When the default skill order changes based on enemy comp
_SKILL_MAX_MATCHUP = {
    # Annie: W max vs heavy tank (more AoE), Q max otherwise
    ("Annie", "heavy_tank"): "W>Q>E",
    ("Annie", "heavy_ad"): "Q>W>E",
    # Riven: E max second vs poke for shield uptime
    ("Riven", "poke"): "Q>E>W",
    # Malphite: E max vs heavy AD (AS slow), Q max vs AP
    ("Malphite", "heavy_ad"): "E>Q>W",
    ("Malphite", "heavy_ap"): "Q>E>W",
    # Viego: W max second vs tanky comps (stun duration), E otherwise
    ("Viego", "heavy_tank"): "Q>W>E",
    # Kayle: Q max vs poke for range harass
    ("Kayle", "poke"): "Q>E>W",
    # Jax: E max second vs heavy AD (dodge uptime)
    ("Jax", "heavy_ad"): "W>E>Q",
    # Warwick: W max vs scaling comps (chase potential)
    ("Warwick", "scaling"): "Q>W>E",
}

def _derive_skill_max(data_list: list[dict]) -> str:
    """Derive skill max order from real timeline data across multiple games.

    Looks at which skill (Q/W/E) reaches level 5 first across all games.
    Returns e.g. "Q>E>W" or empty string if no data.
    """
    from collections import Counter
    max_order_counter = Counter()

    for d in data_list:
        skill_order = d.get("skill_order") or []
        if len(skill_order) < 9:
            continue

        # Count levels per skill at each point
        counts = {"Q": 0, "W": 0, "E": 0}
        first_maxed = []
        for skill in skill_order:
            if skill in counts:
                counts[skill] += 1
                if counts[skill] == 5 and skill not in first_maxed:
                    first_maxed.append(skill)

        if len(first_maxed) >= 2:
            # Fill in the third if missing
            remaining = [s for s in ["Q", "W", "E"] if s not in first_maxed]
            order = first_maxed + remaining
            max_order_counter[">".join(order[:3])] += (2 if d.get("win") else 1)

    if max_order_counter:
        return max_order_counter.most_common(1)[0][0]
    return ""


def _derive_best_skill_order(data_list: list[dict]) -> list[str]:
    """Get the most common first 18 skill level-up sequence from real data."""
    from collections import Counter
    order_counter = Counter()

    for d in data_list:
        skill_order = d.get("skill_order") or []
        if len(skill_order) >= 15:  # Need substantial data
            key = tuple(skill_order[:18])
            order_counter[key] += (2 if d.get("win") else 1)

    if order_counter:
        return list(order_counter.most_common(1)[0][0])
    return []


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

    # Skill order from timeline (if available)
    skill_order = participant.get("skillOrder", [])

    return {
        "champion_id": participant.get("championId"),
        "champion_name": participant.get("championName", ""),
        "role": role,
        "win": participant.get("win", False),
        "enemy_champion_ids": enemy_champs,
        "build_items": build_items,
        "boots_id": boots_id,
        "skill_order": skill_order,
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


async def run_aggregation(min_sample_size: int = 30, current_patch_only: bool = True) -> dict:
    """Process cached matches into build aggregates.

    Groups by (champion, role, enemy_comp_archetype) and aggregates:
    - Most common build path (win-rate weighted)
    - Most common boots
    - Most common runes
    - Most common summoner spells
    - Win rate
    """
    champion_lookup = await load_champion_lookup()

    # Get current patch prefix for filtering
    current_patch_prefix = ""
    if current_patch_only:
        try:
            from oraclegg.static_data.manager import get_latest_patch
            patch = await get_latest_patch()
            # Match on major.minor (e.g. "16.6") not full version
            parts = patch.split(".")
            current_patch_prefix = f"{parts[0]}.{parts[1]}" if len(parts) >= 2 else patch
            logger.info(f"Filtering to current patch: {current_patch_prefix}")
        except Exception:
            current_patch_only = False

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

                    # Filter to current patch only
                    if current_patch_only and current_patch_prefix:
                        game_version = info.get("gameVersion", "")
                        if not game_version.startswith(current_patch_prefix):
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

            # Skill max order — from real data first, then curated, then heuristic
            champ_info = champion_lookup.get(champ_id, {})
            champ_key = champ_info.get("key", "")

            # Try to derive from real timeline data
            skill_max = _derive_skill_max(data_list)
            best_skill_order = _derive_best_skill_order(data_list)

            # Fallback: matchup-aware curated -> general curated -> heuristic
            if not skill_max:
                skill_max = _SKILL_MAX_MATCHUP.get((champ_key, archetype), "")
            if not skill_max:
                skill_max = _SKILL_MAX_ORDER.get(champ_key, "")
            if not skill_max:
                champ_tags = champ_info.get("tags", [])
                if isinstance(champ_tags, str):
                    import json as _j
                    try: champ_tags = _j.loads(champ_tags)
                    except Exception: champ_tags = []
                if role == "SUPPORT":
                    skill_max = "W>Q>E"
                elif "Marksman" in champ_tags:
                    skill_max = "Q>W>E"
                elif "Assassin" in champ_tags:
                    skill_max = "Q>E>W"
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
                skill_order=json.dumps(best_skill_order),
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
