# =========================================================
# --- core_state.py ---
# =========================================================

import numpy as np
import random
import copy
from typing import Optional, List, Dict, Any, Tuple

from .board import BOARD_START, BOARD_END, BAR_FIELD, STONE, NUM_OF_ALL_STONES, DEFAULT_POSITIONS
from .moves import SingleMoveType, SingleMove
from .state_invariants import assert_state_invariant

from utils.bitmask import remove_from_mask, bits_from_indices, set_bit, clear_bit  

# =========================================================

class BackgammonMovesMixin:
    """
    Mixin class providing all stone-moving operations:
    - moving, adding, removing stones
    - applying and undoing single moves and turns
    """

    def move_stone(self, start: int, target: int, player: int) -> None:
        """Move a stone from start to target for the given player."""
        self._remove_stone(start, player)
        self._add_stone(target, player)
        self._assert("_move_stone")

    def undo_stone_move(self, start: int, target: int, player: int) -> None:
        """Undo a previously executed stone move."""
        self.move_stone(target, start, player)
        self._assert("_undo_stone_move")

    def hit_stone(self, start: int, target: int, player: int) -> None:
        """Hit opponent's stone at target and move player's stone there."""
        opp = 1 - player
        self.move_stone(target, BAR_FIELD[opp], opp)
        self.move_stone(start, target, player)

    def undo_hit_stone(self, start: int, target: int, player: int) -> None:
        """Undo a previously executed hit move."""
        opp = 1 - player
        self.undo_stone_move(start, target, player)
        self.undo_stone_move(target, BAR_FIELD[opp], opp)

    def bear_off(self, point: int, player: int) -> None:
        """Bear off a stone from the board for the given player."""
        old_count = self.bear_off_stones[player]
        self._remove_stone(point, player)
        self.bear_off_stones[player] += 1
        new_count = self.bear_off_stones[player]

        self.zobrist_hash ^= ZOBRIST_TABLE[26 + player][player][old_count]
        self.zobrist_hash ^= ZOBRIST_TABLE[26 + player][player][new_count]

    def undo_bear_off(self, point: int, player: int) -> None:
        """Undo a previously executed bear-off move."""
        old_count = self.bear_off_stones[player]
        self.bear_off_stones[player] -= 1
        new_count = self.bear_off_stones[player]

        self._add_stone(point, player)

        self.zobrist_hash ^= ZOBRIST_TABLE[26 + player][player][old_count]
        self.zobrist_hash ^= ZOBRIST_TABLE[26 + player][player][new_count]

    def apply_move(self, move: SingleMove) -> bool:
        """
        Apply a single move to the state.

        Args:
            move (SingleMove): The move to apply.

        Returns:
            bool: True if move applied successfully, False if move is None.
        """
        if not move:
            return False

        if move.move_type == SingleMoveType.NORMAL:
            self.move_stone(move.from_point, move.to_point, move.player)
        elif move.move_type == SingleMoveType.HIT:
            self.hit_stone(move.from_point, move.to_point, move.player)
        elif move.move_type == SingleMoveType.BEAR_OFF:
            self.bear_off(move.from_point, move.player)  

        return True

    def undo_move(self, move: SingleMove) -> None:
        """
        Undo a previously applied move.

        Args:
            move (SingleMove): The move to undo.
        """
        assert move is not None

        if move.move_type == SingleMoveType.NORMAL:
            self.undo_stone_move(move.from_point, move.to_point, move.player)
        elif move.move_type == SingleMoveType.HIT:
            self.undo_hit_stone(move.from_point, move.to_point, move.player)
        elif move.move_type == SingleMoveType.BEAR_OFF:
            self.undo_bear_off(move.from_point, move.player)


# =========================================================
# Zobrist hashing initialization
# =========================================================

ZOBRIST_TABLE = [[[random.getrandbits(64) for _ in range(16)] for _ in range(2)] for _ in range(26)]
ZOBRIST_TABLE += [[[random.getrandbits(64) for _ in range(16)] for _ in range(2)] for _ in range(2)]
ZOBRIST_PLAYER = [random.getrandbits(64), random.getrandbits(64)]

# =========================================================

