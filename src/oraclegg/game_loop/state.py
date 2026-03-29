"""Game state machine: tracks which phase of the game we're in."""

import asyncio
import logging
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class GamePhase(str, Enum):
    IDLE = "idle"
    CHAMP_SELECT = "champ_select"
    IN_GAME = "in_game"
    POST_GAME = "post_game"


# Valid transitions
TRANSITIONS = {
    GamePhase.IDLE: {GamePhase.CHAMP_SELECT},
    GamePhase.CHAMP_SELECT: {GamePhase.IN_GAME, GamePhase.IDLE},  # IDLE = dodge
    GamePhase.IN_GAME: {GamePhase.POST_GAME},
    GamePhase.POST_GAME: {GamePhase.IDLE},
}


class GameStateMachine:
    def __init__(self):
        self._phase = GamePhase.IDLE
        self._listeners: list[Callable] = []
        self._lock = asyncio.Lock()
        self._champ_select_data: dict | None = None
        self._game_data: dict | None = None

    @property
    def phase(self) -> GamePhase:
        return self._phase

    @property
    def champ_select_data(self) -> dict | None:
        return self._champ_select_data

    @property
    def game_data(self) -> dict | None:
        return self._game_data

    def on_transition(self, callback: Callable):
        """Register a callback for phase transitions: callback(old_phase, new_phase)"""
        self._listeners.append(callback)

    async def transition(self, new_phase: GamePhase, data: dict | None = None):
        async with self._lock:
            if new_phase not in TRANSITIONS.get(self._phase, set()):
                logger.warning(
                    f"Invalid transition: {self._phase} -> {new_phase}"
                )
                return False

            old_phase = self._phase
            self._phase = new_phase

            if new_phase == GamePhase.CHAMP_SELECT:
                self._champ_select_data = data
            elif new_phase == GamePhase.IN_GAME:
                self._game_data = data
            elif new_phase == GamePhase.IDLE:
                self._champ_select_data = None
                self._game_data = None

            logger.info(f"Phase: {old_phase.value} -> {new_phase.value}")

            for listener in self._listeners:
                try:
                    result = listener(old_phase, new_phase)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Transition listener error: {e}")

            return True

    def to_dict(self) -> dict:
        return {
            "phase": self._phase.value,
            "has_champ_select_data": self._champ_select_data is not None,
            "has_game_data": self._game_data is not None,
        }
