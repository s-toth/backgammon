# =========================================================
# --- core_moves.py ---
# =========================================================

from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Tuple

# =========================================================

class SingleMoveType(Enum):
    """
    Enumeration of possible move types in Backgammon.

    Attributes:
        NORMAL: Standard move from one point to another.
        HIT: Move that hits an opponent's blot.
        BEAR_OFF: Move that bears a stone off the board.
    """
    NORMAL = 1
    HIT = 2
    BEAR_OFF = 3


@dataclass(frozen=True)
class SingleMove:
    """
    Represents a single atomic move in Backgammon.

    Attributes:
        player (int): The player making the move (0 or 1).
        from_point (int): Starting point index of the move.
        to_point (int): Target point index of the move.
        move_type (SingleMoveType): Type of the move (NORMAL, HIT, BEAR_OFF).
        die (int): Die value used for the move.
    """
    player: int
    from_point: int
    to_point: int
    move_type: SingleMoveType
    die: int

    def __str__(self) -> str:
        """Return a human-readable string representation of the move."""
        return f"{self.from_point}".rjust(2) + " > " + f"{self.to_point}".rjust(2) + f" ({self.die}, {self.move_type.name})"

    def __repr__(self) -> str:
        """Return a formal string representation (same as __str__)."""
        return str(self)


@dataclass(frozen=True)
class TurnMove:
    """
    Represents a full turn consisting of one or more single moves.

    Attributes:
        single_moves (List[SingleMove]): Ordered list of single moves executed during the turn.
    """
    single_moves: List[SingleMove]

    def __iter__(self) -> Iterator[SingleMove]:
        """
        Return an iterator over the single moves.

        Returns:
            Iterator[SingleMove]: Iterator over all single moves in the turn.
        """
        return iter(self.single_moves)

    def __len__(self) -> int:
        """
        Return the number of single moves in the turn.

        Returns:
            int: Number of moves.
        """
        return len(self.single_moves)

    def iter_with_index(self) -> Iterator[Tuple[int, SingleMove]]:
        """
        Generator that yields each single move with its index.

        Yields:
            Tuple[int, SingleMove]: Index and the corresponding SingleMove.
        """
        for idx, smove in enumerate(self.single_moves):
            yield idx, smove

    def __str__(self) -> str:
        """
        Return a string representation of all moves in the turn, separated by ' | '.

        Returns:
            str: Human-readable string of the turn's moves.
        """
        return " | ".join(str(smove) for smove in self.single_moves)

    def __repr__(self) -> str:
        """Return a formal string representation (same as __str__)."""
        return str(self)
