"""FastAPI routes for OracleGG."""

import json
import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from oraclegg.config import settings
from oraclegg.constants import CHAMP_ICON_MAP, spell_name
from oraclegg.db.engine import async_session
from oraclegg.db.models import BuildAggregate, Champion, Item
from oraclegg.recommender.builds import recommend_build, recommend_for_matchup
from oraclegg.riot.client import RiotClient, RiotAPIError
from oraclegg.scouting.scout import scout_player, scout_team
from oraclegg.scouting.comp import classify_comp_from_ids

from pathlib import Path

logger = logging.getLogger(__name__)



router = APIRouter()
_templates_dir = Path(__file__).parent.parent / "ui" / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

# Template global: dynamic DDragon base URL
templates.env.globals["ddragon_base"] = lambda: settings.ddragon_base

# Singleton Riot client — shared across requests for rate limiting
_riot_client: "RiotClient | None" = None


def get_riot_client() -> "RiotClient":
    global _riot_client
    if _riot_client is None:
        _riot_client = RiotClient()
    return _riot_client


# ─── Pages ────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    async with async_session() as session:
        agg_count = await session.execute(
            select(func.count()).select_from(BuildAggregate)
        )
        champ_count = await session.execute(
            select(func.count()).select_from(Champion)
        )

    return templates.TemplateResponse(request, "dashboard.html", {
        "build_count": agg_count.scalar(),
        "champion_count": champ_count.scalar(),
        "api_key_set": settings.api_key_configured,
        "summoner_set": settings.summoner_configured,
        "summoner_tag": settings.summoner_tag,
    })


@router.get("/champ-select", response_class=HTMLResponse)
async def champ_select_page(request: Request):
    return templates.TemplateResponse(request, "champ_select.html")


@router.get("/in-game", response_class=HTMLResponse)
async def in_game_page(request: Request):
    return templates.TemplateResponse(request, "in_game.html")


@router.get("/demo", response_class=HTMLResponse)
async def demo_page(request: Request):
    return templates.TemplateResponse(request, "in_game.html", {"demo": True})


# ─── API Endpoints ───────────────────────────────────────────────────

@router.get("/api/champions")
async def list_champions():
    """List all champions for search/autocomplete."""
    async with async_session() as session:
        result = await session.execute(
            select(Champion).order_by(Champion.name)
        )
        champions = result.scalars().all()
        return [
            {"id": c.id, "name": c.name, "key": c.key, "tags": json.loads(c.tags)}
            for c in champions
        ]


@router.get("/api/recommend")
async def get_recommendation(
    champion_id: int = Query(...),
    role: str = Query(...),
    enemy_ids: str = Query(default=""),
):
    """Get build recommendation for a champion vs enemy team."""
    try:
        if enemy_ids:
            enemy_champion_ids = [int(x) for x in enemy_ids.split(",") if x]
            result = await recommend_for_matchup(champion_id, role, enemy_champion_ids)
        else:
            result = await recommend_build(champion_id, role, ["balanced"])
        return result
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Recommendation error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to generate recommendation. Check that pipeline data has been collected."})


@router.get("/api/recommend/html", response_class=HTMLResponse)
async def get_recommendation_html(
    request: Request,
    champion_id: int = Query(...),
    role: str = Query(...),
    enemy_ids: str = Query(default=""),
):
    """Get build recommendation as HTML partial (for HTMX)."""
    try:
        if enemy_ids:
            enemy_champion_ids = [int(x) for x in enemy_ids.split(",") if x]
            rec = await recommend_for_matchup(champion_id, role, enemy_champion_ids)
        else:
            rec = await recommend_build(champion_id, role, ["balanced"])

        return templates.TemplateResponse(request, "partials/build_panel.html", {
            "rec": rec,
        })
    except Exception as e:
        logger.error(f"Recommendation HTML error: {e}")
        return HTMLResponse(
            '<div class="text-oracle-red text-sm p-3 bg-oracle-bg rounded border border-oracle-red/30">'
            'Failed to load build recommendation. Make sure pipeline data has been collected.'
            '</div>'
        )


