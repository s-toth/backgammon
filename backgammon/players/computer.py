# =========================================================
# --- players_computer.py ---
# =========================================================

import random
import math
from copy import deepcopy
from typing import List, Optional

from core.state import BackgammonState
from core.rules import BackgammonRules
from core.generator import TurnMoveGenerator
from core.moves import SingleMove

from .player import Player
from .valuation import Valuation

# =========================================================

class GammonBot:
    """
    AI bot for Backgammon using weighted heuristics, rollouts, and UCB1 for move selection.

    Attributes:
        rules (BackgammonRules): Rules engine instance.
        tmgen (TurnMoveGenerator): Turn move generator.
        eval (Valuation): Heuristic evaluation object.
        eval_cache (dict): Optional cache for evaluation results.
    """

    def __init__(self, valuation: Optional[Valuation] = None):
        """
        Initialize the GammonBot.

        Args:
            valuation (Optional[Valuation]): Custom evaluation object. Defaults to None.
        """
        self.rules: BackgammonRules = BackgammonRules()
        self.tmgen: TurnMoveGenerator = TurnMoveGenerator()
        self.eval: Valuation = valuation or Valuation(self.rules)
        self.eval_cache: dict = {}

    # ---------------- Evaluation ----------------
    def evaluate(self, state: BackgammonState, player: int) -> float:
        """
        Evaluate a game state for a given player.

        Args:
            state (BackgammonState): Current game state.
            player (int): Player index (0 or 1).

        Returns:
            float: Heuristic score of the state for the player.
        """
        return self.eval.evaluate_state_heuristic(state, player)

    # ---------------- Rollout ----------------
    def rollout(self, state: BackgammonState, depth: int) -> float:
        """
        Perform a random rollout up to a certain depth and evaluate the resulting state.

        Args:
            state (BackgammonState): Current game state.
            depth (int): Number of turns to simulate.

        Returns:
            float: Heuristic evaluation of the resulting state.
        """
        count = 0
        turn = state.turn
        applied_moves: List[SingleMove] = []

        if self.rules.game_over(state, 1):
            return self.evaluate(state, turn)

        while count < depth:
            dice = [random.randint(1, 6), random.randint(1, 6)]
            dice = self.rules.process_dice(dice)

            moves = self.tmgen.generate_legal_moves(state, self.rules, dice)
            if not moves:
                state.switch_turn()
                count += 1
                continue

            move = random.choice(moves)
            for sm in move:
                state.apply_move(sm)
                applied_moves.append(sm)

            state.switch_turn()
            count += 1

        reward = self.evaluate(state, turn)

        # undo moves
        while applied_moves:
            sm = applied_moves.pop()
            state.undo_move(sm)
        state.turn = turn

        return reward

    # ---------------- UCB1 ----------------
    @staticmethod
    def ucb1(value: float, visits: int, total_visits: int, c: float = 1.0) -> float:
        """
        Upper Confidence Bound (UCB1) calculation for exploration-exploitation balance.

        Args:
            value (float): Total value of the node.
            visits (int): Number of times node was visited.
            total_visits (int): Total visits of all sibling nodes.
            c (float, optional): Exploration parameter. Defaults to 1.0.

        Returns:
            float: UCB1 score.
        """
        return (value / visits) + c * math.sqrt(math.log(total_visits + 1) / visits)
    
    # ---------------- Move selection ----------------
    
    def select_move(
        self,
        state: BackgammonState,
        legal_moves: list[list[SingleMove]],
        min_depth: int = 2,
        max_depth: int = 7,
        iterations: int = 120,
    ) -> list[SingleMove]:
        """
        Select the best move using UCB1 and rollout simulations.

        Ensures that the root state is unchanged after each iteration.

        Args:
            state (BackgammonState): Current game state.
            legal_moves (List[List[SingleMove]]): List of legal turn moves.
            min_depth (int, optional): Minimum rollout depth. Defaults to 2.
            max_depth (int, optional): Maximum rollout depth. Defaults to 7.
            iterations (int, optional): Number of rollout iterations per move. Defaults to 120.

        Returns:
            List[SingleMove]: Selected best move.
        """
        player = state.turn
        moves_eval: dict = {}
        applied_moves: list[SingleMove] = []

        # store hash of the root state
        root_hash = state.zobrist_hash

        # initialize move evaluations
        for id, move in enumerate(legal_moves):
            for sm in move:
                state.apply_move(sm)
                applied_moves.append(sm)

            moves_eval[id] = {
                'value': self.evaluate(state, player),
                'visits': 1
            }

            while applied_moves:
                sm = applied_moves.pop()
                state.undo_move(sm)

        # UCB1-based simulations
        for _ in range(iterations):
            total_visits = sum(m['visits'] for m in moves_eval.values())
            id = max(
                moves_eval,
                key=lambda i: self.ucb1(
                    moves_eval[i]['value'],
                    moves_eval[i]['visits'],
                    total_visits,
                    c=1.0
                )
            )

            move = legal_moves[id]

            # determine rollout depth
            depth = min_depth + int((moves_eval[id]['visits'] / 10) * (max_depth - min_depth))
            depth = min(depth, max_depth)

            for sm in move:
                state.apply_move(sm)
                applied_moves.append(sm)

            reward = self.rollout(state, depth)

            while applied_moves:
                sm = applied_moves.pop()
                state.undo_move(sm)

            moves_eval[id]['value'] += reward
            moves_eval[id]['visits'] += 1

            # check that root state is unchanged
            assert state.zobrist_hash == root_hash, "Root state was modified during move selection!"

        # return best move
        id_best = max(moves_eval, key=lambda i: moves_eval[i]['value'] / moves_eval[i]['visits'])
        return legal_moves[id_best]



# =========================================================
# # --- ComputerPlayer wrapper ---
# =========================================================

class ComputerPlayer(Player):
    """
    Wrapper for GammonBot with cube decision heuristics.

    Attributes:
        id (int): Player index (0 or 1).
        comp (GammonBot): The underlying AI bot instance.
    """

    def __init__(self, id: int):
        """
        Initialize a computer player.

        Args:
            id (int): Player index (0 or 1).
        """
        self.id: int = id
        self.comp: GammonBot = GammonBot()

    def __str__(self) -> str:
        """
        Return string representation.

        Returns:
            str: "ComputerPlayer(<id>)"
        """
        return f"ComputerPlayer({self.id})"

    def select_move(
        self,
        moves: List[List[SingleMove]],
        state: BackgammonState,
        dice: List[int]
    ) -> Optional[List[SingleMove]]:
        """
        Select a move using the underlying GammonBot.

        Args:
            moves (List[List[SingleMove]]): List of legal moves.
            state (BackgammonState): Current game state.
            dice (List[int]): Current dice roll.

        Returns:
            Optional[List[SingleMove]]: Selected move or None if no moves available.
        """
        if not moves:
            return None
        return self.comp.select_move(state, moves)

    # ---------------- Cube heuristics ----------------
    def offer_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Decide whether to offer the doubling cube.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if offering, False otherwise.
        """
        return self.comp.eval.offer_double_heuristic(state, self.id)

    def accept_double(self, cube_value: int, state: BackgammonState) -> bool:
        """
        Decide whether to accept the doubling cube.

        Args:
            cube_value (int): Current cube value.
            state (BackgammonState): Current game state.

        Returns:
            bool: True if accepting, False otherwise.
        """
        return self.comp.eval.accept_double_heuristic(state, self.id)




