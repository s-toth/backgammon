# =========================================================
# --- cli_cliHandlers.py ---
# =========================================================

from typing import Any, Dict, Callable

from .cliColors import PLAYER
from .cliUtils import interruptible_sleep, clear
from .boardDisplay import BoardDisplay

# =========================================================

class CLIHandlers:
    """
    Handles CLI events for Backgammon game visualization.

    Attributes:
        delay (float): Delay in seconds between event prints to allow user to follow the game.
    """

    def __init__(self, delay: float = 1.5):
        """
        Initialize the CLI handler with optional delay.

        Args:
            delay (float): Sleep duration between events (default 1.5 seconds).
        """
        self.delay: float = delay

    # ---------------- Event Handlers ----------------
    def handle_start_roll(self, event: Dict[str, Any]) -> None:
        """
        Handle the initial dice roll to determine starting player.

        Args:
            event (dict): Event data with 'dice' and 'turn' keys.
        """
        print(f"\nRolling start dice 🎲🎲 ...:\n")
        print(f"{PLAYER[0]} rolls 🎲: {event['dice'][0]}")
        print(f"{PLAYER[1]} rolls 🎲: {event['dice'][1]}")
        print(f"\n=> {PLAYER[event['turn']]} starts.")
        interruptible_sleep(self.delay)

    def handle_turn_start(self, event: Dict[str, Any]) -> None:
        """
        Handle start of a turn: display board and current player.

        Args:
            event (dict): Event data with 'state', 'turn', and 'bear_off_allowed'.
        """
        BoardDisplay(event["state"]).draw_all()
        print(f"\nTurn: {PLAYER[event['turn']]}")
        if event['bear_off_allowed']:
            print(f"\nBearing off allowed!\n")
        interruptible_sleep(self.delay)

    def handle_doubling_cube(self, event: Dict[str, Any]) -> None:
        """
        Handle doubling cube event: display offered and accepted status.

        Args:
            event (dict): Event data with 'turn', 'offered', 'accepted', and 'cube_value'.
        """
        if event['offered']:
            print(f"\nTurn: {PLAYER[event['turn']]}; Cube offered? {event['offered']}; "
                  f"Accepted? {event['accepted']}; Cube Value: {event['cube_value']}\n")
            interruptible_sleep(self.delay)

    def handle_roll_dice(self, event: Dict[str, Any]) -> None:
        """
        Handle dice roll event: display dice and player type.

        Args:
            event (dict): Event data with 'dice', 'turn', and optionally 'player_type'.
        """
        print(f"\n{PLAYER[event['turn']]} rolled " + "🎲" * len(event['dice']) + f": {event['dice']}\n")

        player_type = event.get("player_type")
        print(f"({player_type})")

        if player_type in ("ComputerPlayer(0)", "ComputerPlayer(1)"):
            print(f"\nComputer thinks 🤔 ... Please be patient 😄")
            interruptible_sleep(self.delay)

        interruptible_sleep(self.delay)

    def handle_no_moves(self, event: Dict[str, Any]) -> None:
        """
        Handle event when no legal moves are available for a player.

        Args:
            event (dict): Event data with 'turn'.
        """
        print(f"\nNo legal moves available!\n")
        interruptible_sleep(self.delay)

    def handle_chosen_move(self, event: Dict[str, Any]) -> None:
        """
        Handle event when a player has chosen a move.

        Args:
            event (dict): Event data with 'turn' and 'move'.
        """
        print(f"\n{PLAYER[event['turn']]} chose {event['move']}")
        interruptible_sleep(self.delay)

    def handle_apply_move(self, event: Dict[str, Any]) -> None:
        """
        Handle event when a move is applied to the board.

        Args:
            event (dict): Event data with 'state' and 'move'.
        """
        BoardDisplay(event["state"]).draw_all()
        print(f"\nApply move: {event['move']}")
        interruptible_sleep(self.delay)
        BoardDisplay(event["state"]).draw_all()
        interruptible_sleep(self.delay)

    def handle_turn_end(self, event: Dict[str, Any]) -> None:
        """
        Handle event when a turn ends.

        Args:
            event (dict): Event data with 'next_turn'.
        """
        print(f"\nTurn ended. Next player: {PLAYER[event['next_turn']]}")
        interruptible_sleep(self.delay)

    def handle_game_over(self, event: Dict[str, Any]) -> None:
        """
        Handle game over event: display winner and game result.

        Args:
            event (dict): Event data with 'state', 'winner', 'player_type', 'points', and 'result_type'.
        """
        BoardDisplay(event["state"]).draw_all()
        print(f"\nGame Over! Winner: {PLAYER[event['winner']]} ({event['player_type']}), "
              f"Points: {event['points']}, Type: {event['result_type']}\n")

    # ---------------- Handler Mapping ----------------
    @property
    def handlers(self) -> Dict[str, Callable[[Dict[str, Any]], None]]:
        """
        Returns a dictionary mapping event types to their handler functions.

        Returns:
            dict: Mapping of event type strings to handler methods.
        """
        return {
            "start_roll": self.handle_start_roll,
            "turn_start": self.handle_turn_start,
            "cube_action": self.handle_doubling_cube,
            "roll_dice": self.handle_roll_dice,
            "no_moves": self.handle_no_moves,
            "chosen_move": self.handle_chosen_move,
            "apply_move": self.handle_apply_move,
            "turn_end": self.handle_turn_end,
            "game_over": self.handle_game_over,
        }
