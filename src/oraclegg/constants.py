"""Shared constants used across OracleGG modules.

Single source of truth for champion icon mappings, role normalization,
summoner spell names, and other shared lookups.
"""

# Champions whose Live Client name differs from Data Dragon key
CHAMP_ICON_MAP = {
    # Spaces / special characters
    "Aurelion Sol": "AurelionSol",
    "Dr. Mundo": "DrMundo",
    "Jarvan IV": "JarvanIV",
    "Lee Sin": "LeeSin",
    "Master Yi": "MasterYi",
    "Miss Fortune": "MissFortune",
    "Tahm Kench": "TahmKench",
    "Twisted Fate": "TwistedFate",
    "Xin Zhao": "XinZhao",
    # Apostrophes
    "Kai'Sa": "Kaisa",
    "Kha'Zix": "Khazix",
    "Bel'Veth": "Belveth",
    "Vel'Koz": "Velkoz",
    "Kog'Maw": "KogMaw",
    "Cho'Gath": "Chogath",
    "Rek'Sai": "RekSai",
    "K'Sante": "KSante",
    # Renamed / special
    "Wukong": "MonkeyKing",
    "Renata Glasc": "Renata",
    "Nunu & Willump": "Nunu",
    "LeBlanc": "Leblanc",
}

# Role normalization: Riot API → standard display names
ROLE_MAP = {
    "TOP": "TOP",
    "JUNGLE": "JUNGLE",
    "MIDDLE": "MID",
    "BOTTOM": "ADC",
    "UTILITY": "SUPPORT",
    "": "UNKNOWN",
}

# Standard role order for lane matchup display
ROLE_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]

# Summoner spell ID → display name
SUMMONER_SPELL_NAMES = {
    1: "Cleanse",
    3: "Exhaust",
    4: "Flash",
    6: "Ghost",
    7: "Heal",
    11: "Smite",
    12: "Teleport",
    14: "Ignite",
    21: "Barrier",
    32: "Mark",
}

# Summoner spell display name → DDragon asset key
SUMMONER_SPELL_KEYS = {
    "Flash": "SummonerFlash",
    "Ignite": "SummonerDot",
    "Teleport": "SummonerTeleport",
    "Smite": "SummonerSmite",
    "Exhaust": "SummonerExhaust",
    "Heal": "SummonerHeal",
    "Ghost": "SummonerHaste",
    "Cleanse": "SummonerBoost",
    "Barrier": "SummonerBarrier",
    "Mark": "SummonerSnowball",
}


def champ_icon_key(name: str) -> str:
    """Get the DDragon icon key for a champion name."""
    return CHAMP_ICON_MAP.get(name, name)


def normalize_role(role: str) -> str:
    """Normalize a Riot API role to standard display name."""
    return ROLE_MAP.get(role, role)


def spell_name(spell_id: int) -> str:
    """Get display name for a summoner spell ID."""
    return SUMMONER_SPELL_NAMES.get(spell_id, f"Spell {spell_id}")
