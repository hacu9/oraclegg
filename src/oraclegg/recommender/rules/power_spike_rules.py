"""Strategic comp analysis rules.

Analyzes team compositions to generate macro strategy tips:
- Scaling vs early game advice
- When to force fights vs when to avoid
- Win condition identification
"""

# Champions that scale hard (win rate increases significantly after 25+ min)
SCALING_CHAMPS = {
    "Kayle", "Kassadin", "Vayne", "Jinx", "KogMaw", "Twitch", "Aphelios",
    "Viktor", "Azir", "Veigar", "Cassiopeia", "Ryze", "Vladimir",
    "MasterYi", "Kindred", "Karthus", "Senna", "Smolder",
    "Nasus", "Jax", "Camille", "Fiora", "Gwen",
    "KaiSa", "Sivir", "Zeri",
}

# Champions that spike early and fall off (win rate decreases after 25+ min)
EARLY_GAME_CHAMPS = {
    "Draven", "Pantheon", "LeeSin", "Elise", "Renekton", "Lucian",
    "Jayce", "Nidalee", "Olaf", "Rek'Sai", "Talon", "Zed",
    "Qiyana", "Naafiri", "Caitlyn",
    "Thresh", "Blitzcrank", "Nautilus",
}

# Strong teamfight champions
TEAMFIGHT_CHAMPS = {
    "Malphite", "Amumu", "Orianna", "Diana", "Kennen", "Wukong",
    "MissFortune", "Seraphine", "Zyra", "Brand", "Rell", "Rakan",
    "Jarvan IV", "Galio",
}

# Split push champions
SPLIT_CHAMPS = {
    "Fiora", "Jax", "Tryndamere", "Camille", "Yorick", "Nasus",
    "Gwen", "Shen",
}


def analyze_team_strategy(
    ally_champs: list[str],
    enemy_champs: list[str],
    game_time: float,
    already_fired: set,
) -> list[tuple[int, str, str]]:
    """Generate strategic tips based on team compositions.

    Returns list of (priority, category, message).
    """
    tips = []
    minutes = game_time / 60

    ally_scaling = sum(1 for c in ally_champs if c in SCALING_CHAMPS)
    ally_early = sum(1 for c in ally_champs if c in EARLY_GAME_CHAMPS)
    enemy_scaling = sum(1 for c in enemy_champs if c in SCALING_CHAMPS)
    enemy_early = sum(1 for c in enemy_champs if c in EARLY_GAME_CHAMPS)
    ally_teamfight = sum(1 for c in ally_champs if c in TEAMFIGHT_CHAMPS)
    ally_split = sum(1 for c in ally_champs if c in SPLIT_CHAMPS)
    enemy_teamfight = sum(1 for c in enemy_champs if c in TEAMFIGHT_CHAMPS)

    # Your team scales, enemy doesn't — be patient
    if ally_scaling >= 2 and enemy_scaling <= 1:
        key = "your_team_scales"
        if key not in already_fired:
            if minutes < 15:
                tips.append((1, "strategy",
                    f"Your team has {ally_scaling} scaling champions. Play safe early, farm up — you outscale them."))
            elif minutes > 25:
                tips.append((1, "strategy",
                    f"Your team has hit its power spike. You outscale — force fights and objectives now."))
            already_fired.add(key)

    # Enemy team scales, yours doesn't — close fast
    if enemy_scaling >= 2 and ally_scaling <= 1:
        key = "enemy_scales"
        if key not in already_fired:
            if minutes < 15:
                tips.append((0, "strategy",
                    f"Enemy has {enemy_scaling} scaling champions. Push your early advantage — close this before 25 min."))
            elif minutes > 25:
                tips.append((0, "strategy",
                    f"Enemy is hitting their scaling power spike. Fight NOW around objectives before they outscale."))
            already_fired.add(key)

    # Strong teamfight comp
    if ally_teamfight >= 2 and enemy_teamfight <= 1:
        key = "your_teamfight"
        if key not in already_fired and minutes > 10:
            tips.append((2, "strategy",
                "Your team has strong teamfight. Group for 5v5 around objectives."))
            already_fired.add(key)

    # Weak teamfight vs strong teamfight
    if enemy_teamfight >= 2 and ally_teamfight <= 1:
        key = "avoid_teamfight"
        if key not in already_fired and minutes > 10:
            tips.append((1, "strategy",
                "Enemy has better teamfight. Avoid 5v5 — look for picks and split push instead."))
            already_fired.add(key)

    # Split push advice
    if ally_split >= 1 and minutes > 15:
        key = "split_push"
        if key not in already_fired:
            splitters = [c for c in ally_champs if c in SPLIT_CHAMPS]
            tips.append((2, "strategy",
                f"You have split push threats ({', '.join(splitters)}). Apply side lane pressure while team groups."))
            already_fired.add(key)

    # Specific scaling champion warnings
    for champ in enemy_champs:
        if champ in SCALING_CHAMPS and minutes > 25:
            key = f"scaling_warning_{champ}"
            if key not in already_fired:
                tips.append((1, "threat",
                    f"Enemy {champ} is a late-game monster. Focus them in fights or end before they take over."))
                already_fired.add(key)
                break  # Only warn about the most dangerous one

    return tips
