# =========================================================
# --- core_board.py ---
# =========================================================

from utils.bitmask import set_all_bits

# =========================================================

"""
Board-related constants and initial configuration for Backgammon.

This module defines:
- Board points and bar locations
- Bear-off anchors
- Home board ranges
- Bitmasks for board regions
- Stone representation and movement directions
- Default starting positions
"""

#: Board point range (1–24 are normal playable points)
BOARD_START = 1
BOARD_END = 24

#: Bar positions for both players
#: Index 0 = Player 1's bar, Index 1 = Player 2's bar
BAR_FIELD = [25, 0]

#: Bear-off target points for both players
#: Player 0 bears off at point 0, Player 1 at point 25
BEAR_OFF_ANCHOR = [0, 25]
# Note: BEAR_OFF_ANCHOR matches the backgammon direction.
# Points 0 and 25 are used only for bear-off/bar logic, not for regular stones.

#: Home board ranges for each player
#: Player 0: points 1-6, Player 1: points 19-24
HOME_START = [1, 19]
HOME_END   = [6, 24]

#: Bitmask representing all playable points on the board
FULL_BOARD_MASK = set_all_bits(BOARD_START, BOARD_END)

#: Bitmasks for each player's home board
HOME_MASK = (
    set_all_bits(HOME_START[0], HOME_END[0]),  # Player 0 home mask
    set_all_bits(HOME_START[1], HOME_END[1]),  # Player 1 home mask
)

#: Bitmasks for outside home board (complement of home)
OUTSIDE_HOME_MASK = (
    HOME_MASK[0] ^ FULL_BOARD_MASK,
    HOME_MASK[1] ^ FULL_BOARD_MASK,
)

#: Total number of stones per player
NUM_OF_ALL_STONES = [15, 15]

#: Stone representation on the board
#: Negative for Player 0, positive for Player 1
STONE = (-1, 1)

#: Movement directions per player
#: Player 0 moves "down" (-1), Player 1 moves "up" (+1)
DIRECTION = (-1, 1)

#: Default starting positions
#: Each entry: list of (point, number_of_stones) for that player
#: Player 0: 2 stones on 24, 5 on 13, 3 on 8, 5 on 6
#: Player 1: 2 stones on 1, 5 on 12, 3 on 17, 5 on 19
DEFAULT_POSITIONS = [
    [(24, 2), (13, 5), (8, 3), (6, 5)],
    [(1, 2), (12, 5), (17, 3), (19, 5)],
]
