# =========================================================
# --- players_player.py ---
# =========================================================

from abc import ABC, abstractmethod
from typing import List, Optional

from core.moves import SingleMoveType, SingleMove, TurnMove
from core.state import BackgammonState


# =========================================================

class Player(ABC):
    """
    Abstract base class for a Backgammon player.

    Attributes:
        id (Optional[int]): Player index (0 or 1). Initialized in constructor.
    """

    def __init__(self, id: Optional[int] = None):
        """
        Initialize a player with an optional ID.

        Args:
            id (Optional[int]): Player index (0 or 1). Defaults to None.
        """
        self.id: Optional[int] = id

    @abstractmethod
    def select_move(
        self,
        moves: List[TurnMove],
        state: BackgammonState,
        dice: List[int]
    ) -> Optional[TurnMove]:
        """
        Select a move from a list of legal moves.

        Args:
            moves (List[TurnMove]): List of legal turn moves.
            state (BackgammonState): Current game state.
            dice (List[int]): Dice rolled for this turn.

        Returns:
            Optional[TurnMove]: Selected turn move, or None if no move possible.
        """
        pass

    @abstractmethod
    def offer_double(self, cube_value: int) -> bool:
        """
        Decide whether to offer a doubling cube.

        Args:
            cube_value (int): Current cube value.

        Returns:
            bool: True if the player wants to offer a double, False otherwise.
        """
        return False

    @abstractmethod
    def accept_double(self, cube_value: int) -> bool:
        """
        Decide whether to accept a doubling cube offered by opponent.

        Args:
            cube_value (int): Current cube value.

        Returns:
            bool: True if the player accepts the double, False otherwise.
        """
        return True
