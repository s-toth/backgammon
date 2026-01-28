# =========================================================
# --- core_undo.py ---
# =========================================================

from collections import deque
from typing import Optional

from .state import BackgammonState
from .moves import SingleMove

# =========================================================

class Undo:
    """
    Hybrid undo manager for Backgammon.

    Maintains both:
        - move-based history (atomic SingleMove undo)
        - snapshot-based history (full board snapshots)
    """

    def __init__(self, max_moves: int = 100, max_snapshots: int = 10) -> None:
        """
        Initialize the Undo manager.

        Args:
            max_moves: Maximum number of moves to store for undo.
            max_snapshots: Maximum number of board snapshots to store.
        """
        self.move_history: deque[SingleMove] = deque(maxlen=max_moves)
        self.snapshots: deque[BackgammonState] = deque(maxlen=max_snapshots)

    def record_move(self, move: SingleMove) -> None:
        """
        Record a single move for later undo.

        Args:
            move: The SingleMove to record.

        Raises:
            ValueError: If move is None.
        """
        if move is None:
            raise ValueError("Move cannot be None")
        self.move_history.append(move)

    def undo_last_move(self, state: BackgammonState) -> SingleMove:
        """
        Undo the last recorded move or snapshot.

        If no moves are available, falls back to the last snapshot.

        Args:
            state: The current BackgammonState to revert.

        Returns:
            The SingleMove that was undone.

        Raises:
            ValueError: If there is nothing to undo.
        """
        if self.move_history:
            move: SingleMove = self.move_history.pop()
            state.undo_move(move)
            return move
        elif self.snapshots:
            self.undo_last_snapshot(state)
        else:
            raise ValueError("Nothing to undo")

    def record_snapshot(self, state: BackgammonState) -> None:
        """
        Record a full snapshot of the current state.

        Args:
            state: The BackgammonState to snapshot.
        """
        self.snapshots.append(state.copy())

    def undo_last_snapshot(self, state: BackgammonState) -> None:
        """
        Revert the state to the last recorded snapshot.

        Args:
            state: The BackgammonState to revert.

        Raises:
            ValueError: If no snapshots are available.
        """
        if not self.snapshots:
            raise ValueError("No snapshots available")

        snapshot: BackgammonState = self.snapshots.pop()
        state.board[:] = snapshot.board
        state.bear_off_stones[:] = snapshot.bear_off_stones
        state._occ_mask = snapshot._occ_mask.copy()
        state._blocked_mask = snapshot._blocked_mask.copy()
        state._recompute_masks()
        state.turn = snapshot.turn
