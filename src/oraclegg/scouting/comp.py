"""Team composition classifier.

Classifies a team of 5 champions into archetypes like heavy_ap, engage, poke, etc.
Used by both the scouting module (live) and the pipeline (historical).
"""

import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from oraclegg.db.models import Champion

logger = logging.getLogger(__name__)

# Champion archetype overrides (champion key -> set of traits)
# These supplement the tag-based classification for accuracy
CHAMPION_TRAITS: dict[str, set[str]] = {
    # Poke champions
    "Xerath": {"poke", "ap"},
    "Ziggs": {"poke", "ap"},
    "Zoe": {"poke", "ap"},
    "Jayce": {"poke", "ad"},
    "Varus": {"poke", "ad"},
    "Nidalee": {"poke", "ap"},
    "Velkoz": {"poke", "ap"},
    "Lux": {"poke", "ap"},
    "Ezreal": {"poke", "ad"},
    # Hard engage
    "Malphite": {"engage", "tank", "ap"},
    "Leona": {"engage", "tank"},
    "Amumu": {"engage", "tank", "ap"},
    "Nautilus": {"engage", "tank"},
    "Rakan": {"engage"},
    "Ornn": {"engage", "tank"},
    "Alistar": {"engage", "tank"},
    "Sejuani": {"engage", "tank"},
    "Zac": {"engage", "tank"},
    "Rell": {"engage", "tank"},
    "Maokai": {"engage", "tank"},
    # Split-pushers
    "Fiora": {"split", "ad"},
    "Jax": {"split", "ad"},
    "Tryndamere": {"split", "ad"},
    "Camille": {"split", "ad"},
    "Yorick": {"split", "ad"},
    "Nasus": {"split", "ad", "tank"},
    "Gwen": {"split", "ap"},
    # Hypercarries / scaling
    "Kayle": {"scaling", "ap"},
    "Kassadin": {"scaling", "ap"},
    "Vayne": {"scaling", "ad"},
    "Jinx": {"scaling", "ad"},
    "KogMaw": {"scaling", "ad"},
    "Twitch": {"scaling", "ad"},
    "Aphelios": {"scaling", "ad"},
    "Viktor": {"scaling", "ap"},
    "Azir": {"scaling", "ap"},
    "Veigar": {"scaling", "ap"},
    # Protect-the-carry supports
    "Lulu": {"protect"},
    "Janna": {"protect"},
    "Karma": {"protect", "ap"},
    "Soraka": {"protect"},
    "Yuumi": {"protect"},
    "Ivern": {"protect"},
    # Assassins
    "Zed": {"assassin", "ad"},
    "Talon": {"assassin", "ad"},
    "Khazix": {"assassin", "ad"},
    "Rengar": {"assassin", "ad"},
    "Akali": {"assassin", "ap"},
    "Katarina": {"assassin", "ap"},
    "Leblanc": {"assassin", "ap"},
    "Evelynn": {"assassin", "ap"},
    "Qiyana": {"assassin", "ad"},
    "Naafiri": {"assassin", "ad"},
    # Early game
    "LeeSin": {"early_game", "ad"},
    "Elise": {"early_game", "ap"},
    "Pantheon": {"early_game", "ad"},
    "Draven": {"early_game", "ad"},
    "Renekton": {"early_game", "ad"},
    "Lucian": {"early_game", "ad"},
    # Specific damage types for champs with misleading tags
    "Annie": {"ap"},
    "Riven": {"ad"},
    "Viego": {"ad"},
    "Yone": {"ad"},
    "Yasuo": {"ad"},
    "Irelia": {"ad"},
    "MasterYi": {"ad", "scaling"},
    "Kindred": {"ad"},
}

# Tag to damage type mapping
TAG_DAMAGE_MAP = {
    "Mage": "ap",
    "Assassin": "mixed",  # Could be either
    "Marksman": "ad",
    "Fighter": "ad",
    "Tank": "tank",
    "Support": "utility",
}


def get_champion_traits(champion_key: str, tags: list[str]) -> set[str]:
    """Get traits for a champion, combining overrides with tag-based inference."""
    traits = set()

    # Start with manual overrides
    if champion_key in CHAMPION_TRAITS:
        traits.update(CHAMPION_TRAITS[champion_key])

    # Supplement with tag-based inference
    for tag in tags:
        damage_type = TAG_DAMAGE_MAP.get(tag)
        if damage_type and damage_type != "mixed":
            traits.add(damage_type)
        if tag == "Tank":
            traits.add("tank")

    # Default to AD if no damage type determined
    if not traits.intersection({"ap", "ad"}):
        if "Mage" in tags:
            traits.add("ap")
        else:
            traits.add("ad")

    return traits


def classify_comp(champion_data: list[dict]) -> list[str]:
    """Classify a team comp into archetypes.

    Args:
        champion_data: list of dicts with 'key' and 'tags' fields

    Returns:
        Ranked list of matching archetypes
    """
    all_traits: list[set[str]] = []
    for champ in champion_data:
        traits = get_champion_traits(champ["key"], champ.get("tags", []))
        all_traits.append(traits)

    archetypes = []

    # Count damage types
    ap_count = sum(1 for t in all_traits if "ap" in t)
    ad_count = sum(1 for t in all_traits if "ad" in t)
    tank_count = sum(1 for t in all_traits if "tank" in t)

    # Heavy AP (3+ AP sources)
    if ap_count >= 3:
        archetypes.append("heavy_ap")

    # Heavy AD (3+ AD sources)
    if ad_count >= 3:
        archetypes.append("heavy_ad")

    # Heavy tank (3+ tanks)
    if tank_count >= 3:
        archetypes.append("heavy_tank")

    # Poke comp (2+ poke champions)
    poke_count = sum(1 for t in all_traits if "poke" in t)
    if poke_count >= 2:
        archetypes.append("poke")

    # Engage comp (2+ hard engage)
    engage_count = sum(1 for t in all_traits if "engage" in t)
    if engage_count >= 2:
        archetypes.append("engage")

    # Split-push comp
    split_count = sum(1 for t in all_traits if "split" in t)
    if split_count >= 1:
        archetypes.append("split_push")

    # Protect-the-carry
    protect_count = sum(1 for t in all_traits if "protect" in t)
    scaling_count = sum(1 for t in all_traits if "scaling" in t)
    if protect_count >= 1 and scaling_count >= 1:
        archetypes.append("protect_carry")

    # Assassin comp (2+ assassins)
    assassin_count = sum(1 for t in all_traits if "assassin" in t)
    if assassin_count >= 2:
        archetypes.append("assassin")

    # Early game comp (3+ early game champions)
    early_count = sum(1 for t in all_traits if "early_game" in t)
    if early_count >= 3:
        archetypes.append("early_game")

    # Scaling comp (3+ scaling champions)
    if scaling_count >= 3:
        archetypes.append("scaling")

    # Always include balanced as fallback
    if not archetypes or (ap_count >= 2 and ad_count >= 2):
        archetypes.append("balanced")

    return archetypes


async def classify_comp_from_ids(
    champion_ids: list[int], session: AsyncSession
) -> list[str]:
    """Classify a team comp from champion IDs using DB data."""
    champion_data = []
    for cid in champion_ids:
        result = await session.execute(select(Champion).where(Champion.id == cid))
        champ = result.scalar_one_or_none()
        if champ:
            champion_data.append({
                "key": champ.key,
                "tags": json.loads(champ.tags),
            })
        else:
            champion_data.append({"key": "Unknown", "tags": []})

    return classify_comp(champion_data)
