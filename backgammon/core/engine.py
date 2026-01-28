# =========================================================
# --- core_engine.py ---
# =========================================================

import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from players.player import Player

from .rules import BackgammonRules, GameResult
from .state import BackgammonState
from .undo import Undo
from .generator import TurnMoveGenerator

# ========================================================

@dataclass
class CubeDecision:
    """
    Represents a doubling cube decision during a turn.

    Attributes:
        offered (bool): Whether the player offered a double.
        accepted (Optional[bool]): Whether the opponent accepted the double. None if not decided yet.
        result (Optional[GameResult]): Game result if the cube decision ended the game.
    """
    offered: bool
    accepted: Optional[bool]
    result: Optional[GameResult]


class EngineEvents:
    """
    Event factory for game engine events. 
    Returns structured dictionaries for UI, logging, or network updates.
    """

    def start_roll(self, dice: list[int], turn: int) -> Dict[str, Any]:
        """Event: A dice roll has started for a player's turn."""
        return {
            "type": "start_roll",
            "dice": dice,
            "turn": turn,
        }

    def turn_start(self, turn: int, state: BackgammonState, bear_off_allowed: bool) -> Dict[str, Any]:
        """Event: A new turn has started."""
        return {
            "type": "turn_start",
            "turn": turn,
            "state": state,
            "bear_off_allowed": bear_off_allowed,
        }

    def roll_dice(self, dice: list[int], turn: int, player_type: str) -> Dict[str, Any]:
        """Event: Dice have been rolled."""
        return {
            "type": "roll_dice",
            "dice": dice,
            "turn": turn,
            "player_type": player_type,
        }

    def no_moves(self, turn: int) -> Dict[str, Any]:
        """Event: Player has no legal moves available."""
        return {
            "type": "no_moves",
            "turn": turn,
        }

    def chosen_move(self, turn: int, move: Any) -> Dict[str, Any]:
        """Event: Player has chosen a move."""
        return {
            "type": "chosen_move",
            "turn": turn,
            "move": move,
        }

    def apply_move(self, move: Any, state: BackgammonState) -> Dict[str, Any]:
        """Event: A move has been applied to the game state."""
        return {
            "type": "apply_move",
            "move": move,
            "state": state,
        }

    def turn_end(self, next_turn: int, state: BackgammonState) -> Dict[str, Any]:
        """Event: The current turn has ended."""
        return {
            "type": "turn_end",
            "next_turn": next_turn,
            "state": state,
        }

    def cube_action(self, turn: int, decision: CubeDecision, cube_value: int) -> Dict[str, Any]:
        """Event: Doubling cube action occurred."""
        return {
            "type": "cube_action",
            "turn": turn,
            "offered": decision.offered,
            "accepted": decision.accepted,
            "cube_value": cube_value,
        }

    def game_over(
        self, 
        state: BackgammonState, 
        winner: int, 
        player_type: str, 
        points: int, 
        cube_value: int, 
        result_type: str
    ) -> Dict[str, Any]:
        """Event: The game has ended."""
        return {
            "type": "game_over",
            "state": state,
            "winner": winner,
            "player_type": player_type,
            "points": points,
            "cube_value": cube_value,
            "result_type": result_type,
        }

