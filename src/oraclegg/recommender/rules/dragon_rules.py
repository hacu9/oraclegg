"""Dragon value analysis.

Evaluates how valuable each dragon soul/buff is for your team vs enemy team.
"""

# Dragon souls and their effects
DRAGON_INFO = {
    "Infernal": {
        "buff": "AP and AD increase",
        "soul": "AoE burn on abilities and autos",
    },
    "Mountain": {
        "buff": "Armor and MR increase",
        "soul": "Shield after not taking damage",
    },
    "Ocean": {
        "buff": "Health regen",
        "soul": "Heal on damage dealt",
    },
    "Cloud": {
        "buff": "Movement speed",
        "soul": "Ultimate CDR + MS burst after ult",
    },
    "Hextech": {
        "buff": "Attack speed and ability haste",
        "soul": "Chain lightning on-hit",
    },
    "Chemtech": {
        "buff": "Tenacity and heal/shield power",
        "soul": "Damage boost when low HP + brief revive",
    },
}

# Champion affinities with dragon types
SCALING_CHAMPS = {
    "Kayle", "Kassadin", "Vayne", "Jinx", "KogMaw", "Viktor", "Azir",
    "Veigar", "Vladimir", "MasterYi", "Nasus", "Jax",
}
BURST_CHAMPS = {
    "Zed", "Talon", "Akali", "Katarina", "Leblanc", "Annie", "Syndra",
    "Veigar", "Lux", "Ahri", "Diana",
}
HEALING_CHAMPS = {
    "Aatrox", "Warwick", "Sylas", "Vladimir", "Soraka", "Yuumi",
    "DrMundo", "Fiora", "Irelia", "Swain", "Illaoi", "Briar",
}
ULT_RELIANT_CHAMPS = {
    "Malphite", "Amumu", "Diana", "Orianna", "Kennen", "MissFortune",
    "Karthus", "Skarner", "Galio", "Seraphine", "Annie",
}
AUTO_ATTACK_CHAMPS = {
    "Vayne", "Jinx", "KogMaw", "Twitch", "Aphelios", "Jax",
    "Tryndamere", "MasterYi", "Kindred", "Yasuo", "Yone", "Viego",
    "Kayle", "Gwen",
}


def evaluate_dragon(
    dragon_type: str,
    ally_champs: list[str],
    enemy_champs: list[str],
) -> dict:
    """Evaluate how valuable a dragon is for both teams.

    Returns dict with value ratings and reasoning.
    """
    info = DRAGON_INFO.get(dragon_type, {})
    if not info:
        return {"type": dragon_type, "priority": "unknown", "reason": "Unknown dragon type"}

    ally_value = 0
    enemy_value = 0
    reasons = []

    if dragon_type == "Infernal":
        # Good for everyone, especially scaling/burst
        ally_scaling = sum(1 for c in ally_champs if c in SCALING_CHAMPS or c in BURST_CHAMPS)
        enemy_scaling = sum(1 for c in enemy_champs if c in SCALING_CHAMPS or c in BURST_CHAMPS)
        ally_value = 3 + ally_scaling
        enemy_value = 3 + enemy_scaling
        reasons.append("Infernal is universally strong — flat damage increase")
        if ally_scaling >= 2:
            reasons.append(f"Extra valuable for your {ally_scaling} scaling/burst champions")

    elif dragon_type == "Mountain":
        # Great for teams that want to frontline/survive
        ally_tanks = sum(1 for c in ally_champs if c not in BURST_CHAMPS and c not in AUTO_ATTACK_CHAMPS)
        enemy_burst = sum(1 for c in enemy_champs if c in BURST_CHAMPS)
        ally_value = 3 + (1 if enemy_burst >= 2 else 0)
        enemy_value = 3
        if enemy_burst >= 2:
            reasons.append(f"Mountain soul counters enemy burst ({enemy_burst} burst champs) — shield absorbs their combo")
            ally_value += 1
        else:
            reasons.append("Mountain provides tankiness — solid but not game-changing for this matchup")

    elif dragon_type == "Ocean":
        # Great for sustain/poke comps, insane for healing champs
        ally_healers = sum(1 for c in ally_champs if c in HEALING_CHAMPS)
        enemy_healers = sum(1 for c in enemy_champs if c in HEALING_CHAMPS)
        ally_value = 3 + ally_healers
        enemy_value = 3 + enemy_healers
        if ally_healers >= 1:
            reasons.append(f"Ocean amplifies your healing champions — high value")
        if enemy_healers >= 2:
            reasons.append(f"Enemy has {enemy_healers} healing champs — denying Ocean from them is critical")
            enemy_value += 1

    elif dragon_type == "Cloud":
        # Great for ult-reliant teams
        ally_ult = sum(1 for c in ally_champs if c in ULT_RELIANT_CHAMPS)
        enemy_ult = sum(1 for c in enemy_champs if c in ULT_RELIANT_CHAMPS)
        ally_value = 2 + ally_ult
        enemy_value = 2 + enemy_ult
        if ally_ult >= 2:
            reasons.append(f"Cloud soul is great — your team has {ally_ult} ult-reliant champs (more ult uptime)")
        elif ally_ult == 0:
            reasons.append("Cloud is the weakest dragon for your comp — MS is nice but not game-changing")
        if enemy_ult >= 2:
            reasons.append(f"Deny it — enemy has {enemy_ult} champs that love ult CDR")

    elif dragon_type == "Hextech":
        # Great for auto-attackers and ability spammers
        ally_aa = sum(1 for c in ally_champs if c in AUTO_ATTACK_CHAMPS)
        enemy_aa = sum(1 for c in enemy_champs if c in AUTO_ATTACK_CHAMPS)
        ally_value = 3 + ally_aa
        enemy_value = 3 + enemy_aa
        if ally_aa >= 2:
            reasons.append(f"Hextech soul chain lightning + AS is great for your {ally_aa} auto-attackers")
        else:
            reasons.append("Hextech provides ability haste and AS — decent for everyone")

    elif dragon_type == "Chemtech":
        # Great for everyone, revive is broken
        ally_value = 4
        enemy_value = 4
        reasons.append("Chemtech soul is one of the strongest — the revive can turn fights")
        ally_divers = sum(1 for c in ally_champs if c in BURST_CHAMPS or c in AUTO_ATTACK_CHAMPS)
        if ally_divers >= 2:
            reasons.append("Extra strong on your team — divers and assassins get a second chance after going in")

    # Determine priority
    net_value = ally_value - enemy_value
    if ally_value >= 5 or (net_value >= 2):
        priority = "high"
    elif ally_value >= 3:
        priority = "medium"
    else:
        priority = "low"

    # Should we contest or concede?
    if enemy_value >= 5 and ally_value < 3:
        contest = "Contest to DENY — this dragon benefits the enemy more than you"
    elif ally_value >= 5:
        contest = "Must take — this dragon is extremely valuable for your team"
    elif ally_value >= 3:
        contest = "Worth fighting for if you have numbers advantage"
    else:
        contest = "Low priority — trade for tower/herald if possible"

    return {
        "type": dragon_type,
        "buff": info["buff"],
        "soul": info["soul"],
        "priority": priority,
        "ally_value": ally_value,
        "enemy_value": enemy_value,
        "contest": contest,
        "reasons": reasons,
    }
