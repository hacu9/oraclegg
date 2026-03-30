"""Matchup-specific knowledge base.

Curated champion vs champion advice that can't be derived from stats alone.
This is the "Annie vs Zed → rush Zhonya's" type knowledge.
"""

# Key: (your_champ, enemy_champ) or (your_champ, "*") for general
# Value: list of tips
MATCHUP_TIPS: dict[tuple[str, str], list[str]] = {
    # Annie
    ("Annie", "Zed"): [
        "Rush Zhonya's Hourglass. Use it when Zed ults you — his ult damage pops on nothing.",
        "Save your stun for when Zed comes out of his ult shadow. He always appears behind you.",
        "Pre-6 you win trades hard. Punish him before he has kill pressure.",
    ],
    ("Annie", "Yasuo"): [
        "Your Q goes through his Wind Wall. Poke with Q freely.",
        "Wait for him to dash onto you, then Tibbers stun. Don't waste ult into his wall.",
        "Tabis reduce his auto damage significantly if you're struggling.",
    ],
    ("Annie", "Fizz"): [
        "Play aggressive levels 1-5. Once he hits 6 his all-in beats yours if he dodges your stun with E.",
        "Hold stun when his E is up. Bait it out first, then combo.",
        "Banshee's Veil blocks his ult fish. Consider it 2nd or 3rd item.",
    ],
    ("Annie", "Syndra"): [
        "She outranges you. Use minions to block her Q-E stun combo.",
        "Flash + Tibbers is your win condition. Wait for her to use E defensively, then go in.",
    ],
    # Riven
    ("Riven", "Darius"): [
        "Short trades only. Q-W-auto then E out. Never let him get 5 stacks of bleed.",
        "Bait his Q by walking in and out. If he misses outer Q, all-in immediately.",
        "After 6, you can all-in if you dodge his Q outer edge with your dashes.",
    ],
    ("Riven", "Renekton"): [
        "Respect his empowered W stun. Don't trade when he has 50+ fury.",
        "You outscale hard. Play safe until you have 2 items, then you win 1v1.",
        "E his W stun to shield the damage, then trade back.",
    ],
    ("Riven", "Malphite"): [
        "You can't kill him after he gets armor. Roam mid and bot instead.",
        "Early game before his first armor item, you can trade aggressively.",
        "Consider Black Cleaver to shred his armor.",
    ],
    ("Riven", "Garen"): [
        "Trade when his Q is on cooldown. Bait it by walking up, E back, then re-engage.",
        "Don't let him regen with passive. Keep poking to prevent his health from coming back.",
    ],
    # Viego
    ("Viego", "LeeSin"): [
        "His early dueling is stronger. Farm and avoid 1v1 until you have BotRK or Kraken.",
        "Counter-gank his ganks rather than forcing your own early.",
        "After 6, you can match him. Possess a tanky champ in fights for survivability.",
    ],
    ("Viego", "Graves"): [
        "He wins early skirmishes with his burst. Don't contest crabs if he's nearby.",
        "Your sustain from passive beats him in extended fights. Look for longer trades.",
    ],
    ("Viego", "Warwick"): [
        "He's stronger 1v1 early due to healing. Don't duel him until you have anti-heal.",
        "His W blood trail reveals low-HP targets. Be careful when low in your jungle.",
    ],
    # General tips for common matchup archetypes
    ("*", "Teemo"): [
        "Buy Oracle Lens to clear his shrooms. Walk predictable paths less.",
        "All-in him when his blind is on cooldown. Don't auto-trade into his blind.",
    ],
    ("*", "Vayne"): [
        "Don't fight her near walls — her E stun does massive damage.",
        "She's weak early. Punish before she gets 2+ items.",
        "Group and burst her in teamfights. She struggles against hard CC.",
    ],
    ("*", "Yuumi"): [
        "Focus whoever Yuumi is attached to. Bursting the host forces Yuumi to detach.",
        "Build Grievous Wounds — Yuumi heals a lot.",
    ],
}

# General role-based tips
ROLE_TIPS: dict[str, list[str]] = {
    "TOP": [
        "Track enemy jungler before trading aggressively. Ward river at 3:00.",
        "Freeze the wave near your tower if you're behind. Let them overextend.",
        "TP bot for dragon fights if you have lane priority.",
    ],
    "JUNGLE": [
        "Full clear is almost always better than forcing a bad level 3 gank.",
        "Track the enemy jungler by watching which lanes are pushing.",
        "Gank the lane that has CC first — it's the highest success rate.",
    ],
    "MID": [
        "Shove and roam after level 6 if you have kill pressure on side lanes.",
        "Place a control ward in the pixel brush for river vision.",
        "Respect fog of war — if you don't see the enemy jungler, play safe.",
    ],
    "ADC": [
        "Focus on CS over kills in lane. 15 CS = 1 kill worth of gold.",
        "Stay behind your support in lane. Don't walk up alone to auto.",
        "In teamfights, hit whoever is closest to you safely. Don't tunnel on the backline.",
    ],
    "SUPPORT": [
        "Ward enemy jungle entrances for your jungler's safety.",
        "Roam mid after a successful bot lane recall. Surprise the enemy mid.",
        "Peel for your ADC in teamfights if they're your win condition.",
    ],
}


def get_matchup_tips(your_champ: str, enemy_champ: str) -> list[str]:
    """Get tips for a specific matchup. Falls back to general tips."""
    tips = MATCHUP_TIPS.get((your_champ, enemy_champ), [])
    if not tips:
        tips = MATCHUP_TIPS.get(("*", enemy_champ), [])
    return tips


def get_role_tips(role: str) -> list[str]:
    return ROLE_TIPS.get(role, [])