@router.get("/api/scout")
async def scout_summoner(
    name: str = Query(...),
    tag: str = Query(...),
    champion_id: int | None = Query(default=None),
):
    """Scout a single summoner by Riot ID."""
    try:
        client = get_riot_client()
        account = await client.get_account_by_riot_id(name, tag)
        report = await scout_player(
            client, account.puuid,
            game_name=account.gameName,
            tag_line=account.tagLine,
            current_champion_id=champion_id,
        )
        return report
    except RiotAPIError as e:
        if e.status_code == 404:
            return JSONResponse(status_code=404, content={"error": f"Player '{name}#{tag}' not found."})
        elif e.status_code == 401 or e.status_code == 403:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired API key. Update it in Settings."})
        elif e.status_code == 429:
            return JSONResponse(status_code=429, content={"error": "Rate limited. Please wait a moment and try again."})
        return JSONResponse(status_code=502, content={"error": f"Riot API error: {e}"})
    except Exception as e:
        logger.error(f"Scout error for {name}#{tag}: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to scout player. Check your API key and connection."})


@router.get("/api/scout/html", response_class=HTMLResponse)
async def scout_summoner_html(
    request: Request,
    name: str = Query(...),
    tag: str = Query(...),
    champion_id: int | None = Query(default=None),
):
    """Scout a summoner and return HTML partial."""
    try:
        client = get_riot_client()
        account = await client.get_account_by_riot_id(name, tag)
        report = await scout_player(
            client, account.puuid,
            game_name=account.gameName,
            tag_line=account.tagLine,
            current_champion_id=champion_id,
        )
        return templates.TemplateResponse(request, "partials/scouting_card.html", {
            "player": report,
        })
    except RiotAPIError as e:
        if e.status_code == 404:
            error_msg = f"Player '{name}#{tag}' not found. Check the name and tag."
        elif e.status_code == 401 or e.status_code == 403:
            error_msg = "Invalid or expired API key. Update it in Settings."
        elif e.status_code == 429:
            error_msg = "Rate limited. Please wait a moment and try again."
        else:
            error_msg = f"Riot API error ({e.status_code}). Try again later."
        return templates.TemplateResponse(request, "partials/scouting_card.html", {
            "player": {"error": error_msg},
        })
    except Exception as e:
        logger.error(f"Scout HTML error for {name}#{tag}: {e}")
        return templates.TemplateResponse(request, "partials/scouting_card.html", {
            "player": {"error": "Failed to scout player. Check your API key and connection."},
        })


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html")


# Tip settings (in-memory, synced from frontend localStorage)
_tip_settings = {
    "categories": {"item": True, "threat": True, "build": True, "objective": True, "strategy": True},
    "min_priority": 2,  # 2=all, 1=important+urgent, 0=urgent only
    "auto_redirect": True,
    "auto_postgame": True,
}


@router.get("/api/settings")
async def get_settings():
    return _tip_settings


@router.post("/api/settings")
async def save_settings(request: Request):
    global _tip_settings
    data = await request.json()
    _tip_settings.update(data)

    # Persist to DB
    async with async_session() as session:
        from oraclegg.db.models import UserSetting
        await session.merge(UserSetting(key="tip_settings", value=json.dumps(_tip_settings)))
        await session.commit()

    return {"ok": True}


@router.get("/api/version")
async def get_version():
    from oraclegg.updater import VERSION
    return {"version": VERSION}


@router.get("/api/update/check")
async def check_update():
    from oraclegg.updater import check_for_update
    update = await check_for_update()
    if update:
        return {"available": True, **update}
    return {"available": False}


