"""Objective timing rules.

Generates tips about dragon, baron, herald based on game time and death timers.
"""

# Standard spawn timers (seconds)
DRAGON_FIRST_SPAWN = 300  # 5:00
DRAGON_RESPAWN = 300  # 5:00
RIFT_HERALD_SPAWN = 840  # 14:00
BARON_SPAWN = 1200  # 20:00
BARON_RESPAWN = 360  # 6:00
ELDER_DRAGON_SPAWN = 2100  # 35:00 (after soul taken)

OBJECTIVE_WINDOWS = [
    (300, "First dragon spawning soon. Set up vision bot side."),
    (840, "Rift Herald spawning at 14:00. Contest if you have priority."),
    (1140, "Void Grubs ending soon. Take them before they despawn at 19:45."),
    (1200, "Baron Nashor spawning at 20:00. Track enemy jungler and set up vision."),
    (2100, "Elder Dragon window approaching. This fight decides the game."),
]


def check_objective_timers(game_time: float, already_fired: set) -> list[tuple[int, str, str]]:
    """Returns list of (priority, category, message) for objective tips."""
    tips = []
    for threshold, message in OBJECTIVE_WINDOWS:
        key = f"obj_{threshold}"
        if key not in already_fired and threshold - 30 <= game_time <= threshold + 10:
            tips.append((1, "objective", message))
            already_fired.add(key)
    return tips
