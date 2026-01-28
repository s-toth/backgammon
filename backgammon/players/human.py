# =========================================================
# --- players_human.py ---
# =========================================================

from typing import Callable, List, Optional

from core.moves import SingleMoveType, SingleMove, TurnMove
from core.state import BackgammonState
from core.engine import CubeDecision

from .player import Player

# =========================================================

class HumanPlayer(Player):
    """
    Human-controlled player class.

    Allows custom input functions for move selection and cube decisions.
    
    Attributes:
        id (int): Player index (0 or 1).
        name (str): Player display name.
        input_func (Callable[[List[TurnMove], BackgammonState, List[int]], Optional[TurnMove]]):
            Function used to select a move from available turn moves.
        input_offer (Callable[[str], str]): Function to query the player for doubling cube offer.
        input_accept (Callable[[str], str]): Function to query the player for accepting the cube.
    """

    def __init__(
        self,
        id: int,
        name: str = "Human Player",
        input_func: Callable[[List[TurnMove], BackgammonState, List[int]], Optional[TurnMove]] = input,
        input_offer: Callable[[str], str] = input,
        input_accept: Callable[[str], str] = input,
    ):
        """
        Initialize a human player.

        Args:
            id (int): Player index (0 or 1).
            name (str, optional): Player display name. Defaults to "Human Player".
            input_func (callable, optional): Function to select a move. Defaults to input().
            input_offer (callable, optional): Function to offer cube. Defaults to input().
            input_accept (callable, optional): Function to accept cube. Defaults to input().
        """
        self.id: int = id
        self.name: str = name
        self.input_func = input_func
        self.input_offer = input_offer
        self.input_accept = input_accept

    def __str__(self) -> str:
        """
        Return string representation of the player.

        Returns:
            str: Player name with ID.
        """
        return f"{self.name}_({self.id})"

    def select_move(
        self,
        moves: List[TurnMove],
        state: BackgammonState,
        dice: List[int],
    ) -> Optional[TurnMove]:
        """
        Prompt human player to select a move from the list of legal turn moves.

        Args:
            moves (List[TurnMove]): Available turn moves.
            state (BackgammonState): Current game state.
            dice (List[int]): Current dice roll.

        Returns:
            Optional[TurnMove]: Selected move or None if skipped.
        """
        return self.input_func(moves, state, dice)

    def offer_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Ask human player whether to offer a doubling cube.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if player offers to double, False otherwise.
        """
        return (
            self.input_offer(f"\n Offer double (cube={cube_value})? [y/N]: ")
            .strip()
            .lower()
            == "y"
        )

    def accept_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Ask human player whether to accept a doubling cube.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if player accepts the double, False if declines.
        """
        return (
            self.input_accept(f"\n Accept double to {cube_value * 2}? [Y/n]: ")
            .strip()
            .lower()
            != "n"
        )