@router.post("/api/update/apply")
async def apply_update(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        return {"ok": False, "error": "No download URL"}

    from oraclegg.updater import download_and_apply_update
    result = await download_and_apply_update(url)
    return {"ok": result, "restart_required": result}


@router.get("/api/settings/account")
async def get_account_settings():
    """Get current API key status and summoner info."""
    key = settings.riot_api_key
    return {
        "api_key_set": key and key != "RGAPI-change-me",
        "api_key_preview": f"...{key[-8:]}" if key and len(key) > 10 else "",
        "summoner_name": settings.summoner_name,
        "summoner_tag": settings.summoner_tag,
        "region": settings.riot_region,
        "platform": settings.riot_platform,
    }


@router.post("/api/settings/api-key")
async def save_api_key(request: Request):
    """Save and validate a new Riot API key."""
    data = await request.json()
    key = data.get("key", "").strip()

    if not key.startswith("RGAPI-"):
        return {"valid": False, "error": "Key must start with RGAPI-"}

    # Validate by making a test request (use platform status — works with dev keys)
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://{settings.riot_platform}.api.riotgames.com/lol/status/v4/platform-data",
                headers={"X-Riot-Token": key},
                timeout=5,
            )
            if r.status_code in (401, 403):
                return {"valid": False, "error": "Invalid or expired key"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

    # Save to .env file
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        import re
        if "RIOT_API_KEY=" in content:
            content = re.sub(r"RIOT_API_KEY=.*", f"RIOT_API_KEY={key}", content)
        else:
            content += f"\nRIOT_API_KEY={key}\n"
        env_path.write_text(content)
    else:
        env_path.write_text(f"RIOT_API_KEY={key}\n")

    # Hot-reload the key into the running app
    settings.riot_api_key = key

    # Update the singleton client
    global _riot_client
    _riot_client = None
    return {"valid": True}


@router.post("/api/settings/claude-key")
async def save_claude_key(request: Request):
    """Save Claude API key for AI analysis."""
    data = await request.json()
    key = data.get("key", "").strip()

    # Save to .env
    import re
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        if "ANTHROPIC_API_KEY=" in content:
            content = re.sub(r"ANTHROPIC_API_KEY=.*", f"ANTHROPIC_API_KEY={key}", content)
        else:
            content += f"\nANTHROPIC_API_KEY={key}\n"
        env_path.write_text(content)

    settings.anthropic_api_key = key
    return {"ok": True}


@router.post("/api/settings/region")
async def save_region(request: Request):
    """Save region/platform settings."""
    data = await request.json()
    platform = data.get("platform", "").strip()
    if not platform:
        return {"ok": False, "error": "Platform is required"}

    # Map platform to region routing
    region_map = {
        "na1": "americas", "br1": "americas", "la1": "americas", "la2": "americas",
        "euw1": "europe", "eun1": "europe", "tr1": "europe", "ru": "europe",
        "kr": "asia", "jp1": "asia",
        "oc1": "sea", "ph2": "sea", "sg2": "sea", "th2": "sea", "tw2": "sea", "vn2": "sea",
    }
    region = region_map.get(platform, "americas")

    # Save to .env
    import re
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        for key, val in [("RIOT_PLATFORM", platform), ("RIOT_REGION", region)]:
            if f"{key}=" in content:
                content = re.sub(f"{key}=.*", f"{key}={val}", content)
            else:
                content += f"\n{key}={val}\n"
        env_path.write_text(content)

    # Hot-reload
    settings.riot_platform = platform
    settings.riot_region = region
    return {"ok": True, "platform": platform, "region": region}


@router.post("/api/settings/summoner")
async def save_summoner(request: Request):
    """Save summoner Riot ID."""
    data = await request.json()
    name = data.get("name", "").strip()
    tag = data.get("tag", "").strip()

    if not name or not tag:
        return {"ok": False, "error": "Name and tag are required"}

    riot_id = f"{name}#{tag}"

    # Save to .env
    import re
    env_path = Path(".env")
    if env_path.exists():
        content = env_path.read_text()
        if "SUMMONER_RIOT_ID=" in content:
            content = re.sub(r"SUMMONER_RIOT_ID=.*", f"SUMMONER_RIOT_ID={riot_id}", content)
        else:
            content += f"\nSUMMONER_RIOT_ID={riot_id}\n"
        env_path.write_text(content)

    # Hot-reload
    settings.summoner_riot_id = riot_id
    return {"ok": True}


@router.get("/api/game-state/demo")
async def demo_game_state():
    """Return fake game state for demo/preview purposes."""
    return {
        "phase": "in_game",
        "game_time": 1247.5,
        "active_player": {"name": "Mistyck", "level": 14, "gold": 892},
        "players": [
            {"name": "Mistyck", "champion": "Viego", "championIcon": "Viego", "team": "CHAOS", "level": 14, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 8, "deaths": 3, "assists": 6, "creepScore": 187, "wardScore": 24},
             "items": [{"itemID": 6672, "displayName": "Kraken Slayer"}, {"itemID": 6676, "displayName": "The Collector"}, {"itemID": 3111, "displayName": "Mercury's Treads"}, {"itemID": 3036, "displayName": "Lord Dominik's Regards"}]},
            {"name": "TopDiff99", "champion": "Riven", "championIcon": "Riven", "team": "CHAOS", "level": 13, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 5, "deaths": 4, "assists": 3, "creepScore": 201, "wardScore": 18},
             "items": [{"itemID": 6610, "displayName": "Sundered Sky"}, {"itemID": 6333, "displayName": "Death's Dance"}, {"itemID": 3158, "displayName": "Ionian Boots of Lucidity"}]},
            {"name": "MidOrFeed", "champion": "Annie", "championIcon": "Annie", "team": "CHAOS", "level": 14, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 11, "deaths": 2, "assists": 7, "creepScore": 168, "wardScore": 21},
             "items": [{"itemID": 3089, "displayName": "Rabadon's Deathcap"}, {"itemID": 3118, "displayName": "Malignance"}, {"itemID": 4645, "displayName": "Shadowflame"}, {"itemID": 3020, "displayName": "Sorcerer's Shoes"}]},
            {"name": "ADCarry1", "champion": "Jinx", "championIcon": "Jinx", "team": "CHAOS", "level": 12, "isDead": True, "respawnTimer": 18,
             "scores": {"kills": 6, "deaths": 5, "assists": 9, "creepScore": 195, "wardScore": 15},
             "items": [{"itemID": 6672, "displayName": "Kraken Slayer"}, {"itemID": 3094, "displayName": "Rapid Firecannon"}, {"itemID": 3031, "displayName": "Infinity Edge"}]},
            {"name": "SuppDiff", "champion": "Thresh", "championIcon": "Thresh", "team": "CHAOS", "level": 11, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 1, "deaths": 3, "assists": 18, "creepScore": 28, "wardScore": 67},
             "items": [{"itemID": 3190, "displayName": "Locket of the Iron Solari"}, {"itemID": 3222, "displayName": "Mikael's Blessing"}, {"itemID": 3117, "displayName": "Mobility Boots"}]},
            {"name": "EnemyTop", "champion": "Malphite", "championIcon": "Malphite", "team": "ORDER", "level": 13, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 2, "deaths": 5, "assists": 8, "creepScore": 178, "wardScore": 14},
             "items": [{"itemID": 3143, "displayName": "Randuin's Omen"}, {"itemID": 3075, "displayName": "Thornmail"}, {"itemID": 3047, "displayName": "Plated Steelcaps"}]},
            {"name": "XxJunglerxX", "champion": "Warwick", "championIcon": "Warwick", "team": "ORDER", "level": 14, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 12, "deaths": 2, "assists": 5, "creepScore": 112, "wardScore": 31},
             "items": [{"itemID": 6631, "displayName": "Stridebreaker"}, {"itemID": 3053, "displayName": "Sterak's Gage"}, {"itemID": 6333, "displayName": "Death's Dance"}, {"itemID": 3065, "displayName": "Spirit Visage"}, {"itemID": 3047, "displayName": "Plated Steelcaps"}]},
            {"name": "MidLaner2", "champion": "Zed", "championIcon": "Zed", "team": "ORDER", "level": 14, "isDead": True, "respawnTimer": 32,
             "scores": {"kills": 7, "deaths": 6, "assists": 3, "creepScore": 192, "wardScore": 11},
             "items": [{"itemID": 6697, "displayName": "Hubris"}, {"itemID": 6676, "displayName": "The Collector"}, {"itemID": 6694, "displayName": "Serylda's Grudge"}]},
            {"name": "BotLane22", "champion": "Vayne", "championIcon": "Vayne", "team": "ORDER", "level": 13, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 4, "deaths": 6, "assists": 2, "creepScore": 210, "wardScore": 13},
             "items": [{"itemID": 6672, "displayName": "Kraken Slayer"}, {"itemID": 3124, "displayName": "Guinsoo's Rageblade"}, {"itemID": 3006, "displayName": "Berserker's Greaves"}]},
            {"name": "SuppMain", "champion": "Leona", "championIcon": "Leona", "team": "ORDER", "level": 11, "isDead": False, "respawnTimer": 0,
             "scores": {"kills": 1, "deaths": 7, "assists": 12, "creepScore": 22, "wardScore": 58},
             "items": [{"itemID": 3190, "displayName": "Locket of the Iron Solari"}, {"itemID": 3047, "displayName": "Plated Steelcaps"}]},
        ],
        "all_tips": [
            {"id": 1, "priority": 0, "category": "threat", "message": "Warwick is 12/2 — DO NOT fight them alone. Group up or avoid.", "time": 980},
            {"id": 2, "priority": 0, "category": "build", "message": "Warwick is fed and heals a lot — your team needs anti-heal!", "time": 985},
            {"id": 3, "priority": 1, "category": "strategy", "message": "Your team has 2 scaling champions. Play safe early, farm up — you outscale them.", "time": 300},
            {"id": 4, "priority": 1, "category": "build", "message": "Recommended boots: Mercury's Treads — 3 hard CC champions, tenacity is critical", "time": 240},
            {"id": 5, "priority": 1, "category": "item", "message": "Warwick completed Spirit Visage — increased healing, consider anti-heal", "time": 1100},
            {"id": 6, "priority": 1, "category": "objective", "message": "Infernal Dragon soul — Must take, extra valuable for your 2 scaling/burst champions", "time": 1200},
            {"id": 7, "priority": 2, "category": "strategy", "message": "Enemy has better teamfight. Avoid 5v5 — look for picks and split push instead.", "time": 600},
        ],
        "tip_version": 7,
        "post_game_result": None,
        "map_terrain": "Infernal",
        "next_dragon": "Infernal",
        "dragons_taken": 3,
        "your_champion": "Viego",
        "your_champion_icon": "Viego",
        "your_role": "JUNGLE",
        "enemy_archetypes": ["heavy_ad", "engage"],
        "build_rec": {
            "champion": {"name": "Viego", "key": "Viego"},
            "win_rate": 58.3,
            "sample_size": 42,
            "build_path": [
                {"id": 6672, "name": "Kraken Slayer"},
                {"id": 6676, "name": "The Collector"},
                {"id": 3036, "name": "Lord Dominik's Regards"},
                {"id": 6673, "name": "Immortal Shieldbow"},
                {"id": 3031, "name": "Infinity Edge"},
            ],
            "boots": {"id": 3111, "name": "Mercury's Treads"},
            "skill_max_order": "Q>W>E",
        },
        "strategy": "The enemy team is heavy AD. Armor items are very gold-efficient here. Tabis and an early armor component go a long way.",
        "lane_matchups": [
            {"role": "TOP", "ally_champ": "Riven", "ally_icon": "Riven", "enemy_champ": "Malphite", "enemy_icon": "Malphite", "rating": "NEGATIVE", "rating_reason": "Hard matchup — Malphite stacks armor", "enemy_stats": {"rank": "Gold II 45LP", "champ_wr": 62, "champ_games": 34}},
            {"role": "JUNGLE", "ally_champ": "Viego", "ally_icon": "Viego", "enemy_champ": "Warwick", "enemy_icon": "Warwick", "rating": "NEGATIVE", "rating_reason": "67% WR on this champ (89G)", "enemy_stats": {"rank": "Plat I 78LP", "champ_wr": 67, "champ_games": 89, "one_trick": True}},
            {"role": "MID", "ally_champ": "Annie", "ally_icon": "Annie", "enemy_champ": "Zed", "enemy_icon": "Zed", "rating": "POSITIVE", "rating_reason": "First-timing this champ", "enemy_stats": {"rank": "Gold IV 12LP", "first_timing": True}},
            {"role": "ADC", "ally_champ": "Jinx", "ally_icon": "Jinx", "enemy_champ": "Vayne", "enemy_icon": "Vayne", "rating": "EVEN", "rating_reason": "", "enemy_stats": {"rank": "Gold III 55LP", "champ_wr": 51, "champ_games": 22}},
            {"role": "SUPPORT", "ally_champ": "Thresh", "ally_icon": "Thresh", "enemy_champ": "Leona", "enemy_icon": "Leona", "rating": "POSITIVE", "rating_reason": "Only 38% WR on this champ (16G)", "enemy_stats": {"rank": "Silver I 88LP", "champ_wr": 38, "champ_games": 16, "tilted": True}},
        ],
        "runes": {
            "primary_tree": "Precision",
            "secondary_tree": "Inspiration",
            "keystone": {"name": "Conqueror", "icon": "perk-images/Styles/Precision/Conqueror/Conqueror.png", "slot": 0, "tree": "Precision"},
            "all_runes": [
                {"name": "Conqueror", "icon": "perk-images/Styles/Precision/Conqueror/Conqueror.png", "slot": 0, "tree": "Precision"},
                {"name": "Triumph", "icon": "perk-images/Styles/Precision/Triumph.png", "slot": 1, "tree": "Precision"},
                {"name": "Legend: Alacrity", "icon": "perk-images/Styles/Precision/LegendAlacrity/LegendAlacrity.png", "slot": 2, "tree": "Precision"},
                {"name": "Last Stand", "icon": "perk-images/Styles/Precision/LastStand/LastStand.png", "slot": 3, "tree": "Precision"},
                {"name": "Magical Footwear", "icon": "perk-images/Styles/Inspiration/MagicalFootwear/MagicalFootwear.png", "slot": 1, "tree": "Inspiration"},
                {"name": "Cosmic Insight", "icon": "perk-images/Styles/Inspiration/CosmicInsight/CosmicInsight.png", "slot": 3, "tree": "Inspiration"},
            ],
        },
        "summoner_spells": ["Flash", "Smite"],
        "win_condition": [
            {"reason": "Focus ZED mid", "detail": "First-timing Zed, free lane for Annie", "type": "target", "champion": "Zed", "icon": "Zed", "timing": "early"},
            {"reason": "Avoid WARWICK 1v1", "detail": "OTP with 67% WR, 12/2 this game — group to shut him down", "type": "threat", "champion": "Warwick", "icon": "Warwick", "timing": "all"},
            {"reason": "Punish LEONA bot", "detail": "38% WR on Leona, tilted — bot lane is free", "type": "target", "champion": "Leona", "icon": "Leona", "timing": "early"},
            {"reason": "You outscale — play for late", "detail": "Jinx + Viego outscale their comp after 3 items. Don't force early.", "type": "timing", "timing": "late"},
            {"reason": "Contest Infernal Drake", "detail": "Infernal soul is high value for your 2 scaling carries. Prioritize every dragon.", "type": "carry", "timing": "mid"},
        ],
        "scouting_status": "done",
        "last_update": "2026-03-29T22:30:00",
    }


