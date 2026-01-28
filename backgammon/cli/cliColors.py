# =========================================================
# --- cli_cliColors.py ---
# =========================================================

from typing import Tuple

# =========================================================

class TColor:
    """
    ANSI escape codes for terminal text coloring.

    Attributes:
        BLUE (str): Blue color for player 0.
        RED (str): Red color for player 1.
        GREEN (str): Highlight color for "from" point.
        YELLOW (str): Highlight color for "to" point.
        PURPLE (str): Highlight color for combined "from + to".
        RESET (str): Reset color to default terminal color.
        BOLD (str): Bold text formatting.
    """
    BLUE: str    = "\033[94m"   # Player 0
    RED: str     = "\033[91m"   # Player 1
    GREEN: str   = "\033[92m"   # Move source highlight
    YELLOW: str  = "\033[93m"   # Move target highlight
    PURPLE: str  = "\033[95m"   # Source + target highlight
    RESET: str   = "\033[0m"    # Reset formatting
    BOLD: str    = "\033[1m"    # Bold text


PLAYER: Tuple[str, str] = (
    f"{TColor.BLUE}(B)lue{TColor.RESET}",  # Player 0 display string
    f"{TColor.RED}(R)ed{TColor.RESET}"     # Player 1 display string
)
