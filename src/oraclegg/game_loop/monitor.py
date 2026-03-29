"""Background game state monitor.

Polls for active games and updates game state for the UI.
On first game detection, fetches build recommendations, classifies enemy comp,
generates lane matchup assessments and strategic advice.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from oraclegg.config import settings
from oraclegg.db.engine import async_session
from oraclegg.db.models import Champion
from oraclegg.recommender.tips import tip_engine
from oraclegg.riot.live_client import LiveClientAPI

logger = logging.getLogger(__name__)

_tip_counter = 0
_game_initialized = False

# Map Live Client position names to standard role names
POSITION_MAP = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MID",
    "BOTTOM": "ADC",
    "UTILITY": "SUPPORT",
}

ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

# Champions whose Live Client name differs from Data Dragon key
CHAMP_ICON_MAP = {
    "Wukong": "MonkeyKing",
    "Renata Glasc": "Renata",
    "Nunu & Willump": "Nunu",
    "Kai'Sa": "Kaisa",
    "Kha'Zix": "Khazix",
    "Bel'Veth": "Belveth",
    "Vel'Koz": "Velkoz",
    "Kog'Maw": "KogMaw",
    "Cho'Gath": "Chogath",
    "Rek'Sai": "RekSai",
    "K'Sante": "KSante",
    "LeBlanc": "Leblanc",
}

# Strategy advice per enemy comp archetype
STRATEGY_TIPS = {
    "scaling": "The enemy team scales very well into late game. You need to gain early advantages and help your allies close the game quickly before they outscale you.",
    "early_game": "The enemy team is strong early. Play safe, survive the laning phase, and you will outscale them in teamfights as the game goes on.",
    "poke": "The enemy team has heavy poke. Engage hard when you find an opening — don't let them whittle you down from range. Build sustain if possible.",
    "engage": "The enemy team has strong engage tools. Maintain distance, save mobility spells, and peel for your carries. Ward flanks to avoid surprise engages.",
    "heavy_ap": "The enemy team is heavy AP. Prioritize magic resist items early — even one MR item can significantly reduce their burst damage.",
    "heavy_ad": "The enemy team is heavy AD. Armor items are very gold-efficient here. Tabis and an early armor component go a long way.",
    "split_push": "The enemy team has strong split push pressure. Group and force 5v4 fights when they split, or match their splitpusher with a duelist.",
    "assassin": "The enemy team has assassins. Group together, protect your carries, and avoid face-checking bushes. Pink wards deny their flanks.",
    "protect_carry": "The enemy team is built around protecting their carry. Look for flanks or dive opportunities to reach their backline.",
    "heavy_tank": "The enemy team is very tanky. Prioritize anti-tank items like % health damage, armor penetration, and sustained DPS over burst.",
    "balanced": "The enemy team is well-balanced. Play to your champion's strengths and look for picks before objectives spawn.",
}

# Simple matchup heuristics based on champion class
_CLASS_ADVANTAGE = {
    ("Assassin", "Mage"): "POSITIVE",
    ("Assassin", "Marksman"): "POSITIVE",
    ("Tank", "Assassin"): "POSITIVE",
    ("Fighter", "Marksman"): "POSITIVE",
    ("Fighter", "Mage"): "POSITIVE",
    ("Mage", "Tank"): "POSITIVE",
    ("Marksman", "Tank"): "POSITIVE",
    ("Support", "Assassin"): "NEGATIVE",
    ("Mage", "Assassin"): "NEGATIVE",
    ("Marksman", "Assassin"): "NEGATIVE",
    ("Marksman", "Fighter"): "NEGATIVE",
    ("Mage", "Fighter"): "NEGATIVE",
    ("Tank", "Mage"): "NEGATIVE",
    ("Tank", "Marksman"): "NEGATIVE",
}

# Shared state accessible from API routes
game_state = {
    "phase": "idle",
    "game_data": None,
    "players": [],
    "events": [],
    "game_time": 0,
    "last_update": None,
    "all_tips": [],
    "tip_version": 0,
    # Enhanced fields (populated on game start)
    "your_champion": None,
    "your_champion_icon": None,
    "your_role": None,
    "enemy_archetypes": [],
    "build_rec": None,
    "strategy": "",
    "lane_matchups": [],
    "runes": None,
    "summoner_spells": [],
    "win_condition": [],
}


async def _resolve_champions(names: list[str]) -> dict[str, dict]:
    """Map champion names to {id, key, tags} from the database."""
    async with async_session() as session:
        result = await session.execute(
            select(Champion).where(Champion.name.in_(names))
        )
        champs = result.scalars().all()
    return {
        c.name: {"id": c.id, "key": c.key, "tags": c.tags}
        for c in champs
    }


def _get_primary_class(tags_json: str) -> str:
    """Extract primary class from champion tags JSON."""
    try:
        import json
        tags = json.loads(tags_json)
        if tags:
            return tags[0]
    except Exception:
        pass
    return "Fighter"


def _rate_matchup(ally_tags: str, enemy_tags: str) -> str:
    """Rate a lane matchup based on champion class interactions."""
    ally_class = _get_primary_class(ally_tags)
    enemy_class = _get_primary_class(enemy_tags)

    rating = _CLASS_ADVANTAGE.get((ally_class, enemy_class))
    if rating:
        return rating

    # Check reverse
    reverse = _CLASS_ADVANTAGE.get((enemy_class, ally_class))
    if reverse == "POSITIVE":
        return "NEGATIVE"
    if reverse == "NEGATIVE":
        return "POSITIVE"

    return "EVEN"


def _pair_lanes(allies: list[dict], enemies: list[dict], champ_data: dict) -> list[dict]:
    """Pair ally and enemy champions by lane position."""
    ally_by_pos = {}
    enemy_by_pos = {}

    for p in allies:
        pos = p.get("position", "")
        if pos:
            ally_by_pos[pos] = p

    for p in enemies:
        pos = p.get("position", "")
        if pos:
            enemy_by_pos[pos] = p

    matchups = []
    for pos in ROLE_ORDER:
        ally = ally_by_pos.get(pos)
        enemy = enemy_by_pos.get(pos)
        if ally and enemy:
            ally_name = ally.get("championName", "")
            enemy_name = enemy.get("championName", "")
            ally_info = champ_data.get(ally_name, {})
            enemy_info = champ_data.get(enemy_name, {})

            rating = _rate_matchup(
                ally_info.get("tags", "[]"),
                enemy_info.get("tags", "[]"),
            )

            matchups.append({
                "role": POSITION_MAP.get(pos, pos),
                "ally_champ": ally_name,
                "ally_icon": CHAMP_ICON_MAP.get(ally_name, ally_name),
                "enemy_champ": enemy_name,
                "enemy_icon": CHAMP_ICON_MAP.get(enemy_name, enemy_name),
                "rating": rating,
            })

    return matchups


def _identify_win_conditions(allies: list[dict], champ_data: dict) -> list[dict]:
    """Identify key carry champions on your team."""
    carries = []
    for p in allies:
        name = p.get("championName", "")
        info = champ_data.get(name, {})
        tags_str = info.get("tags", "[]")
        primary = _get_primary_class(tags_str)
        pos = POSITION_MAP.get(p.get("position", ""), "")

        # Identify carries by role and class
        if pos in ("ADC", "MID") or primary in ("Marksman", "Mage", "Assassin"):
            carries.append({
                "champion": name,
                "icon": CHAMP_ICON_MAP.get(name, name),
                "role": pos or primary,
            })

    return carries[:2]  # Top 2 win conditions


def _parse_runes(runes_data: dict) -> dict | None:
    """Parse rune data from Live Client API activePlayer.fullRunes."""
    if not runes_data:
        return None

    keystone = runes_data.get("keystone", {})
    primary_tree = runes_data.get("primaryRuneTree", {})
    secondary_tree = runes_data.get("secondaryRuneTree", {})
    general = runes_data.get("generalRunes", [])

    return {
        "keystone": {
            "name": keystone.get("displayName", ""),
            "id": keystone.get("id", 0),
        },
        "primary_tree": primary_tree.get("displayName", ""),
        "secondary_tree": secondary_tree.get("displayName", ""),
        "all_runes": [
            {"name": r.get("displayName", ""), "id": r.get("id", 0)}
            for r in general
        ],
    }


def _parse_spells(player_data: dict) -> list[str]:
    """Parse summoner spells from a player's data."""
    spells = player_data.get("summonerSpells", {})
    result = []
    for key in ("summonerSpellOne", "summonerSpellTwo"):
        spell = spells.get(key, {})
        name = spell.get("displayName", "")
        if name:
            result.append(name)
    return result


