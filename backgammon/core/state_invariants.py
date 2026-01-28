# =========================================================
# --- core_state_invariants.py ---
# =========================================================

import numpy as np
from typing import Any, Optional

from .board import BOARD_START, BOARD_END, BAR_FIELD, STONE, NUM_OF_ALL_STONES
from utils.bitmask import bits_from_indices

# =========================================================

def assert_stone_invariant(state: Any, where: str = "") -> None:
    """
    Check that the total number of stones for each player is consistent.

    This includes stones on the board, on the bar, and borne off stones.

    Args:
        state: The BackgammonState object to check.
        where: Optional description of where the check is performed (for debugging).

    Raises:
        AssertionError: If the total stones for a player do not equal NUM_OF_ALL_STONES.
    """
    for p in (0, 1):
        board = sum(state.num_of_stones(i, p) for i in range(BOARD_START, BOARD_END + 1))
        bar = abs(state.board[BAR_FIELD[p]])
        total = board + bar + state.bear_off_stones[p]

        if total != NUM_OF_ALL_STONES[p]:
            raise AssertionError(
                f"[STONE LOST] Player {p}: {total}/{NUM_OF_ALL_STONES[p]} at {where}\n"
                f"Board={board}, Bar={bar}, BearOff={state.bear_off_stones[p]}"
            )


def assert_mask_invariant(state: Any, where: str = "") -> None:
    """
    Check that the occupancy and blocked masks are consistent with the board.

    Args:
        state: The BackgammonState object to check.
        where: Optional description of where the check is performed (for debugging).

    Raises:
        AssertionError: If any occupancy or blocked mask does not match the board.
    """
    for p in (0, 1):
        occ = bits_from_indices(np.flatnonzero(state.board * STONE[p] > 0))
        if state._occ_mask[p] != occ:
            raise AssertionError(
                f"[MASK DESYNC] occupied mask mismatch at {where}\n"
                f"Player={p}\n"
                f"Current ={bin(state._occ_mask[p])}\n"
                f"Expected={bin(occ)}"
            )

        opp = 1 - p
        blocked = bits_from_indices(np.flatnonzero(state.board * STONE[opp] >= 2))
        if state._blocked_mask[p] != blocked:
            raise AssertionError(
                f"[MASK DESYNC] blocked mask mismatch at {where}\n"
                f"Player={p}"
            )


def assert_state_invariant(state: Any, where: str = "") -> None:
    """
    Perform full invariant check for a Backgammon state.

    This includes:
    - Stone count consistency
    - Occupancy and blocked mask consistency

    Args:
        state: The BackgammonState object to check.
        where: Optional description of where the check is performed (for debugging).

    Raises:
        AssertionError: If any invariant fails.
    """
    assert_stone_invariant(state, where)
    assert_mask_invariant(state, where)

