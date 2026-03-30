"""Tests for boot recommendation rules."""

from oraclegg.recommender.rules.boots_rules import (
    BOOTS,
    recommend_boots,
)


class TestRecommendBoots:
    def test_heavy_cc_recommends_mercs(self):
        enemy_champs = ["Leona", "Nautilus", "Amumu", "Ashe", "Lux"]
        result = recommend_boots("Ahri", "MID", enemy_champs, {})
        assert result["boot_id"] == 3111  # Mercury's Treads
        assert result["boot_name"] == "Mercury's Treads"
        assert result["enemy_breakdown"]["cc_count"] >= 3

    def test_heavy_auto_attackers_recommends_steelcaps(self):
        enemy_champs = ["Vayne", "Jinx", "Tryndamere", "Jax", "Thresh"]
        result = recommend_boots("Ahri", "MID", enemy_champs, {})
        assert result["boot_id"] == 3047  # Plated Steelcaps
        assert result["enemy_breakdown"]["auto_attackers"] >= 3

    def test_heavy_ap_items_recommends_mercs(self):
        enemy_champs = ["Brand", "Viktor", "Syndra", "Caitlyn", "Thresh"]
        enemy_items = {
            "Brand": {6653},    # Liandry's
            "Viktor": {3089},   # Rabadon's
            "Syndra": {4645},   # Shadowflame
        }
        result = recommend_boots("Jinx", "ADC", enemy_champs, enemy_items)
        assert result["boot_id"] == 3111
        assert result["enemy_breakdown"]["ap_threats"] >= 3

    def test_heavy_ad_items_recommends_steelcaps(self):
        enemy_champs = ["Zed", "Talon", "Graves", "Caitlyn", "Thresh"]
        enemy_items = {
            "Zed": {6692},      # Eclipse
            "Talon": {6676},    # Collector
            "Graves": {3078},   # Trinity
            "Caitlyn": {3031},  # IE
        }
        result = recommend_boots("Ahri", "MID", enemy_champs, enemy_items)
        assert result["boot_id"] == 3047

    def test_mid_mage_default_sorc_shoes(self):
        # Use champs that are not in AUTO_ATTACK_CHAMPS or HARD_CC_CHAMPS
        enemy_champs = ["Garen", "Darius", "Akali", "Graves", "Soraka"]
        result = recommend_boots("Viktor", "MID", enemy_champs, {})
        assert result["boot_id"] == 3020  # Sorc Shoes

    def test_adc_default_berserkers(self):
        enemy_champs = ["Garen", "Darius", "Akali", "Graves", "Soraka"]
        result = recommend_boots("Jinx", "ADC", enemy_champs, {})
        assert result["boot_id"] == 3006  # Berserker's

    def test_support_default_lucidity(self):
        enemy_champs = ["Garen", "Darius", "Akali", "Graves", "Soraka"]
        result = recommend_boots("Lulu", "SUPPORT", enemy_champs, {})
        assert result["boot_id"] == 3158  # Ionian

    def test_result_has_expected_keys(self):
        result = recommend_boots("Ahri", "MID", ["Garen"], {})
        assert "boot_id" in result
        assert "boot_name" in result
        assert "reasons" in result
        assert "alternatives" in result
        assert "enemy_breakdown" in result

    def test_alternatives_exclude_recommendation(self):
        result = recommend_boots("Ahri", "MID", ["Garen"], {})
        alt_ids = {a["id"] for a in result["alternatives"]}
        assert result["boot_id"] not in alt_ids

    def test_empty_enemy_list(self):
        result = recommend_boots("Ahri", "MID", [], {})
        assert result["boot_id"] is not None
        assert isinstance(result["reasons"], list)

    def test_jungle_with_cc(self):
        enemy_champs = ["Leona", "Nautilus", "Lux", "Caitlyn", "Garen"]
        result = recommend_boots("LeeSin", "JUNGLE", enemy_champs, {})
        # Should pick mercs due to CC
        assert result["boot_id"] == 3111

    def test_jungle_without_cc(self):
        enemy_champs = ["Garen", "Darius", "Akali", "Graves", "Soraka"]
        result = recommend_boots("LeeSin", "JUNGLE", enemy_champs, {})
        # Should pick CDR boots (no CC, no auto-attackers)
        assert result["boot_id"] == 3158

    def test_top_ad_leaning(self):
        enemy_champs = ["Garen", "MasterYi", "Ahri", "Caitlyn", "Janna"]
        enemy_items = {
            "Garen": {3078},
            "MasterYi": {6672},
        }
        result = recommend_boots("Malphite", "TOP", enemy_champs, enemy_items)
        assert result["boot_id"] == 3047  # Steelcaps for AD leaning
