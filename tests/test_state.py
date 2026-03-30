"""Tests for game state machine transitions."""

import pytest

from oraclegg.game_loop.state import GamePhase, GameStateMachine, TRANSITIONS


class TestGamePhaseEnum:
    def test_all_phases_are_strings(self):
        for phase in GamePhase:
            assert isinstance(phase.value, str)

    def test_phase_values(self):
        assert GamePhase.IDLE.value == "idle"
        assert GamePhase.CHAMP_SELECT.value == "champ_select"
        assert GamePhase.IN_GAME.value == "in_game"
        assert GamePhase.POST_GAME.value == "post_game"


class TestTransitions:
    def test_all_phases_have_transition_entry(self):
        for phase in GamePhase:
            assert phase in TRANSITIONS

    def test_idle_can_go_to_champ_select(self):
        assert GamePhase.CHAMP_SELECT in TRANSITIONS[GamePhase.IDLE]

    def test_idle_cannot_go_to_in_game(self):
        assert GamePhase.IN_GAME not in TRANSITIONS[GamePhase.IDLE]

    def test_champ_select_can_dodge_to_idle(self):
        assert GamePhase.IDLE in TRANSITIONS[GamePhase.CHAMP_SELECT]

    def test_champ_select_to_in_game(self):
        assert GamePhase.IN_GAME in TRANSITIONS[GamePhase.CHAMP_SELECT]

    def test_in_game_to_post_game(self):
        assert GamePhase.POST_GAME in TRANSITIONS[GamePhase.IN_GAME]

    def test_post_game_to_idle(self):
        assert GamePhase.IDLE in TRANSITIONS[GamePhase.POST_GAME]


class TestStateMachine:
    async def test_initial_state_is_idle(self):
        sm = GameStateMachine()
        assert sm.phase == GamePhase.IDLE

    async def test_valid_transition(self):
        sm = GameStateMachine()
        result = await sm.transition(GamePhase.CHAMP_SELECT)
        assert result is True
        assert sm.phase == GamePhase.CHAMP_SELECT

    async def test_invalid_transition_rejected(self):
        sm = GameStateMachine()
        result = await sm.transition(GamePhase.IN_GAME)
        assert result is False
        assert sm.phase == GamePhase.IDLE

    async def test_full_game_cycle(self):
        sm = GameStateMachine()
        assert await sm.transition(GamePhase.CHAMP_SELECT) is True
        assert await sm.transition(GamePhase.IN_GAME) is True
        assert await sm.transition(GamePhase.POST_GAME) is True
        assert await sm.transition(GamePhase.IDLE) is True
        assert sm.phase == GamePhase.IDLE

    async def test_dodge_returns_to_idle(self):
        sm = GameStateMachine()
        await sm.transition(GamePhase.CHAMP_SELECT)
        result = await sm.transition(GamePhase.IDLE)
        assert result is True
        assert sm.phase == GamePhase.IDLE

    async def test_champ_select_stores_data(self):
        sm = GameStateMachine()
        data = {"picks": [1, 2, 3]}
        await sm.transition(GamePhase.CHAMP_SELECT, data=data)
        assert sm.champ_select_data == data

    async def test_in_game_stores_data(self):
        sm = GameStateMachine()
        await sm.transition(GamePhase.CHAMP_SELECT)
        game_data = {"map": "SR"}
        await sm.transition(GamePhase.IN_GAME, data=game_data)
        assert sm.game_data == game_data

    async def test_return_to_idle_clears_data(self):
        sm = GameStateMachine()
        await sm.transition(GamePhase.CHAMP_SELECT, data={"x": 1})
        await sm.transition(GamePhase.IN_GAME, data={"y": 2})
        await sm.transition(GamePhase.POST_GAME)
        await sm.transition(GamePhase.IDLE)
        assert sm.champ_select_data is None
        assert sm.game_data is None

    async def test_to_dict(self):
        sm = GameStateMachine()
        d = sm.to_dict()
        assert d["phase"] == "idle"
        assert d["has_champ_select_data"] is False
        assert d["has_game_data"] is False

    async def test_to_dict_with_data(self):
        sm = GameStateMachine()
        await sm.transition(GamePhase.CHAMP_SELECT, data={"x": 1})
        d = sm.to_dict()
        assert d["phase"] == "champ_select"
        assert d["has_champ_select_data"] is True

    async def test_listener_called_on_transition(self):
        sm = GameStateMachine()
        calls = []
        sm.on_transition(lambda old, new: calls.append((old, new)))
        await sm.transition(GamePhase.CHAMP_SELECT)
        assert len(calls) == 1
        assert calls[0] == (GamePhase.IDLE, GamePhase.CHAMP_SELECT)

    async def test_listener_not_called_on_invalid_transition(self):
        sm = GameStateMachine()
        calls = []
        sm.on_transition(lambda old, new: calls.append((old, new)))
        await sm.transition(GamePhase.POST_GAME)  # invalid from IDLE
        assert len(calls) == 0

    async def test_listener_error_does_not_break_transition(self):
        sm = GameStateMachine()

        def bad_listener(old, new):
            raise ValueError("boom")

        sm.on_transition(bad_listener)
        result = await sm.transition(GamePhase.CHAMP_SELECT)
        assert result is True
        assert sm.phase == GamePhase.CHAMP_SELECT

    async def test_async_listener(self):
        sm = GameStateMachine()
        calls = []

        async def async_listener(old, new):
            calls.append((old, new))

        sm.on_transition(async_listener)
        await sm.transition(GamePhase.CHAMP_SELECT)
        assert len(calls) == 1
