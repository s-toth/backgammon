# =========================================================
# --- bot.py ---
# =========================================================

import os
from datetime import datetime
from contextlib import redirect_stdout
from typing import Optional, List, Dict, Any

from core.moves import SingleMoveType, SingleMove, TurnMove
from core.state import BackgammonState
from core.rules import BackgammonRules
from core.engine import GameEngine

from players.computer import ComputerPlayer
from players.random import RandomPlayer

from cli.boardDisplay import BoardDisplay

from .parser import OutputParser
from .resolver import GnuBGMoveResolver

# =========================================================

class GnuBGBot:
    """
    Bot interface for GNUBG. Parses GNUBG output, keeps engine state, 
    and generates moves or responses automatically.
    """

    def __init__(self, bot_player_type: str = "ComputerPlayer", log_file: Optional[str] = None, debug: bool = True) -> None:
        """
        Initialize the bot.

        Args:
            bot_player_type: Type of bot player to use.
            log_file: Optional file path to log bot actions.
            debug: If True, logs are generated for each move.
        """
        self.parser: OutputParser = OutputParser()
        self._bot_player_type: str = bot_player_type              
        self._dice: Dict[str, Optional[List[int]]] = {"O": None, "X": None}
        self._engine: Optional[GameEngine] = None
        
        self.debug: bool = debug
        self.log_file: Optional[str] = log_file
        self.log_entry_counter: int = 1
        self._pending_commands: List[str] = []

        self.setup_engine()

    # --- Setup ---
    @property
    def bot_player_type(self) -> ComputerPlayer:
        """Return an instance of the bot player."""
        __bot_engine_id = 0
        if self._bot_player_type == "ComputerPlayer":
            return ComputerPlayer(id=__bot_engine_id)
        raise ValueError("No valid player type found!")

    @property   
    def player_prop(self) -> Dict[str, Dict[str, Any]]:
        """Return properties of bot and GNUBG players."""
        return {
            "bot": {"engine_id": 0, "token": "X", "player_type": self.bot_player_type},
            "gnubg": {"engine_id": 1, "token": "O", "player_type": None}
        }

    def setup_engine(self) -> GameEngine:
        """Initialize the game engine with players if not already initialized."""
        if self._engine is None:
            players: List[Optional[Any]] = [None, None]
            bot_id = self.player_prop["bot"]["engine_id"]
            gnubg_id = self.player_prop["gnubg"]["engine_id"]
            players[bot_id] = self.player_prop["bot"]["player_type"]
            players[gnubg_id] = self.player_prop["gnubg"]["player_type"]
            self._engine = GameEngine(*players, BackgammonState(), BackgammonRules())
        return self._engine

    # --- Dice & Engine Sync ---
    def sync_engine_turn_and_dice(self, player: str) -> None:
        """
        Sync engine turn and dice with the specified player.

        Args:
            player: Either "bot" or "gnubg".

        Raises:
            ValueError: If no dice are found for the player.
        """
        if self._engine.game_finished():
            self._engine.state.reset_board() 
        prop = self.player_prop[player]
        if self._engine.turn != prop["engine_id"]:
            self._engine.next_turn()
        dice = self._dice.get(prop["token"])
        if dice is None:
            raise ValueError(f"No dice found for {player}")
        self._engine.dice = self._engine.rules.process_dice(dice)

    def _handle_dice(self, board_out: Dict[str, Any]) -> None:
        """Update the bot's dice from the parsed board output."""
        if board_out.get("dice_O"):
            self._dice["O"] = board_out["dice_O"].copy()
        if board_out.get("dice_X"):
            self._dice["X"] = board_out["dice_X"].copy()

    # --- Bot Move ---
    def _turnmove_to_gnubg_move(self, turn: TurnMove) -> str:
        """
        Convert a TurnMove object into GNUBG move string.

        Args:
            turn: TurnMove object.

        Returns:
            GNUBG-style move string, e.g. "24/23 8/7".
        """
        return " ".join(f"{sm.from_point}/{sm.to_point}" for sm in turn.single_moves)

    def _handle_bot_move(self, board_out: Dict[str, Any]) -> None:
        """Generate bot moves if it's the bot's turn to move."""
        if board_out.get("X_has_to_move"):
            self.sync_engine_turn_and_dice("bot")
            legal_moves = self._engine.legal_moves
            move = self._engine.player.select_move(legal_moves, self._engine.state, self._engine.dice)
            if move:
                for sm in move:
                    self._engine.state.apply_move(sm)
                self._pending_commands.append(self._turnmove_to_gnubg_move(move))

    # --- Event Handlers ---
    def handle_board(self, result: Dict[str, Any]) -> None:
        """Process board output from GNUBG and prepare bot actions."""
        board_out = result.get("content_from_board", {})
        self._handle_dice(board_out)
        if board_out.get("has_to_roll_X"):
            self._pending_commands.append("roll")
        if board_out.get("dice_X"):
            self._handle_bot_move(board_out)

    def handle_double(self, gnubg_info: List[str]) -> None:
        """Process cube double offers from GNUBG."""
        if "double_offered" in gnubg_info:
            self.sync_engine_turn_and_dice("bot")
            self._engine.player.accept_double(self._engine.cube_value, self._engine.state)
            self._engine.cube_value *= 2
            self._engine.cube_owner = 1
            self._pending_commands.append("accept")

    def handle_gnubg_move(self, result: Dict[str, Any]) -> None:
        """Process GNUBG moves and apply them to the engine state."""
        moves = result.get("gnubg_move")
        if not moves:
            return
        self.sync_engine_turn_and_dice("gnubg")
        resolver = GnuBGMoveResolver(
            self._engine, self._dice, self.player_prop["gnubg"],
            log_file=self.log_file if self.debug else None
        )
        resolver.apply_moves(moves)

    def handle_prompt(self, result: Dict[str, Any]) -> bool:
        """
        Handle GNUBG prompts and generate bot commands.

        Returns:
            True if prompt was handled, False otherwise.
        """
        prompt = result.get("prompt")
        if prompt == "new_match":
            self._pending_commands.append("new match")
            return True
        if prompt == "exit_info":
            self._pending_commands.append('y')
            return True
        if prompt == "OK":
            return True
        return False
    
    # --- Logging ---
    def log_bot_action(self, cmd: Optional[str] = None, board_display: bool = False, gnubg_info: Any = False) -> None:
        """
        Log bot actions, commands, board state, and GNUBG info to the log file.

        Args:
            cmd: Command executed.
            board_display: Whether to print the board to the log.
            gnubg_info: GNUBG info list to log.
        """
        if not self.log_file:
            return
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"ENTRY {self.log_entry_counter} - {datetime.now()}\n\n")
            f.write("COMMAND:\n")
            f.write(str(cmd) if cmd else "<no command>\n")
            f.write("\nBOARD:\n")
            if board_display:
                bd = BoardDisplay(self._engine.state, clear_screen=False, use_color=False)
                with redirect_stdout(f):
                    bd.draw_all()
            else:
                f.write("<no board>\n")
            f.write("\nGNUBG INFO:\n")
            f.write(f"{gnubg_info}\n")
        self.log_entry_counter += 1

    # --- Main Command Selection ---
    def select_command(self, data: str) -> Optional[str]:
        """
        Parse GNUBG output and decide the next bot command.

        Args:
            data: GNUBG output text.

        Returns:
            Next command string for GNUBG, or None if no command.
        """
        result: Dict[str, Any] = self.parser.parse(data)
        gnubg_info: List[str] = result.get("gnubg_info", [])

        action_handler: Dict[str, Any] = {
            "unknown_keyword": lambda _: self._pending_commands.append("exit"),
            "illegal_move": lambda _: self._pending_commands.append("exit"),
            "waiting_double": lambda _: self._pending_commands.append("exit"),
            "game_over": lambda _: self._pending_commands.append("exit"),
            "give_up": lambda _: self._pending_commands.append("accept"),
            "game_start_info": lambda _: None,
            "cube_refused": lambda _: None,
            "double_offered": lambda _: self.handle_double(gnubg_info),
            "board_detected": lambda _: self.handle_board(result),
            "gnubg_move_detected": lambda _: self.handle_gnubg_move(result),
        }

        for info, handler in action_handler.items():
            if info in gnubg_info:
                handler(None)

        if "prompt_detected" in gnubg_info:
            self.handle_prompt(result)
            cmd = self._pending_commands.pop(0) if self._pending_commands else None
        else:
            cmd = None

        if self.debug:
            self.log_bot_action(cmd, "board_detected" in gnubg_info, gnubg_info)

        return cmd
