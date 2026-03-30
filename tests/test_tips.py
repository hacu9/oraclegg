"""Tests for the TipEngine."""

from oraclegg.recommender.tips import TipEngine, Tip, POWER_SPIKE_ITEMS


def _make_player(name, team, champion, kills=0, deaths=0, assists=0,
                 items=None, is_dead=False, level=6, position=""):
    return {
        "riotIdGameName": name,
        "summonerName": name,
        "team": team,
        "championName": champion,
        "position": position,
        "level": level,
        "isDead": is_dead,
        "scores": {"kills": kills, "deaths": deaths, "assists": assists},
        "items": [{"itemID": i} for i in (items or [])],
    }


def _make_game_state(my_name, players, game_time=600, events=None, terrain="Default"):
    return {
        "active_player": {"name": my_name},
        "players": players,
        "game_time": game_time,
        "events": events or [],
        "map_terrain": terrain,
    }


class TestTipEngineBasics:
    def test_empty_players_returns_no_tips(self):
        engine = TipEngine()
        state = {"active_player": {"name": "me"}, "players": [], "game_time": 0}
        assert engine.analyze(state) == []

    def test_no_active_player_returns_no_tips(self):
        engine = TipEngine()
        state = {"active_player": {}, "players": [_make_player("me", "ORDER", "Ahri")], "game_time": 0}
        # active_player has no "name" key -> empty string -> won't match
        tips = engine.analyze(state)
        assert tips == []

    def test_player_not_found_returns_no_tips(self):
        engine = TipEngine()
        players = [_make_player("other", "ORDER", "Ahri")]
        state = _make_game_state("ghost", players)
        assert engine.analyze(state) == []


class TestThreatDetection:
    def test_super_fed_enemy(self):
        engine = TipEngine()
        players = [
            _make_player("me", "ORDER", "Ahri"),
            _make_player("fed_zed", "CHAOS", "Zed", kills=12, deaths=1),
        ]
        state = _make_game_state("me", players)
        tips = engine.analyze(state)
        threat_tips = [t for t in tips if t.category == "threat"]
        assert len(threat_tips) >= 1
        assert "Zed" in threat_tips[0].message

    def test_fed_healer_suggests_antiheal(self):
        engine = TipEngine()
        players = [
            _make_player("me", "ORDER", "Ahri"),
            _make_player("aatrox", "CHAOS", "Aatrox", kills=8, deaths=2),
        ]
        state = _make_game_state("me", players)
        tips = engine.analyze(state)
        build_tips = [t for t in tips if t.category == "build"]
        assert any("anti-heal" in t.message for t in build_tips)


class TestTeamGold:
    def test_far_behind_triggers_safe_tip(self):
        engine = TipEngine()
        allies = [_make_player(f"a{i}", "ORDER", "Ahri", kills=1) for i in range(5)]
        enemies = [_make_player(f"e{i}", "CHAOS", "Zed", kills=5) for i in range(5)]
        players = allies + enemies
        state = _make_game_state("a0", players, game_time=900)
        tips = engine.analyze(state)
        strat_tips = [t for t in tips if t.category == "strategy"]
        assert any("behind" in t.message.lower() or "safe" in t.message.lower()
                    for t in strat_tips)

    def test_stomping_triggers_objective_tip(self):
        engine = TipEngine()
        allies = [_make_player(f"a{i}", "ORDER", "Ahri", kills=5) for i in range(5)]
        enemies = [_make_player(f"e{i}", "CHAOS", "Zed", kills=1) for i in range(5)]
        players = allies + enemies
        state = _make_game_state("a0", players, game_time=900)
        tips = engine.analyze(state)
        strat_tips = [t for t in tips if t.category == "strategy"]
        assert any("stomp" in t.message.lower() or "objective" in t.message.lower()
                    for t in strat_tips)


class TestDeadEnemies:
    def test_three_dead_enemies_late_game(self):
        engine = TipEngine()
        allies = [_make_player("me", "ORDER", "Ahri")]
        enemies = [
            _make_player(f"e{i}", "CHAOS", f"Champ{i}", is_dead=True)
            for i in range(3)
        ]
        players = allies + enemies
        state = _make_game_state("me", players, game_time=1300)
        tips = engine.analyze(state)
        obj_tips = [t for t in tips if t.category == "objective"]
        assert any("dead" in t.message.lower() for t in obj_tips)


class TestPowerSpikes:
    def test_enemy_level_6_before_me(self):
        engine = TipEngine()
        players = [
            _make_player("me", "ORDER", "Ahri", level=5),
            _make_player("enemy", "CHAOS", "Zed", level=6),
        ]
        state = _make_game_state("me", players)
        tips = engine.analyze(state)
        threat_tips = [t for t in tips if t.category == "threat"]
        assert any("level 6" in t.message.lower() for t in threat_tips)


class TestDedup:
    def test_tips_deduped_across_calls(self):
        engine = TipEngine()
        players = [
            _make_player("me", "ORDER", "Ahri", level=5),
            _make_player("enemy", "CHAOS", "Zed", level=6),
        ]
        state = _make_game_state("me", players)
        tips1 = engine.analyze(state)
        tips2 = engine.analyze(state)
        # Second call should have fewer (or zero) tips because they were deduped
        assert len(tips2) <= len(tips1)

    def test_max_five_tips(self):
        engine = TipEngine()
        allies = [_make_player(f"a{i}", "ORDER", "Ahri", kills=1) for i in range(5)]
        enemies = [
            _make_player(f"e{i}", "CHAOS", f"Champ{i}", kills=10, deaths=0, is_dead=(i < 3))
            for i in range(5)
        ]
        players = allies + enemies
        state = _make_game_state("a0", players, game_time=1500)
        tips = engine.analyze(state)
        assert len(tips) <= 5