@router.get("/api/champ-select/live")
async def champ_select_live():
    """Get live champ select data from LCU if available."""
    from oraclegg.game_loop.monitor import game_state
    lcu_phase = game_state.get("lcu_phase", "idle")
    data = game_state.get("champ_select_data")

    if lcu_phase != "champ_select" or not data:
        return {"active": False}

    return {
        "active": True,
        "data": data,
    }


@router.get("/api/matchup-tips")
async def get_matchup_tips(
    your_champ: str = Query(...),
    enemy_champ: str = Query(...),
    role: str = Query(default=""),
):
    """Get matchup-specific tips from the knowledge base."""
    from oraclegg.recommender.matchup_kb import get_matchup_tips, get_role_tips
    tips = get_matchup_tips(your_champ, enemy_champ)
    role_tips = get_role_tips(role) if role else []
    return {
        "matchup_tips": tips,
        "role_tips": role_tips,
        "has_specific": len(tips) > 0,
    }


@router.get("/api/boots")
async def get_boot_recommendation(
    champion: str = Query(...),
    role: str = Query(...),
    enemies: str = Query(..., description="Comma-separated enemy champion names"),
):
    """Get boot recommendation based on enemy team."""
    try:
        from oraclegg.recommender.rules.boots_rules import recommend_boots
        enemy_list = [e.strip() for e in enemies.split(",") if e.strip()]
        rec = recommend_boots(champion, role, enemy_list, {})
        return rec
    except Exception as e:
        logger.error(f"Boot recommendation error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to generate boot recommendation."})