async def _initialize_game(data: dict):
    """Run once when a game is first detected.

    Fetches build recommendation, classifies enemy comp, generates
    lane matchups, strategy, and win conditions.
    """
    global _game_initialized

    all_players = data.get("allPlayers", [])
    active = data.get("activePlayer", {})
    active_name = active.get("riotIdGameName", active.get("summonerName", ""))

    # Find your player entry
    you = None
    for p in all_players:
        pname = p.get("riotIdGameName", p.get("summonerName", ""))
        if pname == active_name:
            you = p
            break

    if not you:
        logger.warning("Could not identify active player in game data")
        _game_initialized = True
        return

    your_team = you.get("team", "")
    your_champ = you.get("championName", "")
    your_position = POSITION_MAP.get(you.get("position", ""), "MID")

    allies = [p for p in all_players if p.get("team") == your_team]
    enemies = [p for p in all_players if p.get("team") != your_team]

    # Resolve all champion names to IDs/keys/tags
    all_names = [p.get("championName", "") for p in all_players if p.get("championName")]
    champ_data = await _resolve_champions(all_names)

    your_info = champ_data.get(your_champ, {})
    your_champ_id = your_info.get("id")
    your_champ_key = your_info.get("key", CHAMP_ICON_MAP.get(your_champ, your_champ))

    enemy_ids = [
        champ_data[p.get("championName", "")]["id"]
        for p in enemies
        if p.get("championName", "") in champ_data
    ]

    # Classify enemy comp
    archetypes = []
    if enemy_ids:
        try:
            from oraclegg.scouting.comp import classify_comp_from_ids
            async with async_session() as session:
                archetypes = await classify_comp_from_ids(enemy_ids, session)
        except Exception as e:
            logger.error(f"Comp classification error: {e}")

    # Fetch build recommendation
    build_rec = None
    if your_champ_id and enemy_ids:
        try:
            from oraclegg.recommender.builds import recommend_for_matchup
            build_rec = await recommend_for_matchup(your_champ_id, your_position, enemy_ids)
        except Exception as e:
            logger.error(f"Build recommendation error: {e}")

    # Generate strategy from primary archetype
    strategy = ""
    for arch in archetypes:
        if arch in STRATEGY_TIPS and arch != "balanced":
            strategy = STRATEGY_TIPS[arch]
            break
    if not strategy:
        strategy = STRATEGY_TIPS.get("balanced", "")

    # Pair lane matchups
    lane_matchups = _pair_lanes(allies, enemies, champ_data)

    # Identify win conditions
    win_condition = _identify_win_conditions(allies, champ_data)

    # Parse runes from active player
    runes = _parse_runes(active.get("fullRunes", {}))

    # Parse summoner spells
    summoner_spells = _parse_spells(you)

    # Store in game state
    game_state["your_champion"] = your_champ
    game_state["your_champion_icon"] = your_champ_key
    game_state["your_role"] = your_position
    game_state["enemy_archetypes"] = archetypes
    game_state["build_rec"] = build_rec
    game_state["strategy"] = strategy
    game_state["lane_matchups"] = lane_matchups
    game_state["win_condition"] = win_condition
    game_state["runes"] = runes
    game_state["summoner_spells"] = summoner_spells

    _game_initialized = True
    logger.info(
        f"Game initialized: {your_champ} {your_position} vs {archetypes[:3]}"
    )