class BackgammonState(BackgammonMovesMixin):
    """
    Represents the complete mutable Backgammon game state.

    Attributes:
        board (np.ndarray): Array of 26 integers representing stones on each point.
        bear_off_stones (np.ndarray): Array of 2 integers for stones borne off per player.
        _occ_mask (List[int]): Occupancy masks for each player.
        _blocked_mask (List[int]): Blocked masks for each player.
        turn (int): Current active player (0 or 1).
        zobrist_hash (int): Zobrist hash of the current state.
        debug (bool): Enable state invariant assertions.
    """

    def __init__(self, positions: Optional[List[List[Tuple[int,int]]]] = None, start_player: int = 0, debug: bool = False):
        self.debug: bool = debug        
        
        self.board: np.ndarray = np.zeros(26, dtype=np.int8)
        self.bear_off_stones: np.ndarray = np.zeros(2, dtype=np.int8)

        self._occ_mask: List[np.uint32] = [np.uint32(0), np.uint32(0)]
        self._blocked_mask: List[np.uint32] = [np.uint32(0), np.uint32(0)]

        self.start_game(positions, start_player)
        self.zobrist_hash: int = 0
        self.update_zobrist_hash()
    
    # ---------- Setup / Copy ----------
    def copy(self) -> "BackgammonState":
        """Return a deep copy of the current game state."""
        new_state = BackgammonState()
        new_state.board = copy.deepcopy(self.board)
        new_state.bear_off_stones = copy.deepcopy(self.bear_off_stones)
        new_state._occ_mask = self._occ_mask.copy()
        new_state._blocked_mask = self._blocked_mask.copy()
        new_state.turn = self.turn
        new_state.zobrist_hash = self.zobrist_hash
        return new_state

    def reset_board(self) -> None:
        """Reset the board, masks, and bear-off counters to empty state."""
        self.board[:] = 0
        self.bear_off_stones[:] = 0
        self._occ_mask[:] = [0, 0]
        self._blocked_mask[:] = [0, 0]
  
    def start_game(self, positions: Optional[List[List[Tuple[int,int]]]] = None, start_player: int = 0) -> None:
        """Initialize a new game with optional starting positions and starting player."""
        self.reset_board()
        self.turn = start_player
        if positions is None:
            positions = DEFAULT_POSITIONS
        self.place_stones_from_list(positions)
        self._recompute_masks()

    # ---------- Properties ----------
    @property
    def opp(self) -> int:
        """Return opponent player index (0 or 1)."""
        return 1 - self.turn

    @property
    def stone_player(self) -> int:
        """Return the stone sign of the active player (+1 or -1)."""
        return STONE[self.turn]

    @property
    def stone_opp(self) -> int:
        """Return the stone sign of the opponent (+1 or -1)."""
        return STONE[self.opp]

    @property
    def masks(self) -> Dict[str, int]:
        """
        Return a dictionary of bitmasks for the current board state:
        - occupied: points occupied by active player
        - blocked: points blocked by active player
        - hittable: opponent stones that can be hit
        - unprotected: active player stones unprotected by opponent
        """
        return {
            'occupied': self._occ_mask[self.turn],
            'blocked': self._blocked_mask[self.turn],
            'hittable': remove_from_mask(self._occ_mask[self.opp], self._blocked_mask[self.turn]),
            'unprotected': remove_from_mask(self._occ_mask[self.turn], self._blocked_mask[self.opp]),
        }

    def is_on_board(self, point: int) -> bool:
        """Check if a point index is on the board."""
        return BOARD_START <= point <= BOARD_END

    def num_of_stones(self, point: int, player: Optional[int] = None) -> int:
        """
        Return the number of stones on a given point for a specific player.
        
        Args:
            point (int): Board point index.
            player (Optional[int]): Player index (0 or 1). If None, no count is returned.
        
        Returns:
            int: Number of stones of the player at the point.
        """
        if player is not None:
            sign = STONE[player]
            val = self.board[point] * sign
            return val if val > 0 else 0

    # ---------- Masks / Updates ----------
    def _update_occupied(self, point: int) -> None:
        """Update the occupancy bitmask for a given point."""
        for player in (0,1):
            if self.num_of_stones(point, player) > 0:
                self._occ_mask[player] = set_bit(point, self._occ_mask[player])
            else:
                self._occ_mask[player] = clear_bit(point, self._occ_mask[player])
 
    def _update_blocked(self, point: int) -> None:
        """Update the blocked bitmask for a given point."""
        for player in (0,1):
            opp = 1 - player
            if self.num_of_stones(point, opp) >= 2:
                self._blocked_mask[player] = set_bit(point, self._blocked_mask[player])
            else:
                self._blocked_mask[player] = clear_bit(point, self._blocked_mask[player])
    
    def _recompute_masks(self) -> None:
        """Recompute all occupancy and blocked masks for both players."""
        for player in (0, 1):
            opp = 1 - player
            occ = np.flatnonzero(self.board * STONE[player] > 0)
            blocked = np.flatnonzero(self.board * STONE[opp] >= 2)
            self._occ_mask[player] = bits_from_indices(occ)
            self._blocked_mask[player] = bits_from_indices(blocked)

    # ---------- Stone primitives ----------
    def _add_stone(self, point: int, player: int) -> None:
        """Add a stone to a point for a player and update masks and hash."""
        old_count = self.num_of_stones(point, player)
        self.board[point] += STONE[player]
        new_count = self.num_of_stones(point, player)

        self.zobrist_hash ^= ZOBRIST_TABLE[point][player][old_count]
        self.zobrist_hash ^= ZOBRIST_TABLE[point][player][new_count]

        self._update_occupied(point)
        self._update_blocked(point)

    def _remove_stone(self, point: int, player: int) -> int:
        """Remove a stone from a point for a player and update masks and hash.
        
        Returns:
            int: The stone removed (+1 or -1)
        """
        old_count = self.num_of_stones(point, player)
        if old_count == 0:
            return 0
        self.board[point] -= STONE[player]
        new_count = self.num_of_stones(point, player)

        self.zobrist_hash ^= ZOBRIST_TABLE[point][player][old_count]
        self.zobrist_hash ^= ZOBRIST_TABLE[point][player][new_count]

        self._update_occupied(point)
        self._update_blocked(point)
        return STONE[player]

    # ---------- Turn ----------
    def switch_turn(self) -> None:
        """Switch the active player (0 <-> 1)."""
        self.turn = 1 - self.turn

    # ---------- Serialization ----------
    def place_stones_from_list(self, positions: List[List[Tuple[int,int]]]) -> None:
        """Place stones on the board given a serialized position list."""
        for player in (0, 1):
            total = 0
            for point, count in positions[player]:
                if point == -1:
                    self.bear_off_stones[player] += count
                else:
                    self.board[point] = count * STONE[player]
                    total += count
            if total + self.bear_off_stones[player] != NUM_OF_ALL_STONES[player]:
                raise ValueError("Invalid number of stones")
        self._recompute_masks()

    def state_to_list(self) -> List[List[Tuple[int,int]]]:
        """Serialize the board into a list of positions per player."""
        positions: List[List[Tuple[int,int]]] = [[], []]
        for point, stones in enumerate(self.board):
            if stones < 0:
                positions[0].append((point, -stones))
            elif stones > 0:
                positions[1].append((point, stones))
        for player in (0, 1):
            if self.bear_off_stones[player] > 0:
                positions[player].append((-1, self.bear_off_stones[player]))
        return positions

    # ---------- Zobrist / Hash ----------
    def __hash__(self) -> int:
        """Return the Zobrist hash of the current state."""
        return self.zobrist_hash

    def __eq__(self, other: Any) -> bool:
        """Check equality with another BackgammonState."""
        return (
            np.array_equal(self.board, other.board) and
            np.array_equal(self.bear_off_stones, other.bear_off_stones) and
            self.turn == other.turn
        )

    def update_zobrist_hash(self) -> None:
        """Recompute the Zobrist hash of the current state."""
        h = 0
        for point in range(26):
            for player in (0, 1):
                count = self.num_of_stones(point, player)
                if count > 0:
                    h ^= ZOBRIST_TABLE[point][player][count]
        for player in (0, 1):
            count = self.bear_off_stones[player]
            if count > 0:
                h ^= ZOBRIST_TABLE[26 + player][player][count]
        h ^= ZOBRIST_PLAYER[self.turn]
        self.zobrist_hash = h

    # ---------- Debug / Assertions ----------
    def _assert(self, where: str = "") -> None:
        """Assert state invariants if debug mode is active."""
        if self.debug:
            assert_state_invariant(self, where)
