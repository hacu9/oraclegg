"""Tests for player tendency analyzer."""

from oraclegg.scouting.analyzer import analyze_tendencies


def _make_match(champion_id=1, champion_name="TestChamp", win=True,
                kills=5, deaths=3, assists=7, role="MID"):
    return {
        "champion_id": champion_id,
        "champion_name": champion_name,
        "win": win,
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "role": role,
    }


class TestEmptyInput:
    def test_empty_list_returns_no_data(self):
        result = analyze_tendencies([])
        assert result == {"no_data": True}

    def test_none_champion_ids_returns_no_data(self):
        matches = [{"win": True, "kills": 1, "deaths": 0, "assists": 2}]
        result = analyze_tendencies(matches)
        assert result == {"no_data": True}


class TestOneTrick:
    def test_one_trick_detected(self):
        # 8 out of 10 games on same champ -> >60%
        matches = [_make_match(champion_id=42, champion_name="Riven")] * 8
        matches += [_make_match(champion_id=99, champion_name="Ahri")] * 2
        result = analyze_tendencies(matches)
        assert "one_trick" in result
        assert result["one_trick"]["champion_id"] == 42
        assert result["one_trick"]["pct"] == 80

    def test_diverse_pool_no_one_trick(self):
        matches = [
            _make_match(champion_id=i, champion_name=f"Champ{i}")
            for i in range(10)
        ]
        result = analyze_tendencies(matches)
        assert "one_trick" not in result


class TestFirstTiming:
    def test_first_timing_detected(self):
        matches = [_make_match(champion_id=1)] * 10
        result = analyze_tendencies(matches, current_champion_id=999)
        assert result.get("first_timing") is True

    def test_not_first_timing_if_played_before(self):
        matches = [_make_match(champion_id=42)] * 5
        result = analyze_tendencies(matches, current_champion_id=42)
        assert "first_timing" not in result
        assert "current_champ_stats" in result

    def test_current_champ_winrate(self):
        matches = [
            _make_match(champion_id=42, win=True),
            _make_match(champion_id=42, win=True),
            _make_match(champion_id=42, win=False),
            _make_match(champion_id=99, win=True),
        ]
        result = analyze_tendencies(matches, current_champion_id=42)
        stats = result["current_champ_stats"]
        assert stats["games"] == 3
        assert stats["wins"] == 2
        assert stats["win_rate"] == 67  # round(2/3 * 100)


class TestTilted:
    def test_tilted_three_loss_streak(self):
        matches = [
            _make_match(win=False),
            _make_match(win=False),
            _make_match(win=False),
            _make_match(win=True),
            _make_match(win=True),
        ]
        result = analyze_tendencies(matches)
        assert "tilted" in result
        assert result["tilted"]["loss_streak"] == 3

    def test_tilted_five_loss_streak(self):
        matches = [_make_match(win=False)] * 5
        result = analyze_tendencies(matches)
        assert result["tilted"]["loss_streak"] == 5

    def test_not_tilted_win_first(self):
        matches = [
            _make_match(win=True),
            _make_match(win=False),
            _make_match(win=False),
            _make_match(win=False),
            _make_match(win=False),
        ]
        result = analyze_tendencies(matches)
        assert "tilted" not in result

    def test_not_tilted_only_two_losses(self):
        matches = [
            _make_match(win=False),
            _make_match(win=False),
            _make_match(win=True),
        ]
        result = analyze_tendencies(matches)
        assert "tilted" not in result


class TestPlaystyle:
    def test_aggressive_playstyle(self):
        matches = [_make_match(kills=10, deaths=7, assists=3)] * 10
        result = analyze_tendencies(matches)
        assert result.get("playstyle") == "aggressive"

    def test_safe_playstyle(self):
        matches = [_make_match(kills=4, deaths=1, assists=8)] * 10
        result = analyze_tendencies(matches)
        assert result.get("playstyle") == "safe"

    def test_team_player_playstyle(self):
        matches = [_make_match(kills=2, deaths=3, assists=12)] * 10
        result = analyze_tendencies(matches)
        assert result.get("playstyle") == "team_player"


class TestStreaks:
    def test_hot_streak(self):
        matches = [_make_match(win=True)] * 10
        result = analyze_tendencies(matches)
        assert result.get("hot_streak") is True

    def test_cold_streak(self):
        matches = [_make_match(win=False)] * 10
        result = analyze_tendencies(matches)
        assert result.get("cold_streak") is True

    def test_no_streak_mixed(self):
        matches = [_make_match(win=i % 2 == 0) for i in range(10)]
        result = analyze_tendencies(matches)
        assert "hot_streak" not in result
        assert "cold_streak" not in result


class TestKDA:
    def test_kda_computed(self):
        matches = [_make_match(kills=5, deaths=2, assists=10)] * 4
        result = analyze_tendencies(matches)
        kda = result["kda"]
        assert kda["avg_kills"] == 5.0
        assert kda["avg_deaths"] == 2.0
        assert kda["avg_assists"] == 10.0
        # KDA = (5+10)/2 = 7.5
        assert kda["kda"] == 7.5

    def test_kda_zero_deaths(self):
        matches = [_make_match(kills=5, deaths=0, assists=10)] * 3
        result = analyze_tendencies(matches)
        # KDA = (total_kills + total_assists) / max(total_deaths, 1)
        # = (15 + 30) / 1 = 45.0
        assert result["kda"]["kda"] == 45.0

    def test_recent_winrate(self):
        matches = [_make_match(win=True)] * 3 + [_make_match(win=False)] * 7
        result = analyze_tendencies(matches)
        assert result["recent_winrate"]["wins"] == 3
        assert result["recent_winrate"]["losses"] == 7
        assert result["recent_winrate"]["pct"] == 30