def _reset_game_state():
    """Reset enhanced game state for next game."""
    global _game_initialized, _tip_counter
    _game_initialized = False
    _tip_counter = 0
    tip_engine._seen_items.clear()
    tip_engine._game_tips_given.clear()
    game_state["all_tips"] = []
    game_state["tip_version"] = 0
    game_state["your_champion"] = None
    game_state["your_champion_icon"] = None
    game_state["your_role"] = None
    game_state["enemy_archetypes"] = []
    game_state["build_rec"] = None
    game_state["strategy"] = ""
    game_state["lane_matchups"] = []
    game_state["win_condition"] = []
    game_state["runes"] = None
    game_state["summoner_spells"] = []
    game_state["post_game_result"] = None


async def game_monitor_loop():
    """Background loop that polls for active games."""
    global _tip_counter
    live_client = LiveClientAPI()
    poll_interval = settings.live_client_poll_interval

    logger.info("Game monitor started")

    while True:
        try:
            data = await live_client.poll()

            if data:
                game_state["phase"] = "in_game"
                game_state["game_data"] = data
                game_state["players"] = data.get("allPlayers", [])
                game_state["events"] = data.get("events", {}).get("Events", [])
                game_state["game_time"] = data.get("gameData", {}).get("gameTime", 0)
                game_state["last_update"] = datetime.utcnow().isoformat()

                active = data.get("activePlayer", {})
                game_state["active_player"] = {
                    "name": active.get("riotIdGameName", ""),
                    "level": active.get("level", 0),
                    "gold": active.get("currentGold", 0),
                }

                # Track dragon type from map terrain and events
                game_data = data.get("gameData", {})
                map_terrain = game_data.get("mapTerrain", "Default")
                game_state["map_terrain"] = map_terrain

                events = data.get("events", {}).get("Events", [])
                dragon_kills = [
                    e for e in events
                    if e.get("EventName") == "DragonKill"
                ]
                game_state["dragons_taken"] = len(dragon_kills)
                if dragon_kills:
                    last_dragon = dragon_kills[-1]
                    game_state["last_dragon"] = last_dragon.get("DragonType", "")

                if map_terrain != "Default" and len(dragon_kills) >= 2:
                    game_state["next_dragon"] = map_terrain
                else:
                    game_state["next_dragon"] = "Unknown"

                # One-time game initialization (fetch build, comp, matchups)
                if not _game_initialized:
                    try:
                        await _initialize_game(data)
                    except Exception as e:
                        logger.error(f"Game initialization error: {e}")
                        _game_initialized = True  # Don't retry forever

                # Generate tips
                new_tips = tip_engine.analyze(game_state)

                # Apply settings filter
                try:
                    from oraclegg.api.routes import _tip_settings
                    cats = _tip_settings.get("categories", {})
                    min_prio = _tip_settings.get("min_priority", 0)
                    urgent_only = _tip_settings.get("urgent_only", False)

                    new_tips = [
                        t for t in new_tips
                        if cats.get(t.category, True)
                        and (t.priority <= min_prio if not urgent_only else t.priority == 0)
                    ]
                except Exception:
                    pass

                if new_tips:
                    for t in new_tips:
                        _tip_counter += 1
                        game_state["all_tips"].append({
                            "id": _tip_counter,
                            "priority": t.priority,
                            "category": t.category,
                            "message": t.message,
                            "time": game_state["game_time"],
                        })
                    game_state["tip_version"] += 1

                    if len(game_state["all_tips"]) > 50:
                        game_state["all_tips"] = game_state["all_tips"][-30:]

            elif game_state["phase"] == "in_game":
                game_state["phase"] = "post_game"
                logger.info("Game ended, running post-game analysis...")

                try:
                    from oraclegg.tracker.post_game import analyze_post_game
                    from oraclegg.riot.client import RiotClient
                    client = RiotClient()
                    await asyncio.sleep(15)
                    result = await analyze_post_game(client)
                    if result:
                        game_state["post_game_result"] = result
                        logger.info(f"Post-game: {result['champion']} {result['kda']} {'WIN' if result['win'] else 'LOSS'}")
                    await client.close()
                except Exception as e:
                    logger.error(f"Post-game analysis error: {e}")

                # Reset for next game but preserve post-game result for display
                pg_result = game_state.get("post_game_result")
                _reset_game_state()
                game_state["post_game_result"] = pg_result
                game_state["phase"] = "post_game"

            else:
                game_state["phase"] = "idle"

        except Exception as e:
            logger.debug(f"Monitor poll error: {e}")

        await asyncio.sleep(poll_interval)
