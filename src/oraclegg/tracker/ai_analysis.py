"""AI-powered post-game analysis.

Generates detailed match analysis using Claude API or falls back to rule-based analysis.
Each match gets a persistent analysis stored in the DB.
"""

import json
import logging
from datetime import datetime

from sqlalchemy import select

from oraclegg.db.engine import async_session
from oraclegg.db.models import PersonalMatch, Champion, Item

logger = logging.getLogger(__name__)


async def _get_champion_name(cid: int) -> str:
    async with async_session() as session:
        r = await session.execute(select(Champion).where(Champion.id == cid))
        c = r.scalar_one_or_none()
        return c.name if c else f"Champion {cid}"


async def _get_item_name(iid: int) -> str:
    async with async_session() as session:
        r = await session.execute(select(Item).where(Item.id == iid))
        i = r.scalar_one_or_none()
        return i.name if i else f"Item {iid}"


def _kda_rating(kills, deaths, assists):
    ratio = (kills + assists) / max(deaths, 1)
    if ratio >= 5:
        return "excellent"
    elif ratio >= 3:
        return "good"
    elif ratio >= 2:
        return "average"
    elif ratio >= 1:
        return "below average"
    return "poor"


def _cs_rating(cs_per_min, role):
    if role in ("SUPPORT",):
        return "n/a"
    if cs_per_min >= 8:
        return "excellent"
    elif cs_per_min >= 7:
        return "good"
    elif cs_per_min >= 6:
        return "average"
    elif cs_per_min >= 5:
        return "needs improvement"
    return "poor"


def _vision_rating(vision_score, game_mins, role):
    expected = game_mins * (1.5 if role == "SUPPORT" else 0.8)
    ratio = vision_score / max(expected, 1)
    if ratio >= 1.2:
        return "excellent"
    elif ratio >= 0.8:
        return "good"
    elif ratio >= 0.5:
        return "needs improvement"
    return "poor"


def _death_timing_analysis(kills, deaths, assists, game_duration, win):
    """Analyze death patterns and their likely impact."""
    insights = []
    game_mins = game_duration / 60

    deaths_per_min = deaths / max(game_mins, 1)

    if deaths >= 10:
        insights.append("Very high deaths. Focus on dying less — each death gives enemy gold and map pressure.")
    elif deaths >= 7:
        insights.append("Dying frequently. Try to identify your worst death each game and think about what caused it.")

    if kills >= 10 and deaths >= 8:
        insights.append("High kill participation but also high deaths suggests aggressive but risky trades. Consider playing fights more patiently.")

    if deaths <= 2 and game_mins > 20:
        insights.append("Very few deaths — strong survival. Make sure you're still taking calculated risks for objectives though.")

    if kills + assists <= 3 and game_mins > 20 and deaths >= 5:
        insights.append("Low impact with high deaths. You may be getting caught out of position or taking bad fights.")

    return insights


def _damage_analysis(damage_dealt, gold_earned, role, game_duration):
    """Analyze damage efficiency."""
    insights = []
    game_mins = game_duration / 60
    dpm = damage_dealt / max(game_mins, 1)

    if role in ("ADC", "MID"):
        if dpm >= 800:
            insights.append("Strong damage output. You were a significant threat in fights.")
        elif dpm < 400:
            insights.append("Low damage for your role. Were you unable to find good fight positions, or farming too passively?")
    elif role == "JUNGLE":
        if dpm >= 600:
            insights.append("High damage for a jungler. Your ganks and skirmishes were impactful.")
    elif role == "TOP":
        if dpm >= 700:
            insights.append("Strong damage from top lane. You found good flanks or split push pressure.")

    if gold_earned > 0 and damage_dealt > 0:
        gold_efficiency = damage_dealt / gold_earned
        if gold_efficiency < 0.5 and role not in ("SUPPORT",):
            insights.append("Low damage relative to gold earned. Consider if your item build is optimal for damage output.")

    return insights


