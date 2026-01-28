# =========================================================
# --- cli_boardDisplay.py ---
# =========================================================

from typing import Optional, Set, Iterable
from core.board import BOARD_START, BOARD_END, BAR_FIELD, HOME_START, HOME_END
from core.state import BackgammonState

from .cliColors import TColor, PLAYER
from .cliUtils import clear

# =========================================================

class BoardDisplay:
    """
    Class for displaying the Backgammon board in the terminal.

    Attributes:
        state (BackgammonState): The current game state.
        clear_screen (bool): Whether to clear the screen before drawing.
        field_size (int): Width of a board point for formatting.
        use_color (bool): Whether to use colored output.
    """

    def __init__(self, state: 'BackgammonState', clear_screen: bool = True, use_color: bool = True) -> None:
        """
        Initializes the BoardDisplay.

        Args:
            state (BackgammonState): The current game state.
            clear_screen (bool, optional): Whether to clear the screen before drawing. Defaults to True.
            use_color (bool, optional): Whether to use colored output. Defaults to True.
        """
        self.state: 'BackgammonState' = state
        self.clear_screen: bool = clear_screen
        self.field_size: int = 3  # Width of each board point for alignment
        self.use_color: bool = use_color

    def _point_str(self, point: int) -> str:
        """
        Returns a formatted string representing a board point, including colored stones.

        Args:
            point (int): The board point number.

        Returns:
            str: Formatted string for the point.
        """
        blue_stones = self.state.num_of_stones(point, 0)
        red_stones = self.state.num_of_stones(point, 1)

        if blue_stones:
            s = f"B{blue_stones}".rjust(self.field_size)  # Right-align the text
            return f"{TColor.BLUE}{s}{TColor.RESET}" if self.use_color else s
        if red_stones:
            s = f"R{red_stones}".rjust(self.field_size)
            return f"{TColor.RED}{s}{TColor.RESET}" if self.use_color else s
        return "..."  # Empty point

    def _color_index(
        self,
        point: int,
        from_points: Optional[Iterable[int]] = None,
        to_points: Optional[Iterable[int]] = None
    ) -> str:
        """
        Returns a formatted point string with color coding for moves.

        - GREEN: point is a source (stone moving from)
        - YELLOW: point is a target (stone moving to)
        - PURPLE: point is both source and target
        - Default: no move highlights

        Args:
            point (int): The board point number.
            from_points (Optional[Iterable[int]]): Points where stones are moving from.
            to_points (Optional[Iterable[int]]): Points where stones are moving to.

        Returns:
            str: Colored or formatted point string.
        """
        from_points = from_points or set()
        to_points = to_points or set()

        s = f"{point}".rjust(self.field_size)
        # Apply color coding based on move highlights
        if point in from_points and point in to_points:
            return f"{TColor.PURPLE}{s}{TColor.RESET}" if self.use_color else s
        if point in from_points:
            return f"{TColor.GREEN}{s}{TColor.RESET}" if self.use_color else s
        if point in to_points:
            return f"{TColor.YELLOW}{s}{TColor.RESET}" if self.use_color else s
        return s

    def draw_points(self, from_points: Optional[Set[int]] = None, to_points: Optional[Set[int]] = None) -> None:
        """
        Draws all board points including move color highlights.

        The board is split into upper and lower halves. Each half shows:
        - Index row (point numbers with move color highlights)
        - Stone row (number of stones at each point)

        Args:
            from_points (Optional[Set[int]]): Points stones are moving from.
            to_points (Optional[Set[int]]): Points stones are moving to.
        """
        from_points = from_points or set()
        to_points = to_points or set()

        half = (BOARD_END - BOARD_START + 1) // 2
        sep = " "
        home_format = (half - 1) * len(sep) + half * self.field_size

        # Upper half (typically Red home)
        upper_range = range(half + 1, BOARD_END + 1)
        upper_idx = sep.join(self._color_index(p, from_points, to_points) for p in upper_range)
        upper_points = sep.join(self._point_str(p) for p in upper_range)
        print(f"{TColor.RED if self.use_color else ''}HOME R ({HOME_START[1]}-{HOME_END[1]})".rjust(home_format) + (TColor.RESET if self.use_color else ''))
        print(upper_idx)    # Index row with move highlights
        print(upper_points) # Stone count row

        # Lower half (typically Blue home, reversed order)
        lower_range = range(half, BOARD_START - 1, -1)
        lower_points = sep.join(self._point_str(p) for p in lower_range)
        lower_idx = sep.join(self._color_index(p, from_points, to_points) for p in lower_range)
        print(lower_points)
        print(lower_idx)
        print(f"{TColor.BLUE if self.use_color else ''}HOME B ({HOME_START[0]}-{HOME_END[0]})".rjust(home_format) + (TColor.RESET if self.use_color else ''))

    def draw_bar(self) -> None:
        """
        Draws the bar (captured stones) for both players.
        """
        blue, red = 0, 1
        b_count = self.state.num_of_stones(BAR_FIELD[blue], blue)
        r_count = self.state.num_of_stones(BAR_FIELD[red], red)
        print(f"Bar  "
              f"{TColor.BLUE + 'B:' + str(b_count) + TColor.RESET if self.use_color else 'B:'+str(b_count)} | "
              f"{TColor.RED + 'R:' + str(r_count) + TColor.RESET if self.use_color else 'R:'+str(r_count)}")

    def draw_bear_off(self) -> None:
        """
        Draws the bear-off area (stones that have been removed from the board) for both players.
        """
        blue, red = 0, 1
        print(f"Bear "
              f"{TColor.BLUE + 'B:' + str(self.state.bear_off_stones[blue]) + TColor.RESET if self.use_color else 'B:'+str(self.state.bear_off_stones[blue])} | "
              f"{TColor.RED + 'R:' + str(self.state.bear_off_stones[red]) + TColor.RESET if self.use_color else 'R:'+str(self.state.bear_off_stones[red])}")

    def draw_all(self, from_points: Optional[Set[int]] = None, to_points: Optional[Set[int]] = None) -> None:
        """
        Draws the entire board, including points, bar, and bear-off areas.

        Args:
            from_points (Optional[Set[int]]): Points stones are moving from.
            to_points (Optional[Set[int]]): Points stones are moving to.
        """
        if self.clear_screen:
            clear()  # Clear terminal for clean board display
        print(f"{TColor.BOLD + '--- Board ---' + TColor.RESET if self.use_color else '--- Board ---'}")
        self.draw_points(from_points, to_points)
        self.draw_bar()
        self.draw_bear_off()
