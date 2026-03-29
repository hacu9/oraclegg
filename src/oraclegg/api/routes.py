"""FastAPI routes for OracleGG."""

import json

from fastapi import APIRouter, Query, Request

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
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, func

from oraclegg.db.engine import async_session
from oraclegg.db.models import BuildAggregate, Champion, Item
from oraclegg.recommender.builds import recommend_build, recommend_for_matchup
from oraclegg.riot.client import RiotClient
from oraclegg.scouting.scout import scout_player, scout_team
from oraclegg.scouting.comp import classify_comp_from_ids

from pathlib import Path

router = APIRouter()
_templates_dir = Path(__file__).parent.parent / "ui" / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))

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
        # Get stats
        agg_count = await session.execute(
            select(func.count()).select_from(BuildAggregate)
        )
        champ_count = await session.execute(
            select(func.count()).select_from(Champion)
        )

    return templates.TemplateResponse(request, "dashboard.html", {
        "build_count": agg_count.scalar(),
        "champion_count": champ_count.scalar(),
    })


@router.get("/champ-select", response_class=HTMLResponse)
async def champ_select_page(request: Request):
    return templates.TemplateResponse(request, "champ_select.html")


@router.get("/in-game", response_class=HTMLResponse)
async def in_game_page(request: Request):
    return templates.TemplateResponse(request, "in_game.html")


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
    """Get build recommendation for a champion vs enemy team.

    enemy_ids: comma-separated champion IDs (e.g., "86,238,64,222,412")
    """
    if enemy_ids:
        enemy_champion_ids = [int(x) for x in enemy_ids.split(",") if x]
        result = await recommend_for_matchup(champion_id, role, enemy_champion_ids)
    else:
        result = await recommend_build(champion_id, role, ["balanced"])

    return result


@router.get("/api/recommend/html", response_class=HTMLResponse)
async def get_recommendation_html(
    request: Request,
    champion_id: int = Query(...),
    role: str = Query(...),
    enemy_ids: str = Query(default=""),
):
    """Get build recommendation as HTML partial (for HTMX)."""
    if enemy_ids:
        enemy_champion_ids = [int(x) for x in enemy_ids.split(",") if x]
        rec = await recommend_for_matchup(champion_id, role, enemy_champion_ids)
    else:
        rec = await recommend_build(champion_id, role, ["balanced"])

    return templates.TemplateResponse(request, "partials/build_panel.html", {
        "rec": rec,
    })


@router.get("/api/scout")
async def scout_summoner(
    name: str = Query(...),
    tag: str = Query(...),
    champion_id: int | None = Query(default=None),
):
    """Scout a single summoner by Riot ID."""
    client = get_riot_client()
    account = await client.get_account_by_riot_id(name, tag)
    report = await scout_player(
        client, account.puuid,
        game_name=account.gameName,
        tag_line=account.tagLine,
        current_champion_id=champion_id,
    )
    return report


@router.get("/api/scout/html", response_class=HTMLResponse)
async def scout_summoner_html(
    request: Request,
    name: str = Query(...),
    tag: str = Query(...),
    champion_id: int | None = Query(default=None),
):
    """Scout a summoner and return HTML partial."""
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


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html")


# Tip settings (in-memory, synced from frontend localStorage)
_tip_settings = {
    "categories": {"item": True, "threat": True, "build": True, "objective": True, "strategy": True},
    "min_priority": 0,
    "urgent_only": False,
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
    from oraclegg.config import settings
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

    # Validate by making a test request
    import httpx
    try:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                "https://americas.api.riotgames.com/riot/account/v1/accounts/me",
                headers={"X-Riot-Token": key},
                timeout=5,
            )
            # 401 = bad key, 403 = good key but this endpoint needs auth
            # Any non-401 means the key is valid
            if r.status_code == 401:
                return {"valid": False, "error": "Invalid or expired key"}
    except Exception as e:
        return {"valid": False, "error": str(e)}

    # Save to .env file
    from pathlib import Path
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
    from oraclegg.config import settings
    settings.riot_api_key = key

    # Update the singleton client
    global _riot_client
    _riot_client = None  # Will be recreated with new key on next use

    return {"valid": True}


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

    # Hot-reload
    from oraclegg.config import settings
    settings.summoner_riot_id = riot_id

    return {"ok": True}


