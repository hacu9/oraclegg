"""Boot recommendation rules.

Analyzes enemy team composition to recommend optimal boots.
"""

# Boot IDs and names
BOOTS = {
    3006: "Berserker's Greaves",   # Attack speed
    3009: "Boots of Swiftness",     # MS + slow resist
    3020: "Sorcerer's Shoes",       # Magic pen
    3047: "Plated Steelcaps",       # Armor + auto reduction
    3111: "Mercury's Treads",       # MR + tenacity
    3117: "Mobility Boots",         # Roaming
    3158: "Ionian Boots of Lucidity",  # CDR
}

# CC abilities by champion (champions with meaningful hard CC)
HARD_CC_CHAMPS = {
    "Leona", "Nautilus", "Thresh", "Amumu", "Sejuani", "Alistar", "Rell",
    "Maokai", "Zac", "Ornn", "Morgana", "Lux", "Ahri", "Ashe", "Veigar",
    "TwistedFate", "Elise", "Rammus", "Skarner", "Malzahar", "Lissandra",
    "Annie", "Renekton", "Pantheon", "Rakan", "Galio", "Cassiopeia",
    "Syndra", "Braum", "Blitzcrank", "Pyke", "Kennen", "Neeko",
    "Lillia", "Yone", "Aurora", "Hwei",
}

# Auto-attack reliant champions
AUTO_ATTACK_CHAMPS = {
    "Vayne", "Jinx", "KogMaw", "Twitch", "Aphelios", "Zeri", "Kalista",
    "Tristana", "Caitlyn", "Draven", "Jhin", "MissFortune", "Sivir",
    "Tryndamere", "MasterYi", "Jax", "Fiora", "Irelia", "Yasuo", "Yone",
    "Kindred", "Belveth", "Briar", "Warwick", "Gwen", "Kayle",
    "Viego", "Nilah",
}


def recommend_boots(
    my_champion: str,
    my_role: str,
    enemy_champs: list[str],
    enemy_items: dict[str, set[int]],  # champ_name -> set of item IDs
) -> dict:
    """Recommend boots based on enemy team composition.

    Returns dict with recommended boot, reasoning, and alternatives.
    """
    # Count enemy damage types and CC
    ap_threats = 0
    ad_threats = 0
    cc_count = 0
    auto_attackers = 0

    ap_item_ids = {3089, 4645, 4646, 6653, 6655, 3152, 3115, 3116, 3118, 3135}
    ad_item_ids = {3031, 6672, 6676, 3036, 6333, 6692, 3078, 6631, 3033, 3094}
    lethality_ids = {6676, 6697, 6698, 6694}

    for champ in enemy_champs:
        items = enemy_items.get(champ, set())

        if items & ap_item_ids:
            ap_threats += 1
        if items & ad_item_ids:
            ad_threats += 1
        if items & lethality_ids:
            ad_threats += 1  # Extra weight for lethality
        if champ in HARD_CC_CHAMPS:
            cc_count += 1
        if champ in AUTO_ATTACK_CHAMPS:
            auto_attackers += 1

    # Fallback: count by champion archetype if no items visible yet
    if ap_threats == 0 and ad_threats == 0:
        # Use champion tags as proxy
        for champ in enemy_champs:
            if champ in AUTO_ATTACK_CHAMPS:
                ad_threats += 1
                auto_attackers += 1
            elif champ in HARD_CC_CHAMPS:
                ap_threats += 0.5  # Might be AP, might be tank

    # Decision logic
    reasons = []
    recommendation = None
    alternatives = []

    # Heavy CC (3+) -> Mercury's Treads
    if cc_count >= 3:
        recommendation = 3111
        reasons.append(f"Enemy has {cc_count} hard CC champions — tenacity is critical")
        if ap_threats >= 2:
            reasons.append(f"Also provides MR against {ap_threats} AP threats")
        alternatives = [3047, 3009]

    # Heavy auto-attackers (3+) -> Plated Steelcaps
    elif auto_attackers >= 3:
        recommendation = 3047
        reasons.append(f"Enemy has {auto_attackers} auto-attack champions — reduces their damage by 12%")
        alternatives = [3111, 3009]

    # Heavy AP (3+) -> Mercury's Treads
    elif ap_threats >= 3:
        recommendation = 3111
        reasons.append(f"Enemy has {ap_threats} AP threats — MR + tenacity")
        alternatives = [3009]

    # Heavy AD (3+) -> Plated Steelcaps
    elif ad_threats >= 3:
        recommendation = 3047
        reasons.append(f"Enemy has {ad_threats} AD threats — armor + auto reduction")
        alternatives = [3111]

    # Mixed with CC -> Mercury's Treads
    elif cc_count >= 2 and ap_threats >= 1:
        recommendation = 3111
        reasons.append(f"{cc_count} CC threats + AP damage — tenacity helps survive burst combos")
        alternatives = [3047, 3158]

    # Mixed with auto-attackers -> Steelcaps
    elif auto_attackers >= 2 and ad_threats >= 2:
        recommendation = 3047
        reasons.append(f"Multiple auto-attackers with AD builds")
        alternatives = [3111, 3158]

    # Role-specific defaults
    else:
        if my_role in ("MID",) and my_champion not in AUTO_ATTACK_CHAMPS:
            recommendation = 3020
            reasons.append("Balanced enemy comp — Sorc Shoes give you damage to carry")
            alternatives = [3111, 3158]
        elif my_role in ("ADC",):
            recommendation = 3006
            reasons.append("Balanced enemy comp — Berserker's for DPS")
            alternatives = [3047, 3009]
        elif my_role in ("SUPPORT",):
            recommendation = 3158
            reasons.append("CDR boots for more ability uptime on support")
            alternatives = [3117, 3111]
        elif my_role in ("JUNGLE",):
            recommendation = 3158 if cc_count <= 1 else 3111
            reasons.append("CDR for faster clears and more ganks" if cc_count <= 1 else "Tenacity for safer ganks into CC")
            alternatives = [3047, 3111] if cc_count <= 1 else [3047, 3158]
        else:
            recommendation = 3047 if ad_threats > ap_threats else 3111
            reasons.append(f"{'AD' if ad_threats > ap_threats else 'AP'}-leaning enemy comp")
            alternatives = [3111 if ad_threats > ap_threats else 3047, 3158]

    return {
        "boot_id": recommendation,
        "boot_name": BOOTS.get(recommendation, "Unknown"),
        "reasons": reasons,
        "alternatives": [
            {"id": b, "name": BOOTS.get(b, "Unknown")}
            for b in alternatives if b != recommendation
        ],
        "enemy_breakdown": {
            "ap_threats": ap_threats,
            "ad_threats": ad_threats,
            "cc_count": cc_count,
            "auto_attackers": auto_attackers,
        },
    }
