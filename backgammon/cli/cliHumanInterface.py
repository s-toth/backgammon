# =========================================================
# --- cli_cliHumanInterface.py ---
# =========================================================
import copy
from typing import List, Dict, Any

from core.moves import SingleMoveType, SingleMove, TurnMove
from core.state import BackgammonState
from core.generator import MoveTree

from .boardDisplay import BoardDisplay
from .cliUtils import interruptible_sleep, safe_input, clear

# =========================================================

class HumanMoveNavigator:
    """
    Provides an interactive CLI interface for human players to navigate
    possible turn moves and select a sequence of SingleMoves.
    """

    def __init__(self, state: BackgammonState, turn_moves: List[TurnMove], dice: List[int]):
        """
        Initialize the navigator with the game state, possible turn moves, and dice.

        Args:
            state (BackgammonState): Current board state.
            turn_moves (List[TurnMove]): List of legal turn moves (sequence of SingleMoves).
            dice (List[int]): Dice values available for this turn.
        """
        self.state: BackgammonState = state
        self.tree: MoveTree = MoveTree(turn_moves)
        self.board_display: BoardDisplay = BoardDisplay(state)
        self.current_path: List[SingleMove] = []  # moves the player has selected so far
        self.state_copy: BackgammonState = state.copy()
        self.dice: List[int] = dice.copy()
        self.dice_all: List[int] = dice.copy()

    # ---------------- Main method ----------------
    def navigate(self) -> TurnMove:
        """
        Start the interactive navigation to select a sequence of moves.

        Returns:
            TurnMove: The confirmed sequence of SingleMoves chosen by the human player.
        """
        node = self.tree.root

        while True:
            options: List[SingleMove] = list(node.keys())

            if not options:
                if self._handle_leaf():
                    return TurnMove(self.current_path)
                # Leaf reset
                node = self.tree.root
                continue

            self._display_board(options)
            self._display_options(options)

            choice: str = safe_input("\nYour choice: ")
            node = self._handle_choice(choice, node, options)

    # ---------------- Leaf handling ----------------
    def _handle_leaf(self) -> bool:
        """
        Handle completion of a move sequence (leaf node in move tree).
        Asks the player for confirmation.

        Returns:
            bool: True if the sequence is confirmed, False to restart.
        """
        print("\n✅ TurnMove complete:")
        print(" | ".join(str(m) for m in self.current_path))
        confirm: str = safe_input("Confirm this sequence? (y/n): ")
        if confirm.lower() == "y":
            return True
        self.current_path.clear()
        self.state_copy = self.state.copy()
        self.dice = self.dice_all.copy()
        return False

    # ---------------- Board display ----------------
    def _display_board(self, options: List[SingleMove]) -> None:
        """
        Display the board highlighting from-points for available moves.

        Args:
            options (List[SingleMove]): Available single moves at current node.
        """
        from_points = {m.from_point for m in options}
        self.board_display.state = self.state_copy
        self.board_display.draw_all(from_points=from_points)
        print()

    # ---------------- Show move options ----------------
    def _display_options(self, options: List[SingleMove]) -> None:
        """
        Display the available moves grouped by die value.

        Args:
            options (List[SingleMove]): List of single moves to display.
        """
        print("Dice " + "🎲" * len(self.dice) + f": {self.dice}\n")

        last_die = None
        for idx, move in enumerate(options, 1):
            die = move.die
            if last_die != die:
                last_die = die
                print(f"\nDie 🎲: {die}\n")
            print(f"{idx}: {move}")
        print("\nb: go back")

    # ---------------- Handle choice / backtracking ----------------
    def _handle_choice(self, choice: str, node: Dict[SingleMove, Any], options: List[SingleMove]) -> Dict[SingleMove, Any]:
        """
        Handle a player’s choice from the displayed options.
        Applies the chosen move or goes back if requested.

        Args:
            choice (str): Player input.
            node (dict): Current subtree in the move tree.
            options (List[SingleMove]): List of moves at current node.

        Returns:
            dict: The next subtree after applying the choice.
        """
        if choice.lower() == "b":
            self._go_back()
            # Reset tree node according to current path
            new_node: Dict[SingleMove, Any] = self.tree.root
            for m in self.current_path:
                new_node = new_node[m]
            return new_node

        if not choice.isdigit() or not (1 <= int(choice) <= len(options)):
            print("Invalid choice, please try again.")
            interruptible_sleep(0.5)
            return node

        # Apply move
        move: SingleMove = options[int(choice) - 1]
        self.state_copy.apply_move(move)
        self.current_path.append(move)
        self.dice.remove(move.die)
        return node[move]

    def _go_back(self) -> None:
        """
        Undo the last move in the current sequence and restore dice.
        """
        if not self.current_path:
            print("Already at the beginning, cannot go back.")
            interruptible_sleep(0.5)
            return
        last_move: SingleMove = self.current_path.pop()
        self.state_copy.undo_move(last_move)
        self.dice.append(last_move.die)