@router.get("/api/boots")
async def get_boot_recommendation(
    champion: str = Query(...),
    role: str = Query(...),
    enemies: str = Query(..., description="Comma-separated enemy champion names"),
):
    """Get boot recommendation based on enemy team."""
    from oraclegg.recommender.rules.boots_rules import recommend_boots
    enemy_list = [e.strip() for e in enemies.split(",") if e.strip()]
    rec = recommend_boots(champion, role, enemy_list, {})
    return rec


@router.get("/api/dragon")
async def get_dragon_value(
    dragon_type: str = Query(...),
    allies: str = Query(..., description="Comma-separated ally champion names"),
    enemies: str = Query(..., description="Comma-separated enemy champion names"),
):
    """Evaluate dragon value for the current game."""
    from oraclegg.recommender.rules.dragon_rules import evaluate_dragon
    ally_list = [a.strip() for a in allies.split(",") if a.strip()]
    enemy_list = [e.strip() for e in enemies.split(",") if e.strip()]
    return evaluate_dragon(dragon_type, ally_list, enemy_list)


@router.get("/api/comp/classify")
async def classify_team_comp(
    champion_ids: str = Query(..., description="Comma-separated champion IDs"),
):
    """Classify a team composition into archetypes."""
    ids = [int(x) for x in champion_ids.split(",") if x]
    async with async_session() as session:
        archetypes = await classify_comp_from_ids(ids, session)
    return {"champion_ids": ids, "archetypes": archetypes}


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

        # Most covered champions
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

        top_list = []
        for champ_id, total_games, builds in top_champs:
            champ = (await session.execute(
                select(Champion).where(Champion.id == champ_id)
            )).scalar_one_or_none()
            top_list.append({
                "champion": champ.name if champ else f"ID:{champ_id}",
                "total_games": total_games,
                "builds": builds,
            })

    return {
        "aggregates": agg_count,
        "champions": champ_count,
        "items": item_count,
        "top_champions": top_list,
    }


@router.get("/api/game-state")
async def get_game_state():
    """Get current game state (polled by UI)."""
    from oraclegg.game_loop.monitor import game_state
    return {
        "phase": game_state["phase"],
        "game_time": round(game_state.get("game_time", 0), 1),
        "active_player": game_state.get("active_player"),
        "players": [
            {
                "name": p.get("riotIdGameName", p.get("summonerName", "")),
                "champion": p.get("championName", ""),
                "championIcon": CHAMP_ICON_MAP.get(p.get("championName", ""), p.get("championName", "")),
                "team": p.get("team", ""),
                "level": p.get("level", 0),
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
    }


# ─── Tracking ────────────────────────────────────────────────────────

@router.get("/tracking", response_class=HTMLResponse)
async def tracking_page(request: Request):
    return templates.TemplateResponse(request, "tracking.html")


@router.get("/api/tracking/matches")
async def tracking_matches():
    from oraclegg.tracker.personal import get_recent_matches
    return await get_recent_matches(20)


@router.get("/api/tracking/champions")
async def tracking_champions():
    from oraclegg.tracker.personal import get_champion_stats
    return await get_champion_stats()


@router.get("/api/tracking/overview")
async def tracking_overview():
    from oraclegg.tracker.personal import get_overall_stats
    return await get_overall_stats()


@router.get("/api/tracking/analysis/{match_id}")
async def match_analysis(match_id: str):
    """Get AI analysis for a specific match."""
    from oraclegg.tracker.ai_analysis import get_or_generate_analysis
    result = await get_or_generate_analysis(match_id)
    if not result:
        return {"error": "Match not found"}
    return result


@router.post("/api/tracking/analyze-all")
async def analyze_all_matches():
    """Generate analysis for all matches without one."""
    from oraclegg.tracker.ai_analysis import generate_all_analyses
    count = await generate_all_analyses()
    return {"analyzed": count}
