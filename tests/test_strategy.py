"""Tests for power spike / strategic comp analysis rules."""

from oraclegg.recommender.rules.power_spike_rules import (
    analyze_team_strategy,
    SCALING_CHAMPS,
    EARLY_GAME_CHAMPS,
    TEAMFIGHT_CHAMPS,
    SPLIT_CHAMPS,
)


class TestScalingAdvice:
    def test_your_team_scales_early(self):
        allies = ["Kayle", "Kassadin", "Vayne", "Viktor", "Lulu"]
        enemies = ["Draven", "Pantheon", "LeeSin", "Caitlyn", "Thresh"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=600, already_fired=fired)
        assert any("scaling" in m.lower() or "safe" in m.lower() for _, _, m in tips)

    def test_your_team_scales_late(self):
        allies = ["Kayle", "Kassadin", "Vayne", "Viktor", "Lulu"]
        enemies = ["Draven", "Pantheon", "LeeSin", "Caitlyn", "Thresh"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=1600, already_fired=fired)
        assert any("outscale" in m.lower() or "force" in m.lower() for _, _, m in tips)

    def test_enemy_scales_early_warning(self):
        allies = ["Draven", "Pantheon", "LeeSin", "Caitlyn", "Thresh"]
        enemies = ["Kayle", "Kassadin", "Vayne", "Viktor", "Lulu"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=600, already_fired=fired)
        assert any("close" in m.lower() or "early" in m.lower() for _, _, m in tips)

    def test_enemy_scales_late_warning(self):
        allies = ["Draven", "Pantheon", "LeeSin", "Caitlyn", "Thresh"]
        enemies = ["Kayle", "Kassadin", "Vayne", "Viktor", "Lulu"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=1600, already_fired=fired)
        assert any("scaling" in m.lower() or "outscale" in m.lower() or "fight now" in m.lower()
                    for _, _, m in tips)


class TestTeamfightAdvice:
    def test_strong_teamfight_comp(self):
        allies = ["Malphite", "Amumu", "Orianna", "MissFortune", "Rell"]
        enemies = ["Fiora", "LeeSin", "Zed", "Caitlyn", "Thresh"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=700, already_fired=fired)
        assert any("teamfight" in m.lower() for _, _, m in tips)

    def test_weak_teamfight_advice(self):
        allies = ["Fiora", "LeeSin", "Zed", "Caitlyn", "Thresh"]
        enemies = ["Malphite", "Amumu", "Orianna", "MissFortune", "Rell"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=700, already_fired=fired)
        assert any("avoid" in m.lower() or "picks" in m.lower() or "split" in m.lower()
                    for _, _, m in tips)


class TestSplitPush:
    def test_split_push_advice(self):
        allies = ["Fiora", "LeeSin", "Ahri", "Jinx", "Thresh"]
        enemies = ["Garen", "Warwick", "Viktor", "Caitlyn", "Lulu"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=1000, already_fired=fired)
        assert any("split" in m.lower() for _, _, m in tips)

    def test_no_split_advice_before_15_min(self):
        allies = ["Fiora", "LeeSin", "Ahri", "Jinx", "Thresh"]
        enemies = ["Garen", "Warwick", "Viktor", "Caitlyn", "Lulu"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=600, already_fired=fired)
        split_tips = [m for _, _, m in tips if "split" in m.lower() and "side lane" in m.lower()]
        assert len(split_tips) == 0


class TestAlreadyFired:
    def test_tips_not_repeated(self):
        allies = ["Kayle", "Kassadin", "Vayne", "Viktor", "Lulu"]
        enemies = ["Draven", "Pantheon", "LeeSin", "Caitlyn", "Thresh"]
        fired = set()
        tips1 = analyze_team_strategy(allies, enemies, game_time=600, already_fired=fired)
        tips2 = analyze_team_strategy(allies, enemies, game_time=600, already_fired=fired)
        assert len(tips2) == 0  # all keys already fired


class TestScalingWarnings:
    def test_late_game_scaling_enemy_warning(self):
        allies = ["Garen", "LeeSin", "Ahri", "Caitlyn", "Thresh"]
        enemies = ["Kayle", "Kassadin", "Viktor", "Jinx", "Lulu"]
        fired = set()
        tips = analyze_team_strategy(allies, enemies, game_time=1600, already_fired=fired)
        threat_tips = [(p, c, m) for p, c, m in tips if c == "threat"]
        assert any("late-game monster" in m.lower() for _, _, m in threat_tips)


class TestEmptyTeams:
    def test_empty_teams_no_crash(self):
        tips = analyze_team_strategy([], [], game_time=600, already_fired=set())
        assert isinstance(tips, list)

    def test_single_champion_each(self):
        tips = analyze_team_strategy(["Kayle"], ["Zed"], game_time=600, already_fired=set())
        assert isinstance(tips, list)
