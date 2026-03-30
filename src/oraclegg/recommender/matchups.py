"""Matchup-specific knowledge base.

Curated advice for specific champion vs champion matchups.
This is game knowledge that can't be derived from API data.
"""

# Format: (your_champ, enemy_champ): [list of tips]
# Tips are shown during champ select and early game
MATCHUP_TIPS: dict[tuple[str, str], list[str]] = {
    # ─── Annie matchups ──────────────────────────────────
    ("Annie", "Zed"): [
        "Rush Zhonya's after first item. Hold stun for his ult shadow.",
        "Pre-6 you win trades hard. Zone him off CS with stun threat.",
        "After 6, save stun for when he ults. Tibbers + stun when he appears behind you.",
    ],
    ("Annie", "Yasuo"): [
        "Your stun goes through his Wind Wall. Abuse this.",
        "Short trades with Q are good. Don't let him dash through your wave.",
        "At 6, Tibbers + Flash is almost guaranteed kill if he has no passive shield.",
    ],
    ("Annie", "Fizz"): [
        "Play aggressive pre-6. Your range advantage is huge.",
        "After 6, bait his E before using Tibbers. If he E's your ult it's wasted.",
        "Banshee's Veil is great to block his ult.",
    ],
    ("Annie", "Sylas"): [
        "He steals Tibbers — but your version is better because of your passive stun.",
        "Short trade with Q+W, don't let him sustain with W.",
    ],
    ("Annie", "Katarina"): [
        "Hold stun for her ult. One stun cancels her entire combo.",
        "Stand away from her daggers. If she jumps on a dagger, stun immediately.",
    ],

    # ─── Riven matchups ──────────────────────────────────
    ("Riven", "Renekton"): [
        "His W stun breaks your combo. Bait it first, then go in.",
        "Short trade: Q+W, E out before he can W you.",
        "After 6, all-in only if his fury is low. Full fury W+Q is devastating.",
    ],
    ("Riven", "Darius"): [
        "Never let him get 5 passive stacks. Short trades only.",
        "Q3 + W to stun, then E away. Don't extended trade.",
        "Ignite is mandatory. Kill pressure at 6 if you dodge his Q outer ring.",
    ],
    ("Riven", "Malphite"): [
        "He wins by stacking armor. You need to snowball early.",
        "Trade when his passive shield is down (10 sec CD).",
        "Consider Black Cleaver rush for armor shred.",
    ],
    ("Riven", "Garen"): [
        "Trade when his Q is on cooldown. His silence cancels your combo.",
        "Don't let him regen with passive. Keep poking.",
        "At 6, bait his ult by staying above 30% HP then all-in.",
    ],
    ("Riven", "Fiora"): [
        "She parries your W stun. Bait it by Q3'ing first, delay W.",
        "Short trades win early. Don't let her proc all 4 vitals.",
    ],

    # ─── Viego matchups ──────────────────────────────────
    ("Viego", "LeeSin"): [
        "He's stronger early. Avoid 1v1 until you have Kraken Slayer.",
        "Ward his jungle to track him. Counter-gank is better than fighting him at scuttle.",
    ],
    ("Viego", "Warwick"): [
        "He outsustains you early. Don't fight him near half HP (his W movespeed).",
        "Build Executioner's early. His healing is his entire kit.",
        "You outscale hard. Farm and scale, fight after 2 items.",
    ],
    ("Viego", "Graves"): [
        "He wins early skirmishes. Avoid contesting first scuttle.",
        "Your W stun is key — hit it and you can trade back.",
        "After Kraken + Collector, you can 1v1 him.",
    ],
    ("Viego", "Kindred"): [
        "Contest her marks when possible. Denying marks cripples her scaling.",
        "In fights, save your possession for after her ult ends.",
    ],
    ("Viego", "Sejuani"): [
        "She can't kill you but she can lock you down for her team.",
        "Invade early — you win 1v1. She needs lanes to gank.",
        "Build Merc Treads for tenacity against her CC chain.",
    ],
}

# Generic role-based tips
ROLE_TIPS: dict[str, list[str]] = {
    "JUNGLE": [
        "Track enemy jungler by watching which lanes have priority.",
        "Clear efficiently: always be moving toward your next gank or objective.",
        "After a successful gank, check if dragon or herald is available.",
    ],
    "MID": [
        "Shove and roam after getting a kill or forcing a back.",
        "Ward river at 3:00 — first gank timing for most junglers.",
        "Ping missing when your laner disappears, even for 5 seconds.",
    ],
    "TOP": [
        "Freeze near your tower when ahead to deny CS safely.",
        "TP bot for dragon fights if you have teleport.",
        "Track enemy jungler — top lane is the longest lane to escape ganks.",
    ],
    "ADC": [
        "Position behind your frontline in teamfights. Never in front.",
        "Focus whoever is closest, not whoever is lowest. Don't tunnel.",
        "Auto-attack between ability casts (auto-weaving).",
    ],
    "SUPPORT": [
        "Ward river and tri-bush before dragon spawns (30 sec early).",
        "Roam mid after pushing bot wave under enemy tower.",
        "Sweep enemy vision around objectives 60 seconds before they spawn.",
    ],
}


def get_matchup_tips(my_champ: str, enemy_champ: str) -> list[str]:
    """Get tips for a specific matchup."""
    return MATCHUP_TIPS.get((my_champ, enemy_champ), [])


def get_role_tips(role: str) -> list[str]:
    """Get general tips for a role."""
    return ROLE_TIPS.get(role, [])


def get_all_matchup_tips(my_champ: str, enemy_champs: list[str]) -> list[dict]:
    """Get matchup tips for all enemy champions."""
    results = []
    for enemy in enemy_champs:
        tips = get_matchup_tips(my_champ, enemy)
        if tips:
            results.append({"enemy": enemy, "tips": tips})
    return results
