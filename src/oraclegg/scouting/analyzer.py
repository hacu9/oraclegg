"""Player tendency analyzer.

Analyzes match history to identify tendencies: one-trick, first-timer,
tilted, autofilled, playstyle, etc.
"""

from collections import Counter


def analyze_tendencies(
    recent_matches: list[dict],
    current_champion_id: int | None = None,
) -> dict:
    """Analyze a player's recent match history for tendencies.

    Args:
        recent_matches: list of match dicts with champion_id, role, win, kills, deaths, assists
        current_champion_id: the champion they're currently playing

    Returns:
        dict of tendency labels and details
    """
    if not recent_matches:
        return {"no_data": True}

    tendencies = {}
    total = len(recent_matches)

    # Champion pool analysis
    champ_counter = Counter(m.get("champion_id") for m in recent_matches if m.get("champion_id"))
    if not champ_counter:
        return {"no_data": True}
    most_played_id, most_played_count = champ_counter.most_common(1)[0]

    # One-trick: >60% of games on 1-2 champions
    if most_played_count / total > 0.6:
        tendencies["one_trick"] = {
            "champion_id": most_played_id,
            "champion_name": next(
                (m["champion_name"] for m in recent_matches if m.get("champion_id") == most_played_id),
                "Unknown",
            ),
            "games": most_played_count,
            "pct": round(most_played_count / total * 100),
        }

    # First-timing: 0 recent games on current champion
    if current_champion_id:
        games_on_current = sum(
            1 for m in recent_matches if m.get("champion_id") == current_champion_id
        )
        if games_on_current == 0:
            tendencies["first_timing"] = True
        else:
            # Win rate on current champion
            wins = sum(
                1 for m in recent_matches
                if m.get("champion_id") == current_champion_id and m.get("win")
            )
            tendencies["current_champ_stats"] = {
                "games": games_on_current,
                "wins": wins,
                "win_rate": round(wins / games_on_current * 100) if games_on_current else 0,
            }

    # Tilted: 3+ losses in a row (most recent games)
    recent_results = [m.get("win", False) for m in recent_matches[:5]]
    loss_streak = 0
    for result in recent_results:
        if not result:
            loss_streak += 1
        else:
            break
    if loss_streak >= 3:
        tendencies["tilted"] = {
            "loss_streak": loss_streak,
        }

    # Autofilled: playing a role they rarely play
    if current_champion_id:
        role_counter = Counter(m.get("role", "") for m in recent_matches)
        # We can't directly know their current role from champion ID alone,
        # but we can flag if their champion pool suggests off-role

    # Playstyle analysis (from KDA patterns)
    total_kills = sum(m.get("kills", 0) for m in recent_matches)
    total_deaths = sum(m.get("deaths", 0) for m in recent_matches)
    total_assists = sum(m.get("assists", 0) for m in recent_matches)

    avg_kills = total_kills / total if total else 0
    avg_deaths = total_deaths / total if total else 0
    avg_assists = total_assists / total if total else 0
    kda = (total_kills + total_assists) / max(total_deaths, 1)

    tendencies["kda"] = {
        "avg_kills": round(avg_kills, 1),
        "avg_deaths": round(avg_deaths, 1),
        "avg_assists": round(avg_assists, 1),
        "kda": round(kda, 2),
    }

    if avg_kills > 7 and avg_deaths > 5:
        tendencies["playstyle"] = "aggressive"
    elif avg_deaths < 3 and kda > 4:
        tendencies["playstyle"] = "safe"
    elif avg_assists > avg_kills * 1.5:
        tendencies["playstyle"] = "team_player"

    # Overall win rate (recent)
    wins = sum(1 for m in recent_matches if m.get("win"))
    tendencies["recent_winrate"] = {
        "wins": wins,
        "losses": total - wins,
        "pct": round(wins / total * 100),
    }

    # Hot streak or cold streak
    if wins >= 7:
        tendencies["hot_streak"] = True
    elif total - wins >= 7:
        tendencies["cold_streak"] = True

    return tendencies
