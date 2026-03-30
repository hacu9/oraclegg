"""Tests for team composition classifier."""

from oraclegg.scouting.comp import classify_comp, get_champion_traits


def test_heavy_ap_comp():
    champs = [
        {"key": "Annie", "tags": ["Mage"]},
        {"key": "Elise", "tags": ["Mage", "Fighter"]},
        {"key": "Xerath", "tags": ["Mage"]},
        {"key": "KogMaw", "tags": ["Marksman"]},
        {"key": "Karma", "tags": ["Mage", "Support"]},
    ]
    archetypes = classify_comp(champs)
    assert "heavy_ap" in archetypes


def test_heavy_ad_comp():
    champs = [
        {"key": "Riven", "tags": ["Fighter"]},
        {"key": "Khazix", "tags": ["Assassin"]},
        {"key": "Zed", "tags": ["Assassin"]},
        {"key": "Jinx", "tags": ["Marksman"]},
        {"key": "Thresh", "tags": ["Support", "Tank"]},
    ]
    archetypes = classify_comp(champs)
    assert "heavy_ad" in archetypes


def test_engage_comp():
    champs = [
        {"key": "Malphite", "tags": ["Tank", "Fighter"]},
        {"key": "Amumu", "tags": ["Tank", "Mage"]},
        {"key": "Orianna", "tags": ["Mage"]},
        {"key": "Jinx", "tags": ["Marksman"]},
        {"key": "Leona", "tags": ["Tank", "Support"]},
    ]
    archetypes = classify_comp(champs)
    assert "engage" in archetypes


def test_balanced_comp():
    champs = [
        {"key": "Garen", "tags": ["Fighter", "Tank"]},
        {"key": "LeeSin", "tags": ["Fighter", "Assassin"]},
        {"key": "Ahri", "tags": ["Mage", "Assassin"]},
        {"key": "Jinx", "tags": ["Marksman"]},
        {"key": "Thresh", "tags": ["Support", "Tank"]},
    ]
    archetypes = classify_comp(champs)
    assert "balanced" in archetypes


def test_champion_traits_override():
    traits = get_champion_traits("Xerath", ["Mage"])
    assert "poke" in traits
    assert "ap" in traits


def test_champion_traits_default_ad():
    traits = get_champion_traits("UnknownChamp", ["Fighter"])
    assert "ad" in traits
