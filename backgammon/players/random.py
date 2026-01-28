# =========================================================
# --- players_random.py ---
# =========================================================

import random
from typing import List, Optional

from core.moves import TurnMove
from core.state import BackgammonState

from .player import Player
from .valuation import Valuation

# =========================================================

class RandomPlayer(Player):
    """
    Random player with optional evaluation-based cube decisions.

    Attributes:
        id (int): Player index (0 or 1).
        rng (random.Random): Random number generator.
        eval (Optional[Valuation]): Optional evaluation instance for cube heuristics.
    """

    def __init__(self, id: int, rng: Optional[random.Random] = None, valuation: Optional[Valuation] = None):
        """
        Initialize a RandomPlayer.

        Args:
            id (int): Player index (0 or 1).
            rng (Optional[random.Random]): Optional RNG instance. If None, a new RNG is created.
            valuation (Optional[Valuation]): Optional Valuation instance for cube decisions.
        """
        self.id: int = id
        self.rng: random.Random = rng or random.Random()
        self.eval: Optional[Valuation] = valuation

    def __str__(self) -> str:
        """Return a human-readable name for the player."""
        return f"Random player 🎲 {self.id}"

    def select_move(
        self,
        moves: List[TurnMove],
        state: BackgammonState,
        dice: List[int]
    ) -> Optional[TurnMove]:
        """
        Select a move randomly from available moves.

        Args:
            moves (List[TurnMove]): List of legal turn moves.
            state (BackgammonState): Current game state.
            dice (List[int]): Dice rolled for this turn.

        Returns:
            Optional[TurnMove]: Selected turn move, or None if no moves available.
        """
        if not moves:
            return None
        return self.rng.choice(moves)

    # ---------------- Cube heuristics ----------------
    def offer_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Decide whether to offer a doubling cube using evaluation heuristics.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if offering a double, False otherwise.
        """
        return self.eval.offer_double_heuristic(state, self.id) if self.eval else False

    def accept_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Decide whether to accept a doubling cube using evaluation heuristics.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if accepting the double, False otherwise.
        """
        return self.eval.accept_double_heuristic(state, self.id) if self.eval else True

     