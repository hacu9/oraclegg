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
            if r.status_code == 401:
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
