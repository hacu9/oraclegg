"""Tests for shared constants and utility functions."""

from oraclegg.constants import (
    CHAMP_ICON_MAP,
    ROLE_MAP,
    SUMMONER_SPELL_NAMES,
    SUMMONER_SPELL_KEYS,
    champ_icon_key,
    normalize_role,
    spell_name,
)


class TestChampIconKey:
    def test_mapped_champion(self):
        assert champ_icon_key("Wukong") == "MonkeyKing"

    def test_apostrophe_champions(self):
        assert champ_icon_key("Kai'Sa") == "Kaisa"
        assert champ_icon_key("Kha'Zix") == "Khazix"
        assert champ_icon_key("Bel'Veth") == "Belveth"
        assert champ_icon_key("Vel'Koz") == "Velkoz"
        assert champ_icon_key("Kog'Maw") == "KogMaw"
        assert champ_icon_key("Cho'Gath") == "Chogath"
        assert champ_icon_key("Rek'Sai") == "RekSai"
        assert champ_icon_key("K'Sante") == "KSante"

    def test_special_name_champions(self):
        assert champ_icon_key("Renata Glasc") == "Renata"
        assert champ_icon_key("Nunu & Willump") == "Nunu"
        assert champ_icon_key("LeBlanc") == "Leblanc"

    def test_unmapped_champion_returns_same(self):
        assert champ_icon_key("Ahri") == "Ahri"
        assert champ_icon_key("Zed") == "Zed"

    def test_empty_string(self):
        assert champ_icon_key("") == ""


class TestNormalizeRole:
    def test_standard_mappings(self):
        assert normalize_role("TOP") == "TOP"
        assert normalize_role("JUNGLE") == "JUNGLE"
        assert normalize_role("MIDDLE") == "MID"
        assert normalize_role("BOTTOM") == "ADC"
        assert normalize_role("UTILITY") == "SUPPORT"

    def test_empty_string(self):
        assert normalize_role("") == "UNKNOWN"

    def test_unmapped_role_returns_original(self):
        assert normalize_role("FILL") == "FILL"


class TestSpellName:
    def test_known_spells(self):
        assert spell_name(4) == "Flash"
        assert spell_name(14) == "Ignite"
        assert spell_name(11) == "Smite"
        assert spell_name(12) == "Teleport"
        assert spell_name(7) == "Heal"
        assert spell_name(3) == "Exhaust"
        assert spell_name(1) == "Cleanse"
        assert spell_name(6) == "Ghost"
        assert spell_name(21) == "Barrier"
        assert spell_name(32) == "Mark"

    def test_unknown_spell_id(self):
        assert spell_name(999) == "Spell 999"
        assert spell_name(0) == "Spell 0"
        assert spell_name(-1) == "Spell -1"


class TestConstantsIntegrity:
    def test_champ_icon_map_values_are_strings(self):
        for key, value in CHAMP_ICON_MAP.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    def test_role_map_complete(self):
        expected_keys = {"TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY", ""}
        assert set(ROLE_MAP.keys()) == expected_keys

    def test_spell_names_are_strings(self):
        for spell_id, name in SUMMONER_SPELL_NAMES.items():
            assert isinstance(spell_id, int)
            assert isinstance(name, str)

    def test_spell_keys_match_spell_names(self):
        """Every spell in SUMMONER_SPELL_KEYS should have a corresponding name."""
        for display_name in SUMMONER_SPELL_KEYS:
            assert display_name in SUMMONER_SPELL_NAMES.values(), (
                f"{display_name} in SUMMONER_SPELL_KEYS but not in SUMMONER_SPELL_NAMES values"
            )
