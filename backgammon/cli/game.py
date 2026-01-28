# =========================================================
# --- cli_game.py ---
# =========================================================

from core.moves import TurnMove
from core.state import BackgammonState
from core.rules import BackgammonRules
from core.engine import GameEngine

from players.player import Player
from players.human import HumanPlayer
from players.random import RandomPlayer
from players.computer import ComputerPlayer

from .cliColors import PLAYER
from .cliUtils import ExitGame, interruptible_sleep, safe_input, clear
from .cliHumanInterface import HumanMoveNavigator
from .cliHandlers import CLIHandlers

# =========================================================

class CLISetup:
    """
    Factory and setup utilities for configuring players
    and initializing the game engine for the CLI.
    """

    @staticmethod
    def human_cli_input(
        turn_moves: list[TurnMove],
        state: BackgammonState,
        dice: list[int],
    ) -> TurnMove:
        """
        Handle human move selection via interactive CLI navigation.

        Args:
            turn_moves (list[TurnMove]): All legal turn moves.
            state (BackgammonState): Current game state.
            dice (list[int]): Dice values for the current turn.

        Returns:
            TurnMove: The selected move sequence.
        """
        navigator = HumanMoveNavigator(
            state=state,
            turn_moves=turn_moves,
            dice=dice,
        )
        return navigator.navigate()

    @staticmethod
    def create_human_player(slot: int) -> HumanPlayer:
        """
        Create a human player for a given slot.

        Args:
            slot (int): Player index (0 or 1).

        Returns:
            HumanPlayer: Configured human player instance.
        """
        return HumanPlayer(id=slot, input_func=CLISetup.human_cli_input)

    @staticmethod
    def choose_player(slot: int, engine: GameEngine | None = None) -> Player:
        """
        Prompt the user to choose a player type for a given slot.

        Args:
            slot (int): Player index (0 or 1).
            engine (GameEngine | None): Optional engine reference.

        Returns:
            Player: Instantiated player object.
        """
        print(f"\nChoose player for {PLAYER[slot]}: 1-Human, 2-Random, 3-Computer")
        while True:
            choice: str = input("Choice (1/2/3): ").strip()
            if choice == "1":
                return CLISetup.create_human_player(slot)
            if choice == "2":
                return RandomPlayer(id=slot)
            if choice == "3":
                return ComputerPlayer(id=slot)
            print("Invalid input, enter 1,2,3")

    @staticmethod
    def enable_cube() -> bool:
        """
        Ask whether the doubling cube should be enabled.

        Returns:
            bool: True if cube play is enabled, False otherwise.
        """
        choice: str = input("\nEnable doubling cube? [y/N]: ").strip().lower()
        return choice == "y"

    def setup_engine(self) -> GameEngine:
        """
        Initialize the game engine with rules, state, players,
        and cube configuration.

        Returns:
            GameEngine: Fully configured game engine.
        """
        state = BackgammonState()
        rules = BackgammonRules()
        engine = GameEngine(
            None,
            None,
            state,
            rules,
            self.enable_cube(),
        )
        engine.players = [
            self.choose_player(0, engine),
            self.choose_player(1, engine),
        ]
        return engine


class BackgammonCLI:
    """
    Main command-line interface controller for running a Backgammon game.
    """

    def __init__(self, delay: float = 1.5, stepwise: bool = False):
        """
        Initialize the CLI.

        Args:
            delay (float): Delay in seconds between UI updates.
            stepwise (bool): Whether to run the engine in stepwise mode.
        """
        self.setup = CLISetup()
        self.handlers = CLIHandlers(delay).handlers
        self.stepwise = stepwise

    def play_game(self, engine: GameEngine) -> None:
        """
        Run the game loop and dispatch events to CLI handlers.

        Args:
            engine (GameEngine): The configured game engine.

        Raises:
            ExitGame: If the user exits the game intentionally.
        """
        for event in engine.play_game(stepwise=self.stepwise):
            handler = self.handlers.get(event["type"])
            if handler:
                try:
                    handler(event)
                except ExitGame:
                    raise

    def run(self) -> None:
        """
        Start the CLI application and run a complete game session.
        """
        clear()
        try:
            engine = self.setup.setup_engine()
            self.play_game(engine)
        except ExitGame:
            print("\nGame exited by player.")
        except KeyboardInterrupt:
            print("\nGame interrupted by user. Exiting…")


# ---------------- Main ----------------
if __name__ == "__main__":
    cli = BackgammonCLI()
    cli.run()