@router.get("/api/dragon")
async def get_dragon_value(
    dragon_type: str = Query(...),
    allies: str = Query(..., description="Comma-separated ally champion names"),
    enemies: str = Query(..., description="Comma-separated enemy champion names"),
):
    """Evaluate dragon value for the current game."""
    try:
        from oraclegg.recommender.rules.dragon_rules import evaluate_dragon
        ally_list = [a.strip() for a in allies.split(",") if a.strip()]
        enemy_list = [e.strip() for e in enemies.split(",") if e.strip()]
        return evaluate_dragon(dragon_type, ally_list, enemy_list)
    except Exception as e:
        logger.error(f"Dragon evaluation error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to evaluate dragon value."})


@router.get("/api/comp/classify")
async def classify_team_comp(
    champion_ids: str = Query(..., description="Comma-separated champion IDs"),
):
    """Classify a team composition into archetypes."""
    try:
        ids = [int(x) for x in champion_ids.split(",") if x]
        async with async_session() as session:
            archetypes = await classify_comp_from_ids(ids, session)
        return {"champion_ids": ids, "archetypes": archetypes}
    except Exception as e:
        logger.error(f"Comp classification error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to classify team composition."})


@router.get("/api/stats")
async def pipeline_stats():
    """Get pipeline stats."""
    async with async_session() as session:
        agg_count = (await session.execute(
            select(func.count()).select_from(BuildAggregate)
        )).scalar()
        champ_count = (await session.execute(
            select(func.count()).select_from(Champion)
        )).scalar()
        item_count = (await session.execute(
            select(func.count()).select_from(Item)
        )).scalar()

        top_champs = (await session.execute(
            select(
                BuildAggregate.champion_id,
                func.sum(BuildAggregate.sample_size).label("total_games"),
                func.count().label("builds"),
            )
            .group_by(BuildAggregate.champion_id)
            .order_by(func.sum(BuildAggregate.sample_size).desc())
            .limit(10)
        )).all()

        # Batch-fetch champion names (avoid N+1)
        champ_ids = [row[0] for row in top_champs]
        champ_result = await session.execute(
            select(Champion).where(Champion.id.in_(champ_ids))
        )
        champ_map = {c.id: c.name for c in champ_result.scalars().all()}

        top_list = []
        for champ_id, total_games, builds in top_champs:
            top_list.append({
                "champion": champ_map.get(champ_id, f"ID:{champ_id}"),
                "total_games": total_games,
                "builds": builds,
            })

    return {
        "aggregates": agg_count,
        "champions": champ_count,
        "items": item_count,
        "top_champions": top_list,
    }