class GameEngine:
    """
    Backgammon game engine managing players, game state, turns, dice, cube, and events.

    Attributes:
        players (list): List of two player objects.
        state (BackgammonState): Current mutable game state.
        rules (BackgammonRules): Rules engine.
        enable_cube (bool): Whether doubling cube is enabled.
        cube_value (int): Current cube value.
        cube_owner (Optional[int]): Cube owner: None = neutral, 0/1 = player index.
        undo (Undo): Undo manager for moves and snapshots.
        emit_enabled (bool): If True, yield events during play.
        events (EngineEvents): Event generator for logging/UI.
        dice (list[int]): Current dice rolled.
        rng (random.Random): Random number generator for dice rolls.
    """

    def __init__(
        self, 
        player0: Player, 
        player1: Player, 
        state: BackgammonState, 
        rules: BackgammonRules, 
        enable_cube: bool = False, 
        emit_enabled: bool = True, 
        rng: Optional[random.Random] = None
    ):
        self.players: list[Player] = [player0, player1]
        self.state: BackgammonState = state
        self.rules: BackgammonRules = rules
        self.rng: random.Random = rng or random.Random()
        self.enable_cube: bool = enable_cube

        self.cube_value: int = 1
        self.cube_owner: Optional[int] = None  # None = neutral, 0/1 = player

        self.undo: Undo = Undo()
        self.emit_enabled: bool = emit_enabled
        self.events: EngineEvents = EngineEvents()
        self.dice: list[int] = []

    # ---------- Properties ----------
    @property
    def turn(self) -> int:
        """Index of the active player (0 or 1)."""
        return self.state.turn

    @property
    def player(self) -> Player:
        """Return the current player object."""
        return self.players[self.turn]

    @property
    def legal_moves(self) -> list:
        """Return list of legal turn moves for the current dice and state."""
        return TurnMoveGenerator().generate_legal_moves(self.state, self.rules, self.dice)

    def get_player_type(self, player: int) -> str:
        """Return string representation of a player."""
        return str(self.players[player])

    # ---------- Dice ----------
    def roll_start_dice(self) -> tuple[int, int]:
        """Roll dice to determine which player starts. Re-roll doubles."""
        d0, d1 = self.rng.randint(1, 6), self.rng.randint(1, 6)
        while d0 == d1:
            d0, d1 = self.rng.randint(1, 6), self.rng.randint(1, 6)
        start_turn = 0 if d0 > d1 else 1
        if self.turn != start_turn:
            self.state.switch_turn()
        return d0, d1

    def roll_dice(self) -> None:
        """Roll dice for a turn and expand doubles if needed."""
        d1, d2 = self.rng.randint(1, 6), self.rng.randint(1, 6)
        self.dice = self.rules.process_dice([d1, d2])

    # ---------- Turn Management ----------
    def next_turn(self) -> None:
        """Switch to the next player."""
        self.state.switch_turn()

    def game_finished(self) -> Optional[GameResult]:
        """Check if the game is over, returning a GameResult if so."""
        return self.rules.game_over(self.state, self.cube_value)

    # ---------- Doubling Cube ----------
    def offer_double(self) -> CubeDecision:
        """
        Attempt to offer a doubling cube.
        
        Returns:
            CubeDecision: Contains offered, accepted, and result if game ends.
        """
        turn = self.turn

        if self.cube_owner not in (None, turn):
            return CubeDecision(False, None, None)

        player = self.players[turn]
        opponent = self.players[1 - turn]

        if not player.offer_double(self.cube_value, self.state):
            return CubeDecision(False, None, None)

        if not opponent.accept_double(self.cube_value, self.state):
            game_result = GameResult(
                winner=turn,
                points=self.cube_value,
                cube_value=self.cube_value,
                type="DROP",
            )
            return CubeDecision(offered=True, accepted=False, result=game_result)

        self.cube_value *= 2
        self.cube_owner = 1 - turn

        return CubeDecision(True, True, None)

    # ---------- Undo ----------
    def undo_last_move(self) -> Any:
        """Undo the last move and return it."""
        return self.undo.undo_last_move(self.state)

    # ---------- Event Emission ----------
    def emit(self, event: dict) -> Any:
        """Yield an event if emission is enabled."""
        if self.emit_enabled:
            yield event

    # ---------- Internal Phases ----------
    def _cube_phase(self) -> Optional[GameResult]:
        """Handle doubling cube phase at the start of a turn."""
        decision = self.offer_double()
        yield from self.emit(self.events.cube_action(self.turn, decision, self.cube_value))

        if decision.offered and not decision.accepted:
            return decision.result

        return None

    def _play_turn_moves(self, player: Player, dice: list[int], stepwise: bool):
        """Apply all legal moves for a turn, emitting events if stepwise."""
        if not self.legal_moves:
            yield from self.emit(self.events.no_moves(self.turn))
            return

        turn_move = self.player.select_move(self.legal_moves, self.state.copy(), self.dice)
        yield from self.emit(self.events.chosen_move(self.turn, turn_move))

        for smove in turn_move:
            self.state.apply_move(smove)
            if hasattr(self, "undo"):
                self.undo.record_move(smove)
            if stepwise:
                yield from self.emit(self.events.apply_move(smove, self.state))

    # ---------- Game Loop ----------
    def play_from_state(self, stepwise: bool = True, max_turns: Optional[int] = None):
        """
        Play the game from the current state, yielding events stepwise.

        Args:
            stepwise (bool): If True, events are yielded after each move.
            max_turns (Optional[int]): Maximum turns to play. None = no limit.

        Yields:
            dict: Engine events describing the game progression.
        """
        game_result = self.game_finished()
        turns_played = 0

        while not game_result:
            if max_turns is not None and turns_played >= max_turns:
                break

            player = self.players[self.turn]
            bear_off_allowed = self.rules.bearing_off_allowed(self.state)

            yield from self.emit(self.events.turn_start(self.turn, self.state, bear_off_allowed))

            if self.enable_cube:
                cube_result = yield from self._cube_phase()
                if cube_result:
                    game_result = cube_result
                    break

            self.roll_dice()
            yield from self.emit(self.events.roll_dice(self.dice, self.turn, self.get_player_type(self.turn)))

            yield from self._play_turn_moves(player, self.dice, stepwise)

            yield from self.emit(self.events.turn_end(1 - self.turn, self.state))

            self.next_turn()
            turns_played += 1
            game_result = self.game_finished()

        if game_result:
            winner, points, cube_value, result_type = game_result
            yield from self.emit(self.events.game_over(
                self.state, winner, self.get_player_type(winner), points, self.cube_value, result_type
            ))

    def play_game(self, stepwise: bool = True):
        """
        Play a full game starting from initial dice roll.

        Args:
            stepwise (bool): Yield events stepwise if True.

        Yields:
            dict: Engine events describing the game progression.
        """
        d0, d1 = self.roll_start_dice()
        yield from self.emit(self.events.start_roll((d0, d1), self.turn))
        yield from self.play_from_state(stepwise=stepwise)
