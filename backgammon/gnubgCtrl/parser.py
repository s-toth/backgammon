# =========================================================
# --- parser.py ---
# =========================================================

import re
import json
from typing import Optional, List, Dict, Any, Union

# =========================================================

class OutputParser:
    """
    Parser for GNU Backgammon (gnubg) textual output.
    
    Provides detection of game state, player info, dice rolls, moves,
    and special events like cube offers or illegal moves.
    """

    def __init__(self) -> None:
        """
        Initialize the OutputParser with regex patterns for board, dice,
        moves, and other game-related events.
        """
        self.regex: Dict[str, Any] = {
            "board": {
                "normal": r"\+13-14-15-16-17-18-{0,6}19-20-21-22-23-24-\+.*\+12-11-10--9--8--7-{0,7}6--5--4--3--2--1-\+",
                "reversed": r"\+12-11-10--9--8--7-{0,7}6--5--4--3--2--1-\+.*\+13-14-15-16-17-18-{0,6}19-20-21-22-23-24-\+"
            },

            "gnubg_is": {
                "O": r"O:\sgnubg",
                "X": r"X:\sgnubg"
            },

            "dice": {
                "O": r"O:[^B]*?(\d)(\d)",
                "X": r"\d\d[^\+B]*\+[^\+]*\+[^\+]*X:"
            },

            "has_to_roll": {
                "O": r"O:[^BAR]*Am Wurf",
                "X": r"Am Wurf[^BAR]*X:"
            },

            "move_str_1": r"gnubg.{1,50}/\d{1,2}\*?", 
            "move_str_2": r"gnubg.{1,50}/\d{1,2}\*?\(\d\)",

            "move_str": [
                r"gnubg.{1,50}/\d{1,2}\*?",
                r"gnubg.{1,50}/\d{1,2}\*?\(\d\)",
                r"gnubg.{1,50}/off",
                r"gnubg.{1,50}/off\(\d\)"
            ],
           
            "double_offered": r"gnubg do",
            "cube_refused": r"\.\.\. refuses the cube and gives up \.\.\.",
            "illegal_move": r"Illegal or unparsable move\.",
            "unknown_keyword": r"Unknown keyword",
            "give_up": r"gnubg.*aufzugeben",
            "waiting_double": r"Bitte warte.*Doppler-Entscheidung",
            "start_info": r"Copyright",            
            "exit_info": r"Are you sure you want to discard the current match\?",
            "game_over": r"Spielstand",
            "prompt": r"\((sebastian|Keine Partie)\)",
        }

    # --- Board Info ---
    def board_detected(self, data: str) -> bool:
        """Check if a board layout is present in the data."""
        patterns = [self.regex["board"]["normal"], self.regex["board"]["reversed"]]
        return any(re.search(p, data, re.DOTALL) for p in patterns)

    def find_gnubg_player(self, data: str) -> Optional[str]:
        """Return 'O' or 'X' if a player is controlled by gnubg, else None."""
        for p in ["O", "X"]:
            if re.search(self.regex["gnubg_is"][p], data, re.DOTALL):
                return p
        return None

    def has_to_roll(self, data: str, player: str) -> bool:
        """Return True if the specified player must roll."""
        return bool(re.search(self.regex["has_to_roll"][player], data, re.DOTALL))
    
    def parse_dice(self, data: str, player: str) -> Optional[List[int]]:
        """
        Extract dice rolls for a player.
        
        Returns a list of two integers if found, else None.
        """
        pattern = self.regex["dice"][player]
        matches = re.findall(pattern, data, re.DOTALL)
        if not matches:
            return None
        if player == "X":
            digits = [int(matches[-1][0]), int(matches[-1][1])]
        elif player == "O":
            digits = [int(matches[-1][-2]), int(matches[-1][-1])]
        return digits

    # --- Turn Move Parsing ---
    def parse_turn_move_gnubg(self, data: str) -> Optional[List[List[str]]]:
        """
        Parse a gnubg turn output into a flat list of move pairs.

        Handles *-hits and (n)-repeats.
        
        Example:
        "24/23 8/7* 6/5(2)" 
        -> [["24","23"], ["8","7*"], ["6","5"], ["6","5"]]
        """
        move_pattern = self.regex["move_str"]
        possible_gnubg_moves = [re.findall(p, data)[-1] for p in move_pattern if re.findall(p, data)] 
        if not possible_gnubg_moves: 
            return None 
        
        gnubg_move = max(possible_gnubg_moves, key=len)
        token_str_split = gnubg_move.split()
        raw_tokens = [token for token in token_str_split if "/" in token]

        def translate_into_moves(token: str) -> List[List[str]]:
            num_of_move = 1
            if "(" in token and ")" in token:
                token, num = token.split("(")
                num_of_move = int(num.strip(")"))
            points = token.split("/")
            moves = [[points[i], points[i+1]] for i in range(len(points)-1)]
            if num_of_move > 1:
                clean_moves = [[m[0].strip("*"), m[1].strip("*")] for m in moves]*(num_of_move-1)
                return moves + clean_moves 
            return moves

        all_moves: List[List[str]] = []
        for token in raw_tokens:
            all_moves.extend(translate_into_moves(token))

        return all_moves

    # --- Info Detection ---
    def double_offered(self, data: str) -> bool:
        """Check if a double was offered."""
        return bool(re.search(self.regex["double_offered"], data, re.DOTALL))

    def cube_refused_detected(self, data: str) -> bool:
        """Check if the cube was refused."""
        return bool(re.search(self.regex["cube_refused"], data, re.DOTALL))

    def illegal_move_detected(self, data: str) -> bool:
        """Check if an illegal move occurred."""
        return bool(re.search(self.regex["illegal_move"], data, re.DOTALL))

    def unknown_keyword_detected(self, data: str) -> bool:
        """Check if an unknown keyword occurred."""
        return bool(re.search(self.regex["unknown_keyword"], data, re.DOTALL))

    def waiting_double_detected(self, data: str) -> bool:
        """Check if waiting for double decision."""
        return bool(re.search(self.regex["waiting_double"], data, re.DOTALL))

    def game_start_info_detected(self, data: str) -> bool:
        """Check if game start info is present."""
        return bool(re.search(self.regex["start_info"], data, re.DOTALL))

    def exit_info_detected(self, data: str) -> bool:
        """Check if exit info is present."""
        return bool(re.search(self.regex["exit_info"], data, re.DOTALL))
    
    def game_over_detected(self, data: str) -> bool:
        """Check if the game is over."""
        return bool(re.search(self.regex["game_over"], data, re.DOTALL))
    
    def give_up_detected(self, data: str) -> bool:
        """Check if a player gave up."""
        return bool(re.search(self.regex["give_up"], data, re.DOTALL))
    
    def gnubg_move_detected(self, data: str) -> bool:
        """Check if a gnubg move is present."""
        return any(re.search(p, data, re.DOTALL) for p in self.regex["move_str"])

    # --- Prompt ---
    def prompt_detected(self, data: str) -> Optional[str]:
        """
        Detect prompt in gnubg output.
        
        Returns:
            "new_match" if no match,
            "OK" if gnubg is ready,
            "exit_info" if exit prompt is detected,
            None otherwise.
        """
        match = re.search(self.regex["prompt"], data)
        if match:
            text = match.group(1)
            if text == "Keine Partie":
                return "new_match"
            elif text == "sebastian":
                return "OK"
        if self.exit_info_detected(data):
            return "exit_info"
        return None

    # --- Helper: Gnubg Info Parsing ---
    def parse_gnubg_info(self, data: str) -> List[str]:
        """
        Return a list of detected gnubg info flags.
        
        If no recognizable info is found, returns ["not_readable"].
        """
        info_list: List[str] = []
        for checker, label in [
            (self.cube_refused_detected, "cube_refused"),
            (self.unknown_keyword_detected, "unknown_keyword"),
            (self.illegal_move_detected, "illegal_move"),
            (self.waiting_double_detected, "waiting_double"),
            (self.game_start_info_detected, "game_start_info"),
            (self.exit_info_detected, "exit_info"),
            (self.double_offered, "double_offered"),
            (self.board_detected, "board_detected"),
            (self.gnubg_move_detected, "gnubg_move_detected"),
            (self.give_up_detected, "give_up"),
            (self.game_over_detected, "game_over"),
            (self.prompt_detected, "prompt_detected")
        ]:
            if checker(data):
                info_list.append(label)

        return info_list if info_list else ["not_readable"]

    # --- Main Parse ---
    def parse(self, data: str) -> Dict[str, Any]:
        """
        Parse gnubg output data and return structured information.

        Returns:
            dict with keys:
            - gnubg_info: list of detected flags
            - content_from_board: optional dict of board state and dice
            - gnubg_move: optional list of moves
            - prompt: optional prompt status
        """
        result: Dict[str, Any] = {}
        gnubg_info = self.parse_gnubg_info(data)
        result["gnubg_info"] = gnubg_info

        if "board_detected" in gnubg_info:
            result["content_from_board"] = {
                "gnubg_is": self.find_gnubg_player(data),
                "has_to_roll_O": self.has_to_roll(data,"O"),
                "has_to_roll_X": self.has_to_roll(data,"X"),
                "dice_O": self.parse_dice(data, "O"),
                "dice_X": self.parse_dice(data, "X"),
                "X_has_to_move": bool(self.parse_dice(data, "X"))
            }

        if "gnubg_move_detected" in gnubg_info:
            result["gnubg_move"] = self.parse_turn_move_gnubg(data)

        if "prompt_detected" in gnubg_info:
            result["prompt"] = self.prompt_detected(data)

        return result