# ─── Pipeline ────────────────────────────────────────────────────────

@router.post("/api/pipeline/run")
async def run_pipeline(
    players: int = Query(default=50),
    min_sample: int = Query(default=5),
):
    """Trigger the data pipeline (collection + aggregation) in background."""
    if not settings.api_key_configured:
        return JSONResponse(status_code=400, content={
            "error": "Riot API key not configured. Set it in Settings first."
        })

    from oraclegg.pipeline.runner import trigger_pipeline, pipeline_state
    started = trigger_pipeline(max_players=players, min_sample=min_sample)
    if not started:
        return JSONResponse(status_code=409, content={
            "error": "Pipeline is already running.",
            **pipeline_state,
        })
    return {"status": "started", "message": "Pipeline started in background."}


@router.get("/api/pipeline/status")
async def get_pipeline_status():
    """Get current pipeline execution status."""
    from oraclegg.pipeline.runner import pipeline_state
    return pipeline_state


@router.get("/api/game-state")
async def get_game_state():
    """Get current game state (polled by UI)."""
    from oraclegg.game_loop.monitor import game_state
    return {
        "phase": game_state["phase"],
        "lcu_phase": game_state.get("lcu_phase", ""),
        "game_time": round(game_state.get("game_time", 0), 1),
        "active_player": game_state.get("active_player"),
        "ddragon": settings.ddragon_base,
        "players": [
            {
                "name": p.get("riotIdGameName", p.get("summonerName", "")),
                "champion": p.get("championName", ""),
                "championIcon": CHAMP_ICON_MAP.get(p.get("championName", ""), p.get("championName", "")),
                "team": p.get("team", ""),
                "level": p.get("level", 0),
                "position": p.get("position", ""),
                "isDead": p.get("isDead", False),
                "respawnTimer": p.get("respawnTimer", 0),
                "scores": p.get("scores", {}),
                "items": [
                    item for item in p.get("items", [])
                    if item.get("itemID", 0) > 0
                ],
            }
            for p in game_state.get("players", [])
        ],
        "events_count": len(game_state.get("events", [])),
        "all_tips": game_state.get("all_tips", [])[-15:],
        "tip_version": game_state.get("tip_version", 0),
        "post_game_result": game_state.get("post_game_result"),
        "map_terrain": game_state.get("map_terrain", "Default"),
        "next_dragon": game_state.get("next_dragon", "Unknown"),
        "dragons_taken": game_state.get("dragons_taken", 0),
        "last_update": game_state.get("last_update"),
        "lcu_phase": game_state.get("lcu_phase"),
        "champ_select_data": game_state.get("champ_select_data"),
        # Enhanced game intelligence (populated on game start)
        "your_champion": game_state.get("your_champion"),
        "your_champion_icon": game_state.get("your_champion_icon"),
        "your_role": game_state.get("your_role"),
        "enemy_archetypes": game_state.get("enemy_archetypes", []),
        "build_rec": game_state.get("build_rec"),
        "strategy": game_state.get("strategy", ""),
        "lane_matchups": game_state.get("lane_matchups", []),
        "runes": game_state.get("runes"),
        "summoner_spells": game_state.get("summoner_spells", []),
        "win_condition": game_state.get("win_condition", []),
        "scouting_status": game_state.get("scouting_status", "idle"),
    }