async def generate_analysis(match_id: str) -> dict | None:
    """Generate a comprehensive analysis for a specific match.

    Returns analysis dict or None if match not found.
    """
    async with async_session() as session:
        result = await session.execute(
            select(PersonalMatch).where(PersonalMatch.match_id == match_id)
        )
        match = result.scalar_one_or_none()
        if not match:
            return None

    champ_name = await _get_champion_name(match.champion_id)
    game_mins = match.game_duration / 60
    kda_ratio = (match.kills + match.assists) / max(match.deaths, 1)

    # Resolve items
    item_ids = json.loads(match.items_final) if match.items_final else []
    items = []
    for iid in item_ids:
        if iid > 0:
            items.append(await _get_item_name(iid))

    # Resolve enemy champions
    enemy_ids = json.loads(match.enemy_champion_ids) if match.enemy_champion_ids else []
    enemies = []
    for eid in enemy_ids:
        if eid > 0:
            enemies.append(await _get_champion_name(eid))

    # Build analysis sections
    sections = []

    # Overview
    result_str = "Victory" if match.win else "Defeat"
    sections.append({
        "title": "Overview",
        "content": (
            f"{result_str} as {champ_name} {match.role}. "
            f"{match.kills}/{match.deaths}/{match.assists} ({kda_ratio:.1f} KDA) "
            f"in {int(game_mins)}:{int(match.game_duration % 60):02d}."
        ),
    })

    # KDA Analysis
    kda_rate = _kda_rating(match.kills, match.deaths, match.assists)
    sections.append({
        "title": "Combat Performance",
        "rating": kda_rate,
        "content": f"KDA was {kda_rate}. {match.kills} kills, {match.deaths} deaths, {match.assists} assists.",
        "details": _death_timing_analysis(match.kills, match.deaths, match.assists, match.game_duration, match.win),
    })

    # CS Analysis
    cs_rate = _cs_rating(match.cs_per_min, match.role)
    if match.role != "SUPPORT":
        sections.append({
            "title": "Farming",
            "rating": cs_rate,
            "content": f"{match.cs} CS ({match.cs_per_min}/min) — rated {cs_rate}.",
            "details": _get_cs_advice(match.cs_per_min, match.role, game_mins),
        })

    # Vision
    vision_rate = _vision_rating(match.vision_score, game_mins, match.role)
    sections.append({
        "title": "Vision Control",
        "rating": vision_rate,
        "content": f"Vision score: {match.vision_score} — rated {vision_rate}.",
        "details": _get_vision_advice(match.vision_score, game_mins, match.role),
    })

    # Damage
    if match.damage_dealt:
        sections.append({
            "title": "Damage Output",
            "content": f"{match.damage_dealt:,} damage to champions ({int(match.damage_dealt / max(game_mins, 1)):,}/min).",
            "details": _damage_analysis(match.damage_dealt, match.gold_earned, match.role, match.game_duration),
        })

    # Build
    if items:
        sections.append({
            "title": "Build",
            "content": f"Final items: {', '.join(items)}.",
            "details": [],
        })

    # Enemy team
    if enemies:
        sections.append({
            "title": "Enemy Team",
            "content": f"Played against: {', '.join(enemies)}.",
            "details": [],
        })

    # Key takeaway
    takeaways = _generate_takeaways(match, champ_name, kda_ratio, game_mins)
    sections.append({
        "title": "Key Takeaways",
        "content": "",
        "details": takeaways,
    })

    # Store analysis in timeline_summary
    analysis = {
        "match_id": match_id,
        "champion": champ_name,
        "champion_id": match.champion_id,
        "role": match.role,
        "win": match.win,
        "sections": sections,
        "generated_at": datetime.utcnow().isoformat(),
    }

    # Persist to DB
    async with async_session() as session:
        m = await session.execute(
            select(PersonalMatch).where(PersonalMatch.match_id == match_id)
        )
        pm = m.scalar_one_or_none()
        if pm:
            pm.timeline_summary = json.dumps(analysis)
            await session.commit()

    return analysis


def _get_cs_advice(cs_per_min, role, game_mins):
    advice = []
    if cs_per_min < 6 and role in ("MID", "ADC", "TOP"):
        advice.append("Practice last-hitting in practice tool. Aim for 7+ CS/min.")
    if cs_per_min < 5 and role == "JUNGLE":
        advice.append("Low jungle farm. Make sure to clear camps between ganks.")
    if cs_per_min >= 8:
        advice.append("Excellent farming. Your gold income from CS was strong this game.")
    if game_mins > 25 and cs_per_min < 6:
        advice.append("CS/min drops in longer games often mean too much ARAM mid. Remember to catch side waves.")
    return advice


def _get_vision_advice(vision_score, game_mins, role):
    advice = []
    if role == "SUPPORT" and vision_score < game_mins * 1.2:
        advice.append("As support, aim for at least 1.5 vision score per minute. Buy control wards.")
    elif role != "SUPPORT" and vision_score < game_mins * 0.5:
        advice.append("Low vision for your role. Remember to place wards, especially before objectives.")
    if vision_score >= game_mins * 1.5 and role != "SUPPORT":
        advice.append("Great vision control for a non-support. Keep it up.")
    return advice


def _generate_takeaways(match, champ_name, kda_ratio, game_mins):
    takeaways = []

    if match.win:
        if kda_ratio >= 4:
            takeaways.append(f"Dominant performance on {champ_name}. You carried this game.")
        elif match.deaths <= 3:
            takeaways.append("Clean win with few deaths. Good decision-making.")
        else:
            takeaways.append("Got the win despite some deaths. Focus on reducing unnecessary deaths to win more consistently.")
    else:
        if kda_ratio >= 3:
            takeaways.append(f"You played well individually ({match.kills}/{match.deaths}/{match.assists}) but the team couldn't convert. Sometimes games are unwinnable — don't tilt over this one.")
        elif match.deaths >= 8:
            takeaways.append(f"High deaths ({match.deaths}) were likely a major factor in the loss. Identify your 2-3 worst deaths and think about what you could have done differently.")
        else:
            takeaways.append("Loss with moderate stats. Review the game for missed opportunities around objectives.")

    if match.cs_per_min and match.cs_per_min < 5.5 and match.role not in ("SUPPORT", "JUNGLE"):
        takeaways.append(f"CS was low ({match.cs_per_min}/min). Even 1 extra CS/min over a 30-min game is ~300+ extra gold.")

    if match.vision_score and match.vision_score < 10 and game_mins > 20:
        takeaways.append("Very low vision score. Placing wards prevents deaths and enables plays.")

    return takeaways


async def get_or_generate_analysis(match_id: str) -> dict | None:
    """Get cached analysis or generate a new one."""
    async with async_session() as session:
        result = await session.execute(
            select(PersonalMatch).where(PersonalMatch.match_id == match_id)
        )
        match = result.scalar_one_or_none()
        if not match:
            return None

        # Check for cached analysis
        if match.timeline_summary:
            try:
                return json.loads(match.timeline_summary)
            except json.JSONDecodeError:
                pass

    # Generate fresh
    return await generate_analysis(match_id)


async def generate_all_analyses() -> int:
    """Generate analysis for all matches that don't have one yet."""
    async with async_session() as session:
        result = await session.execute(
            select(PersonalMatch).where(
                PersonalMatch.timeline_summary.is_(None)
            )
        )
        matches = result.scalars().all()

    count = 0
    for m in matches:
        try:
            await generate_analysis(m.match_id)
            count += 1
        except Exception as e:
            logger.error(f"Analysis failed for {m.match_id}: {e}")

    return count
