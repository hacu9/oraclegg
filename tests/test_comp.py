"""Tests for team composition classifier."""

from oraclegg.scouting.comp import classify_comp, get_champion_traits


class TestGetChampionTraits:
    def test_override_xerath_has_poke_and_ap(self):
        traits = get_champion_traits("Xerath", ["Mage"])
        assert "poke" in traits
        assert "ap" in traits

    def test_override_fiora_has_split_and_ad(self):
        traits = get_champion_traits("Fiora", ["Fighter"])
        assert "split" in traits
        assert "ad" in traits

    def test_tag_based_marksman_gets_ad(self):
        traits = get_champion_traits("Caitlyn", ["Marksman"])
        assert "ad" in traits

    def test_tag_based_mage_gets_ap(self):
        traits = get_champion_traits("Brand", ["Mage"])
        assert "ap" in traits

    def test_tag_tank_adds_tank_trait(self):
        traits = get_champion_traits("Sion", ["Tank"])
        assert "tank" in traits

    def test_unknown_champion_defaults_to_ad(self):
        traits = get_champion_traits("UnknownChamp", ["Fighter"])
        assert "ad" in traits

    def test_unknown_champion_no_tags_defaults_ad(self):
        traits = get_champion_traits("Nobody", [])
        assert "ad" in traits

    def test_empty_tags_with_override(self):
        traits = get_champion_traits("Zed", [])
        assert "assassin" in traits
        assert "ad" in traits

    def test_multiple_tags_combined(self):
        traits = get_champion_traits("Malphite", ["Tank", "Fighter"])
        assert "engage" in traits
        assert "tank" in traits
        assert "ap" in traits


class TestClassifyComp:
    def test_heavy_ap_comp(self):
        champs = [
            {"key": "Annie", "tags": ["Mage"]},
            {"key": "Elise", "tags": ["Mage", "Fighter"]},
            {"key": "Xerath", "tags": ["Mage"]},
            {"key": "KogMaw", "tags": ["Marksman"]},
            {"key": "Karma", "tags": ["Mage", "Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "heavy_ap" in archetypes

    def test_heavy_ad_comp(self):
        champs = [
            {"key": "Riven", "tags": ["Fighter"]},
            {"key": "Khazix", "tags": ["Assassin"]},
            {"key": "Zed", "tags": ["Assassin"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Thresh", "tags": ["Support", "Tank"]},
        ]
        archetypes = classify_comp(champs)
        assert "heavy_ad" in archetypes

    def test_engage_comp(self):
        champs = [
            {"key": "Malphite", "tags": ["Tank", "Fighter"]},
            {"key": "Amumu", "tags": ["Tank", "Mage"]},
            {"key": "Orianna", "tags": ["Mage"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Leona", "tags": ["Tank", "Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "engage" in archetypes

    def test_poke_comp(self):
        champs = [
            {"key": "Xerath", "tags": ["Mage"]},
            {"key": "Jayce", "tags": ["Fighter"]},
            {"key": "Ezreal", "tags": ["Marksman"]},
            {"key": "Lux", "tags": ["Mage"]},
            {"key": "Janna", "tags": ["Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "poke" in archetypes

    def test_split_push_comp(self):
        champs = [
            {"key": "Fiora", "tags": ["Fighter"]},
            {"key": "LeeSin", "tags": ["Fighter", "Assassin"]},
            {"key": "Ahri", "tags": ["Mage"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Thresh", "tags": ["Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "split_push" in archetypes

    def test_protect_carry_comp(self):
        champs = [
            {"key": "Ornn", "tags": ["Tank"]},
            {"key": "Ivern", "tags": ["Support"]},
            {"key": "Lulu", "tags": ["Support"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Karma", "tags": ["Mage", "Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "protect_carry" in archetypes

    def test_assassin_comp(self):
        champs = [
            {"key": "Zed", "tags": ["Assassin"]},
            {"key": "Khazix", "tags": ["Assassin"]},
            {"key": "Akali", "tags": ["Assassin"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Thresh", "tags": ["Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "assassin" in archetypes

    def test_scaling_comp(self):
        champs = [
            {"key": "Kayle", "tags": ["Fighter"]},
            {"key": "MasterYi", "tags": ["Assassin"]},
            {"key": "Viktor", "tags": ["Mage"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Lulu", "tags": ["Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "scaling" in archetypes

    def test_balanced_comp(self):
        # Need 2+ AP and 2+ AD for "balanced" alongside other archetypes
        champs = [
            {"key": "Garen", "tags": ["Fighter", "Tank"]},     # ad
            {"key": "Annie", "tags": ["Mage"]},                  # ap
            {"key": "Ahri", "tags": ["Mage"]},                   # ap
            {"key": "Jinx", "tags": ["Marksman"]},               # ad
            {"key": "Thresh", "tags": ["Support", "Tank"]},      # ad (default)
        ]
        archetypes = classify_comp(champs)
        assert "balanced" in archetypes

    def test_empty_team(self):
        archetypes = classify_comp([])
        assert "balanced" in archetypes

    def test_single_champion(self):
        champs = [{"key": "Xerath", "tags": ["Mage"]}]
        archetypes = classify_comp(champs)
        assert isinstance(archetypes, list)

    def test_missing_tags_key(self):
        """When 'tags' is missing from dict, should default to empty list."""
        champs = [{"key": "Garen"}, {"key": "Riven"}, {"key": "Zed"}]
        archetypes = classify_comp(champs)
        assert isinstance(archetypes, list)

    def test_heavy_tank_comp(self):
        champs = [
            {"key": "Malphite", "tags": ["Tank", "Fighter"]},
            {"key": "Ornn", "tags": ["Tank"]},
            {"key": "Sejuani", "tags": ["Tank"]},
            {"key": "Jinx", "tags": ["Marksman"]},
            {"key": "Leona", "tags": ["Tank", "Support"]},
        ]
        archetypes = classify_comp(champs)
        assert "heavy_tank" in archetypes