# ─── Tracking ────────────────────────────────────────────────────────

@router.get("/tracking", response_class=HTMLResponse)
async def tracking_page(request: Request):
    return templates.TemplateResponse(request, "tracking.html")


@router.get("/api/tracking/matches")
async def tracking_matches():
    try:
        from oraclegg.tracker.personal import get_recent_matches
        return await get_recent_matches(20)
    except Exception as e:
        logger.error(f"Tracking matches error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to load match history."})


@router.get("/api/tracking/champions")
async def tracking_champions():
    try:
        from oraclegg.tracker.personal import get_champion_stats
        return await get_champion_stats()
    except Exception as e:
        logger.error(f"Tracking champions error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to load champion stats."})


@router.get("/api/tracking/overview")
async def tracking_overview():
    try:
        from oraclegg.tracker.personal import get_overall_stats
        return await get_overall_stats()
    except Exception as e:
        logger.error(f"Tracking overview error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to load overview stats."})


@router.get("/api/tracking/analysis/{match_id}")
async def match_analysis(match_id: str):
    """Get AI analysis for a specific match."""
    try:
        from oraclegg.tracker.ai_analysis import get_or_generate_analysis
        result = await get_or_generate_analysis(match_id)
        if not result:
            return {"error": "Match not found"}
        return result
    except Exception as e:
        logger.error(f"Match analysis error for {match_id}: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to generate match analysis."})


@router.post("/api/tracking/analyze-all")
async def analyze_all_matches():
    """Generate analysis for all matches without one."""
    try:
        from oraclegg.tracker.ai_analysis import generate_all_analyses
        count = await generate_all_analyses()
        return {"analyzed": count}
    except Exception as e:
        logger.error(f"Analyze all error: {e}")
        return JSONResponse(status_code=500, content={"error": "Failed to analyze matches."})
