"""Background game state monitor.

Polls for active games and updates game state for the UI.
On first game detection, auto-scouts all enemies, fetches build recommendations,
classifies enemy comp, generates data-driven lane matchups and strategic advice.
"""

import asyncio
import json
import logging
from datetime import datetime

from sqlalchemy import select

from oraclegg.config import settings
from oraclegg.constants import CHAMP_ICON_MAP, ROLE_MAP, ROLE_ORDER
from oraclegg.db.engine import async_session
from oraclegg.db.models import Champion
from oraclegg.recommender.tips import tip_engine
from oraclegg.riot.live_client import LiveClientAPI

logger = logging.getLogger(__name__)

_tip_counter = 0
_game_initialized = False
_scouting_task: asyncio.Task | None = None

# Alias for backward compatibility with code using POSITION_MAP
POSITION_MAP = ROLE_MAP

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

# Champion class scaling profiles
_SCALING_PROFILE = {
    "Marksman": "late",
    "Mage": "mid",
    "Assassin": "early",
    "Fighter": "mid",
    "Tank": "mid",
    "Support": "mid",
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
    # Scouting intelligence (populated async after game start)
    "enemy_scouting": {},  # champ_name -> scouting report
    "scouting_status": "idle",  # idle, scouting, done, error
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
        tags = json.loads(tags_json)
        if tags:
            return tags[0]
    except Exception:
        pass
    return "Fighter"


def _rate_matchup_from_scouting(enemy_report: dict | None) -> str:
    """Rate a matchup based on scouting data (enemy player stats)."""
    if not enemy_report:
        return "EVEN"

    tendencies = enemy_report.get("tendencies", {})

    # First-timing = strong advantage for us
    if tendencies.get("first_timing"):
        return "POSITIVE"

    # Tilted player = advantage
    if tendencies.get("tilted"):
        return "POSITIVE"

    # Check their current champ stats
    champ_stats = tendencies.get("current_champ_stats")
    if champ_stats:
        wr = champ_stats.get("win_rate", 50)
        games = champ_stats.get("games", 0)
        if games >= 5 and wr >= 60:
            return "NEGATIVE"  # They're good on this champ
        if games >= 5 and wr <= 40:
            return "POSITIVE"  # They struggle on this champ

    # Check recent overall win rate
    recent = tendencies.get("recent_winrate", {})
    pct = recent.get("pct", 50)
    if pct >= 70:
        return "NEGATIVE"
    if pct <= 30:
        return "POSITIVE"

    # OTP on their champ = danger
    if tendencies.get("one_trick"):
        return "NEGATIVE"

    return "EVEN"


def _rate_matchup_class(ally_tags: str, enemy_tags: str) -> str:
    """Fallback: rate matchup by champion class."""
    ally_class = _get_primary_class(ally_tags)
    enemy_class = _get_primary_class(enemy_tags)

    _CLASS_ADVANTAGE = {
        ("Assassin", "Mage"): "POSITIVE",
        ("Assassin", "Marksman"): "POSITIVE",
        ("Tank", "Assassin"): "POSITIVE",
        ("Fighter", "Marksman"): "POSITIVE",
        ("Fighter", "Mage"): "POSITIVE",
        ("Mage", "Tank"): "POSITIVE",
        ("Marksman", "Tank"): "POSITIVE",
    }

    rating = _CLASS_ADVANTAGE.get((ally_class, enemy_class))
    if rating:
        return rating

    reverse = _CLASS_ADVANTAGE.get((enemy_class, ally_class))
    if reverse == "POSITIVE":
        return "NEGATIVE"
    return "EVEN"


def _pair_lanes(
    allies: list[dict],
    enemies: list[dict],
    champ_data: dict,
    enemy_scouting: dict | None = None,
) -> list[dict]:
    """Pair ally and enemy champions by lane position.

    Uses scouting data when available, falls back to class heuristics.
    """
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

            # Try scouting-based rating first, fall back to class heuristic
            enemy_report = (enemy_scouting or {}).get(enemy_name)
            if enemy_report:
                rating = _rate_matchup_from_scouting(enemy_report)
            else:
                rating = _rate_matchup_class(
                    ally_info.get("tags", "[]"),
                    enemy_info.get("tags", "[]"),
                )

            # Extract enemy stats for display
            enemy_stats = {}
            if enemy_report:
                t = enemy_report.get("tendencies", {})
                enemy_stats = {
                    "rank": enemy_report.get("rank"),
                    "win_rate": t.get("recent_winrate", {}).get("pct"),
                    "games": t.get("recent_winrate", {}).get("wins", 0) + t.get("recent_winrate", {}).get("losses", 0),
                    "kda": t.get("kda", {}).get("kda"),
                    "first_timing": t.get("first_timing", False),
                    "tilted": bool(t.get("tilted")),
                    "one_trick": bool(t.get("one_trick")),
                    "hot_streak": t.get("hot_streak", False),
                    "cold_streak": t.get("cold_streak", False),
                    "champ_wr": t.get("current_champ_stats", {}).get("win_rate"),
                    "champ_games": t.get("current_champ_stats", {}).get("games"),
                    "mastery_level": None,
                    "mastery_points": None,
                }
                mastery = enemy_report.get("current_champion_mastery")
                if mastery:
                    enemy_stats["mastery_level"] = mastery.get("level")
                    enemy_stats["mastery_points"] = mastery.get("points")

            matchups.append({
                "role": POSITION_MAP.get(pos, pos),
                "ally_champ": ally_name,
                "ally_icon": CHAMP_ICON_MAP.get(ally_name, ally_name),
                "enemy_champ": enemy_name,
                "enemy_icon": CHAMP_ICON_MAP.get(enemy_name, enemy_name),
                "rating": rating,
                "enemy_stats": enemy_stats,
            })

    return matchups


def _identify_win_conditions(
    allies: list[dict],
    enemies: list[dict],
    champ_data: dict,
    enemy_scouting: dict | None = None,
    archetypes: list[str] | None = None,
) -> list[dict]:
    """Identify win conditions based on scouting data and team comp.

    Returns prioritized list of win condition entries with timing.
    """
    conditions = []

    # 1. Find weak enemy lanes (from scouting)
    if enemy_scouting:
        for p in enemies:
            champ = p.get("championName", "")
            report = enemy_scouting.get(champ)
            if not report:
                continue
            t = report.get("tendencies", {})
            pos = POSITION_MAP.get(p.get("position", ""), "")

            if t.get("first_timing"):
                conditions.append({
                    "champion": champ,
                    "icon": CHAMP_ICON_MAP.get(champ, champ),
                    "type": "target",
                    "reason": f"First-timing {champ}",
                    "detail": f"No recent games on this champion — punish in lane",
                    "timing": "early",
                    "priority": 1,
                })
            elif t.get("tilted"):
                streak = t["tilted"].get("loss_streak", 3)
                conditions.append({
                    "champion": champ,
                    "icon": CHAMP_ICON_MAP.get(champ, champ),
                    "type": "target",
                    "reason": f"Tilted ({streak}L streak)",
                    "detail": f"On a {streak}-game losing streak — likely to make mistakes",
                    "timing": "early",
                    "priority": 2,
                })
            elif t.get("cold_streak"):
                conditions.append({
                    "champion": champ,
                    "icon": CHAMP_ICON_MAP.get(champ, champ),
                    "type": "target",
                    "reason": "Cold streak",
                    "detail": "Struggling recently — apply pressure",
                    "timing": "early",
                    "priority": 3,
                })

            # Identify threats
            champ_stats = t.get("current_champ_stats", {})
            if t.get("one_trick"):
                otp = t["one_trick"]
                conditions.append({
                    "champion": champ,
                    "icon": CHAMP_ICON_MAP.get(champ, champ),
                    "type": "threat",
                    "reason": f"OTP ({otp.get('pct', 0)}% play rate)",
                    "detail": f"One-trick with {otp.get('games', 0)} games — respect their knowledge",
                    "timing": "all",
                    "priority": 4,
                })
            elif champ_stats.get("games", 0) >= 10 and champ_stats.get("win_rate", 50) >= 60:
                conditions.append({
                    "champion": champ,
                    "icon": CHAMP_ICON_MAP.get(champ, champ),
                    "type": "threat",
                    "reason": f"{champ_stats['win_rate']}% WR ({champ_stats['games']}g)",
                    "detail": f"Strong on this pick — don't give them early kills",
                    "timing": "early",
                    "priority": 5,
                })

    # 2. Identify ally carries by role and scaling
    for p in allies:
        name = p.get("championName", "")
        info = champ_data.get(name, {})
        primary = _get_primary_class(info.get("tags", "[]"))
        pos = POSITION_MAP.get(p.get("position", ""), "")
        scaling = _SCALING_PROFILE.get(primary, "mid")

        if primary in ("Marksman",):
            conditions.append({
                "champion": name,
                "icon": CHAMP_ICON_MAP.get(name, name),
                "type": "carry",
                "reason": f"Primary carry ({pos})",
                "detail": "Protect and enable in teamfights",
                "timing": scaling,
                "priority": 6,
            })
        elif pos == "MID" and primary in ("Mage", "Assassin"):
            conditions.append({
                "champion": name,
                "icon": CHAMP_ICON_MAP.get(name, name),
                "type": "carry",
                "reason": f"Mid lane carry",
                "detail": "Roam support or follow-up on their plays",
                "timing": scaling,
                "priority": 7,
            })

    # 3. Comp timing advice
    comp_timing = "mid"
    if archetypes:
        for arch in archetypes:
            if arch in ("scaling",):
                comp_timing = "early"  # We need to end early vs scaling
                break
            if arch in ("early_game", "assassin"):
                comp_timing = "late"  # We outscale them
                break

    if comp_timing != "mid":
        timing_label = {
            "early": "Win early — enemy outscales",
            "late": "Survive early — you outscale",
        }.get(comp_timing, "")
        if timing_label:
            conditions.append({
                "champion": "",
                "icon": "",
                "type": "timing",
                "reason": timing_label,
                "detail": "",
                "timing": comp_timing,
                "priority": 0,
            })

    # Sort by priority (lower = more important)
    conditions.sort(key=lambda x: x["priority"])
    return conditions[:6]


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


async def _scout_enemies_background(enemies: list[dict], champ_data: dict):
    """Scout all enemy players in the background.

    Runs as a separate task so it doesn't block the game monitor.
    Updates game_state progressively as each enemy is scouted.
    """
    from oraclegg.riot.client import RiotClient
    from oraclegg.scouting.scout import scout_player

    game_state["scouting_status"] = "scouting"
    client = RiotClient()
    scouting_results = {}

    try:
        for p in enemies:
            name = p.get("riotIdGameName", p.get("summonerName", ""))
            tag = p.get("riotIdTagLine", "")
            champ = p.get("championName", "")
            champ_id = champ_data.get(champ, {}).get("id")

            if not name:
                continue

            try:
                # Try to get account by Riot ID
                if tag:
                    account = await client.get_account_by_riot_id(name, tag)
                    puuid = account.puuid
                else:
                    # No tag available, skip scouting for this player
                    continue

                report = await scout_player(
                    client, puuid,
                    game_name=name,
                    tag_line=tag,
                    current_champion_id=champ_id,
                )
                scouting_results[champ] = report
                # Update state progressively so UI shows data as it arrives
                game_state["enemy_scouting"] = dict(scouting_results)
                logger.info(f"Scouted {name}#{tag} ({champ}): {report.get('rank', 'Unranked')}")

            except Exception as e:
                logger.warning(f"Failed to scout {name}#{tag}: {e}")

        # All scouting done — recalculate lane matchups and win conditions with real data
        game_state["enemy_scouting"] = scouting_results
        game_state["scouting_status"] = "done"

        # Rebuild lane matchups with scouting data
        allies_raw = game_state.get("_allies_raw", [])
        enemies_raw = game_state.get("_enemies_raw", [])
        archetypes = game_state.get("enemy_archetypes", [])

        if allies_raw and enemies_raw:
            game_state["lane_matchups"] = _pair_lanes(
                allies_raw, enemies_raw, champ_data, scouting_results
            )
            game_state["win_condition"] = _identify_win_conditions(
                allies_raw, enemies_raw, champ_data, scouting_results, archetypes
            )

        logger.info(f"Enemy scouting complete: {len(scouting_results)}/{len(enemies)} players")

    except Exception as e:
        logger.error(f"Enemy scouting failed: {e}")
        game_state["scouting_status"] = "error"
    finally:
        await client.close()


async def _initialize_game(data: dict):
    """Run once when a game is first detected.

    Fetches build recommendation, classifies enemy comp, generates initial
    lane matchups (class-based), then kicks off background scouting for
    data-driven matchup ratings and win conditions.
    """
    global _game_initialized, _scouting_task

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

    # Auto-detect summoner if not configured
    if not settings.summoner_configured:
        tag = you.get("riotIdTagLine", "")
        if active_name and tag:
            riot_id = f"{active_name}#{tag}"
            settings.summoner_riot_id = riot_id
            logger.info(f"Auto-detected summoner: {riot_id}")
            # Persist to .env
            try:
                from pathlib import Path
                import re
                env_path = Path(".env")
                if env_path.exists():
                    content = env_path.read_text()
                    if "SUMMONER_RIOT_ID=" in content:
                        content = re.sub(r"SUMMONER_RIOT_ID=.*", f"SUMMONER_RIOT_ID={riot_id}", content)
                    else:
                        content += f"\nSUMMONER_RIOT_ID={riot_id}\n"
                    env_path.write_text(content)
            except Exception:
                pass  # Best-effort save

    allies = [p for p in all_players if p.get("team") == your_team]
    enemies = [p for p in all_players if p.get("team") != your_team]

    # Store raw player lists for scouting callback
    game_state["_allies_raw"] = allies
    game_state["_enemies_raw"] = enemies

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

    # Initial lane matchups (class-based, updated with scouting later)
    lane_matchups = _pair_lanes(allies, enemies, champ_data)

    # Initial win conditions (will be enriched by scouting)
    win_condition = _identify_win_conditions(allies, enemies, champ_data, None, archetypes)

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
    logger.info(f"Game initialized: {your_champ} {your_position} vs {archetypes[:3]}")

    # Kick off background scouting (doesn't block the monitor loop)
    _scouting_task = asyncio.create_task(
        _scout_enemies_background(enemies, champ_data)
    )

    def _on_scouting_done(task):
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            logger.error(f"Scouting task failed: {exc}")

    _scouting_task.add_done_callback(_on_scouting_done)


def _reset_game_state():
    """Reset enhanced game state for next game."""
    global _game_initialized, _tip_counter, _scouting_task
    _game_initialized = False
    _tip_counter = 0
    if _scouting_task and not _scouting_task.done():
        _scouting_task.cancel()
    _scouting_task = None
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
    game_state["enemy_scouting"] = {}
    game_state["scouting_status"] = "idle"
    game_state["_allies_raw"] = []
    game_state["_enemies_raw"] = []


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

                # One-time game initialization (fetch build, comp, matchups + start scouting)
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
