# =========================================================
# --- resolver.py ---
# =========================================================

import os
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

from core.board import BAR_FIELD, BEAR_OFF_ANCHOR 
from core.moves import SingleMoveType, SingleMove, TurnMove
from core.engine import GameEngine

# =========================================================

class GnuBGMoveResolver:
    """
    Helper class to translate GNUBG move strings into engine Moves.
    
    Handles single dice moves, split moves for non-doubles, and double chains.
    Can also log applied moves to a file.
    """

    def __init__(
        self,
        engine: GameEngine,
        dice_dict: Dict[str, Optional[List[int]]],
        gnubg_prop: Dict[str, Any],
        log_file: Optional[str] = None
    ) -> None:
        """
        Initialize the move resolver.

        Args:
            engine: The game engine instance.
            dice_dict: Dictionary mapping tokens to dice lists.
            gnubg_prop: GNUBG properties containing 'engine_id' and 'token'.
            log_file: Optional file path to log applied moves.
        """
        self.engine = engine
        self.dice_dict = dice_dict

        self.engine_id = gnubg_prop["engine_id"]
        self.token = gnubg_prop["token"]

        self.process_dice_dict()
     
        self.log_file = log_file
        if log_file:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
     
    def process_dice_dict(self) -> None:
        """
        Double dice in case of doubles (e.g., [3,3] -> [3,3,3,3]).
        """
        for token, d in self.dice_dict.items():
            if d and d[0] == d[1]:
                self.dice_dict[token] += d

    def gnubg_to_engine_point(self, p: str) -> int:
        """
        Convert a GNUBG point string to an engine point index.

        Args:
            p: Point string, can be 'bar', 'off', or a number as string.

        Returns:
            Engine point index.
        """
        p_clean = p.replace("*", "")
        if p_clean == "bar":
            return BAR_FIELD[self.engine_id]
        if p_clean == "off":
            return BEAR_OFF_ANCHOR[self.engine_id]
        return BEAR_OFF_ANCHOR[self.engine_id] - int(p_clean)

    def detect_move_type(self, to_token: str, to_point: int) -> SingleMoveType:
        """
        Determine the move type based on target token and engine point.

        Args:
            to_token: Target token string.
            to_point: Engine point index.

        Returns:
            SingleMoveType enum value.
        """
        if "*" in to_token:
            return SingleMoveType.HIT
        if to_point == BEAR_OFF_ANCHOR[self.engine_id]:
            return SingleMoveType.BEAR_OFF
        return SingleMoveType.NORMAL

    def _log_move(self, sm: SingleMove) -> None:
        """
        Log a move to the log file if enabled.

        Args:
            sm: SingleMove object to log.
        """
        if self.log_file:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(
                    f"{datetime.now().strftime('%H:%M:%S')} - Applied Move: "
                    f"{sm.from_point} -> {sm.to_point}, die={sm.die}, type={sm.move_type}\n"
                )

    def _try_single_die_move(self, from_point: int, to_point: int, move_type: SingleMoveType) -> bool:
        """
        Try to apply a move using a single die.

        Args:
            from_point: Engine starting point.
            to_point: Engine target point.
            move_type: Type of move.

        Returns:
            True if move applied successfully, False otherwise.
        """
        dice = self.dice_dict[self.token]
        if not dice:
            return False
        
        die = abs(to_point - from_point)
        candidates = [d for d in dice if d >= die]
        if not candidates:
            return False
        die = min(candidates)

        sm = SingleMove(player=self.engine_id, from_point=from_point, to_point=to_point, die=die, move_type=move_type)
        self.engine.state.apply_move(sm)
        self._log_move(sm)

        dice.remove(die)
        if len(dice) == 0:
            self.dice_dict[self.token] = None
        return True

    def _try_split_non_double(self, from_point: int, to_point: int, move_type: SingleMoveType) -> bool:
        """
        Try to split a move into two non-double dice moves.

        Args:
            from_point: Engine starting point.
            to_point: Engine target point.
            move_type: Move type for the second die.

        Returns:
            True if move applied successfully, False otherwise.
        """
        dice = self.dice_dict[self.token]
        if not dice or len(dice) < 2 or dice[0] == dice[1]:
            return False  

        d1, d2 = sorted(dice)
        for first_die, second_die in [(d1, d2), (d2, d1)]:
            mid = from_point + first_die
            if mid > to_point:  
                continue
            sm1 = SingleMove(player=self.engine_id, from_point=from_point, to_point=mid, die=first_die, move_type=SingleMoveType.NORMAL)
            sm2 = SingleMove(player=self.engine_id, from_point=mid, to_point=to_point, die=second_die, move_type=move_type)
            turn = TurnMove([sm1, sm2])
            if turn in self.engine.legal_moves:
                self.engine.state.apply_move(sm1)
                self._log_move(sm1)
                self.engine.state.apply_move(sm2)
                self._log_move(sm2)
                self.dice_dict[self.token].clear()
                return True

        return False

    def _apply_double_chain(self, from_point: int, to_point: int, move_type: SingleMoveType) -> bool:
        """
        Apply moves using a double die repeatedly.

        Args:
            from_point: Engine starting point.
            to_point: Engine target point.
            move_type: Move type for the last move.

        Returns:
            True after applying moves.
        """
        dice = self.dice_dict[self.token]
        if not dice:
            return False
        die = dice[0]
        moves: List[SingleMove] = []

        step = -die if from_point > to_point else die
        fields = list(range(from_point, to_point, step))
        
        if not fields:
            moves.append(SingleMove(player=self.engine_id, from_point=from_point, to_point=to_point, die=die, move_type=move_type))
        else:
            for i in range(len(fields) - 1):
                moves.append(SingleMove(player=self.engine_id, from_point=fields[i], to_point=fields[i+1], die=die, move_type=SingleMoveType.NORMAL))
            moves.append(SingleMove(player=self.engine_id, from_point=fields[-1], to_point=to_point, die=die, move_type=move_type))

        for move in moves:
            self.engine.state.apply_move(move)
            self._log_move(move)

        return True

    def apply_moves(self, parsed_moves: List[List[str]]) -> None:
        """
        Apply a sequence of parsed GNUBG moves to the engine.

        Args:
            parsed_moves: List of move pairs [[from_token, to_token], ...].

        Raises:
            RuntimeError: If a move cannot be resolved.
        """
        for sm_lst in parsed_moves:
            from_token, to_token = sm_lst
            from_point = self.gnubg_to_engine_point(from_token)
            to_point = self.gnubg_to_engine_point(to_token)
            move_type = self.detect_move_type(to_token, to_point)

            if self._try_single_die_move(from_point, to_point, move_type):
                continue
            if self._try_split_non_double(from_point, to_point, move_type):
                continue
            if self._apply_double_chain(from_point, to_point, move_type):
                continue

            raise RuntimeError(f"Cannot resolve GNUBG-move: {from_token}/{to_token}")
