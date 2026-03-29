"""Background game state monitor.

Polls for active games and updates game state for the UI.
"""

import asyncio
import logging
from datetime import datetime

from oraclegg.config import settings
from oraclegg.recommender.tips import tip_engine
from oraclegg.riot.live_client import LiveClientAPI

logger = logging.getLogger(__name__)

_tip_counter = 0

# Shared state accessible from API routes
game_state = {
    "phase": "idle",
    "game_data": None,
    "players": [],
    "events": [],
    "game_time": 0,
    "last_update": None,
    "all_tips": [],  # persistent tip history with IDs
    "tip_version": 0,  # increments when new tips are added
}


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
                # mapTerrain tells us the rift type after 2nd dragon:
                # "Infernal", "Mountain", "Ocean", "Cloud", "Hextech", "Chemtech"
                game_state["map_terrain"] = map_terrain

                # Parse dragon events to track which dragons have been taken
                events = data.get("events", {}).get("Events", [])
                dragon_kills = [
                    e for e in events
                    if e.get("EventName") == "DragonKill"
                ]
                game_state["dragons_taken"] = len(dragon_kills)
                if dragon_kills:
                    last_dragon = dragon_kills[-1]
                    game_state["last_dragon"] = last_dragon.get("DragonType", "")

                # Determine next dragon type
                # Before 3rd dragon: type varies. After rift changes: all are the terrain type
                if map_terrain != "Default" and len(dragon_kills) >= 2:
                    game_state["next_dragon"] = map_terrain
                else:
                    game_state["next_dragon"] = "Unknown"

                # Generate tips — filter by user settings
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

                    # Cap list
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

                # Reset for next game
                tip_engine._seen_items.clear()
                tip_engine._game_tips_given.clear()
                game_state["all_tips"] = []
                game_state["tip_version"] = 0
                _tip_counter = 0
            else:
                game_state["phase"] = "idle"

        except Exception as e:
            logger.debug(f"Monitor poll error: {e}")

        await asyncio.sleep(poll_interval)
