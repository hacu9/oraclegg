"""Gold lead / team state rules.

Tips based on kill differentials and game tempo.
"""


def check_game_tempo(
    ally_kills: int, enemy_kills: int, game_time: float, already_fired: set
) -> list[tuple[int, str, str]]:
    """Returns (priority, category, message) tips based on game state."""
    tips = []
    kill_diff = ally_kills - enemy_kills
    minutes = game_time / 60

    # Early game warnings (pre-15)
    if minutes < 15:
        if kill_diff <= -5:
            key = "early_behind"
            if key not in already_fired:
                tips.append((0, "strategy", "Down significantly early. Farm safely, give up contested objectives, wait for item spikes."))
                already_fired.add(key)
        elif kill_diff >= 5:
            key = "early_ahead"
            if key not in already_fired:
                tips.append((2, "strategy", "Strong early lead. Use it to take towers and deny enemy jungle camps."))
                already_fired.add(key)

    # Mid game (15-25)
    elif minutes < 25:
        if kill_diff >= 8:
            key = "mid_stomp"
            if key not in already_fired:
                tips.append((1, "strategy", "Big lead mid-game. Group for Baron when it spawns. Don't throw by splitting."))
                already_fired.add(key)
        elif kill_diff <= -8:
            key = "mid_deficit"
            if key not in already_fired:
                tips.append((0, "strategy", "Significant deficit. Look for picks with vision control. Don't force 5v5 teamfights."))
                already_fired.add(key)

    # Late game (25+)
    else:
        if kill_diff <= -3:
            key = "late_behind"
            if key not in already_fired:
                tips.append((1, "strategy", "Behind late game. One teamfight win can turn it. Play around Elder Dragon and Baron."))
                already_fired.add(key)

    return tips
