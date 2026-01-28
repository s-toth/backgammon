# =========================================================
# --- evaluation.py ---
# =========================================================

import math
from typing import Optional, Dict, Tuple

from core.board import BOARD_START, BOARD_END, HOME_MASK
from core.state import BackgammonState
from core.rules import BackgammonRules

from utils.bitmask import remove_from_mask, indices_from_bits, count_bits, mask_intersection_count

# =========================================================

class Valuation:
    """
    Player state evaluation with weighted heuristics.
    Supports heuristic evaluation for moves and cube decisions.
    
    Attributes:
        rules (BackgammonRules): Reference to the rules engine.
        eval_cache (Dict[Tuple[int,int], float]): Cache for heuristic evaluations keyed by (hash, player).
        w_bear_off (float): Weight for stones borne off.
        w_home (float): Weight for stones in home board.
        w_blots (float): Weight for unprotected stones (blots).
        w_blockades (float): Weight for blockades (points occupied by ≥2 stones).
        w_pip (float): Weight for pip penalty (distance to bear-off).
        norm_factor (float): Normalization factor for tanh scaling.
    """

    def __init__(self,
                 rules: BackgammonRules,
                 weight_bear_off: float = 15.0,
                 weight_home: float = 2.0,
                 weight_blots: float = 3.0,
                 weight_blockades: float = 1.0,
                 weight_pip: float = 0.1,
                 normalization_factor: float = 225.0):
        self.rules: BackgammonRules = rules
        self.eval_cache: Dict[Tuple[int, int], float] = {}

        self.w_bear_off: float = weight_bear_off
        self.w_home: float = weight_home
        self.w_blots: float = weight_blots
        self.w_blockades: float = weight_blockades
        self.w_pip: float = weight_pip
        self.norm_factor: float = normalization_factor

    # ---------------- Helper functions ----------------
    @staticmethod
    def count_blots(state: BackgammonState, player: int) -> int:
        """
        Count unprotected stones (blots) for the given player.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index (0 or 1).

        Returns:
            int: Number of blots for the player.
        """
        opp = 1 - player
        blots_mask = remove_from_mask(state._occ_mask[player], state._blocked_mask[opp])
        return int(bin(blots_mask).count("1"))

    @staticmethod
    def count_home_stones(state: BackgammonState, player: int) -> int:
        """
        Count stones in the player's home board.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index (0 or 1).

        Returns:
            int: Number of stones in home board.
        """
        home_indices = indices_from_bits(state._occ_mask[player] & HOME_MASK[player])
        return sum(state.num_of_stones(p, player) for p in home_indices)

    # ---------------- Sub-evaluations ----------------
    def evaluate_bear_off(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate the advantage from stones already borne off.

        Returns a positive score if player has more stones borne off than opponent.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Weighted score for bear-off.
        """
        opp = 1 - player
        return self.w_bear_off * (int(state.bear_off_stones[player]) - int(state.bear_off_stones[opp]))

    def evaluate_home(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate the advantage from stones in the home board.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Weighted score for home board presence.
        """
        opp = 1 - player
        return self.w_home * (self.count_home_stones(state, player) - self.count_home_stones(state, opp))

    def evaluate_blots(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate the penalty/advantage from blots (unprotected stones).

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Weighted score for blots (negative for own blots, positive for opponent's blots).
        """
        opp = 1 - player
        return -self.w_blots * self.count_blots(state, player) + self.w_blots * self.count_blots(state, opp)

    def evaluate_blockades(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate advantage from blockades (points occupied by 2+ stones).

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Weighted score for blockades.
        """
        opp = 1 - player
        return self.w_blockades * (count_bits(state._blocked_mask[player]) - count_bits(state._blocked_mask[opp]))

    def evaluate_pip_penalty(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate the pip penalty: weighted distance of stones to bear-off.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Weighted pip score (negative for player, positive for opponent).
        """
        opp = 1 - player
        return -self.w_pip * sum(int(state.num_of_stones(p, player)) * p for p in range(BOARD_START, BOARD_END + 1)) \
               + self.w_pip * sum(int(state.num_of_stones(p, opp)) * (BOARD_END + 1 - p) for p in range(BOARD_START, BOARD_END +1))

    # ---------------- Full evaluation ----------------
    def evaluate_state_heuristic(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate the full state for the given player using weighted heuristics.

        Includes bear-off, home, blots, blockades, pip penalty, and game-over bonus.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            float: Normalized evaluation score in [-0.4, 0.4].
        """
        h: Tuple[int,int] = (state.zobrist_hash, player)
        if h in self.eval_cache:
            return self.eval_cache[h]

        score: float = 0
        game_over = self.rules.game_over(state, 1)
        game_over_score = {"WIN": 0.6, "GAMMON": 0.8, "BACKGAMMON": 1.0}

        if game_over:
            if game_over.winner == player:
                score += game_over_score[game_over.type]
            else:
                score -= game_over_score[game_over.type]

        # weighted sub-evaluations
        score += self.evaluate_bear_off(state, player)
        score += self.evaluate_home(state, player)
        score += self.evaluate_blots(state, player)
        score += self.evaluate_blockades(state, player)
        score += self.evaluate_pip_penalty(state, player)

        # normalization
        score = 0.4 * math.tanh(score / self.norm_factor)
        self.eval_cache[h] = score
        return score

    # ---------------- Cube heuristics ----------------
    def offer_double_heuristic(self, state: BackgammonState, player: int) -> bool:
        """
        Heuristic: decide if doubling cube should be offered.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            bool: True if cube should be offered.
        """
        my_home = mask_intersection_count(HOME_MASK[player], state._occ_mask[player])
        my_bear_off = state.bear_off_stones[player]
        return my_home >= 10 or my_bear_off > 0

    def accept_double_heuristic(self, state: BackgammonState, player: int) -> bool:
        """
        Heuristic: decide if doubling cube should be accepted.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index.

        Returns:
            bool: True if cube should be accepted, False otherwise.
        """
        opp = 1 - player
        opp_home = mask_intersection_count(HOME_MASK[opp], state._occ_mask[opp])
        opp_bear_off = state.bear_off_stones[opp]
        if opp_bear_off >= 3 and opp_home >= 12:
            return False
        return True

