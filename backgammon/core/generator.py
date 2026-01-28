# =========================================================
# --- core_generator.py ---
# =========================================================

from typing import List, Optional, Iterator, Tuple, Dict

from .board import DIRECTION, BEAR_OFF_ANCHOR
from .moves import SingleMoveType, SingleMove, TurnMove
from .state import BackgammonState
from .rules import BackgammonRules

from utils.bitmask import indices_from_bits, is_bit_set

# =========================================================

class SingleMovesGenerator:
    """Generates legal single moves for a given die and state."""

    def generate_moves(self, die: int, rules: BackgammonRules, state: BackgammonState) -> List[SingleMove]:
        """
        Generate all legal single moves for the current player with a given die.

        Args:
            die: The die value to move.
            rules: Game rules engine.
            state: Current game state.

        Returns:
            List of legal SingleMove instances.
        """
        single_moves: List[SingleMove] = []
        
        for start in indices_from_bits(rules.allowed_start_points_mask(state)):
            smove = self._single_move(start, die, rules, state)
            if smove is not None:
                single_moves.append(smove)
      
        return single_moves

    def _single_move(self, start: int, die: int, rules: BackgammonRules, state: BackgammonState) -> Optional[SingleMove]:
        """
        Generate a single legal move from a given start point using a die.

        Args:
            start: Starting point of the move.
            die: Die value to use.
            rules: Game rules engine.
            state: Current game state.

        Returns:
            A SingleMove if legal, otherwise None.
        """
        target = start + die * DIRECTION[state.turn]
        
        if state.is_on_board(target):
            legal_mask = rules.generate_legal_mask(state, die)
            if is_bit_set(target, legal_mask):
                mtype = SingleMoveType.HIT if rules.hittable_target(state, target) else SingleMoveType.NORMAL
                return SingleMove(state.turn, start, target, mtype, die)
        
        # Check for bearing off
        if rules.bearing_off_allowed(state):
            if rules.bear_off_target(state, start, target, die):
                return SingleMove(state.turn, start, BEAR_OFF_ANCHOR[state.turn], SingleMoveType.BEAR_OFF, die)
        
        return None


class TurnMoveGenerator:
    """Generates legal sequences of moves (TurnMove) for a given dice roll."""

    def any_move_left(self, state: BackgammonState, rules: BackgammonRules, dice: List[int]) -> bool:
        """
        Check if any legal move is possible for the current player with remaining dice.

        Args:
            state: Current game state.
            rules: Game rules engine.
            dice: List of remaining dice.

        Returns:
            True if at least one move is possible, False otherwise.
        """
        if len(dice) == 0:
            return False
                     
        for die in set(dice):
            single_moves = SingleMovesGenerator().generate_moves(die, rules, state)
            if single_moves:
                return True
        
        return False

    def generate_all_turn_moves(self, state: BackgammonState, rules: BackgammonRules, dice: List[int]) -> List[TurnMove]:
        """
        Generate all legal sequences of moves for a given dice roll.

        Args:
            state: Current game state.
            rules: Game rules engine.
            dice: List of dice values.

        Returns:
            List of TurnMove sequences.
        """
        turn_moves: List[TurnMove] = []
        visited_states: set[Tuple[int, Tuple[int, ...]]] = set()

        def dfs(state: BackgammonState, dice_left: List[int], path: List[SingleMove]) -> None:
            if not self.any_move_left(state, rules, dice_left):
                if path:
                    turn_moves.append(TurnMove(single_moves=path))
                return

            state_hash = (hash(state), tuple(sorted(dice_left)))
            if state_hash in visited_states:
                return
            visited_states.add(state_hash)

            for idx, die in enumerate(dice_left):
                single_moves = SingleMovesGenerator().generate_moves(die, rules, state)
                if not single_moves:
                    continue

                remaining = dice_left[:idx] + dice_left[idx+1:]
                for smove in single_moves:
                    state.apply_move(smove)
                    dfs(state, remaining, path + [smove])
                    state.undo_move(smove)

        dfs(state, dice, [])
        return turn_moves

    def generate_legal_moves(self, state: BackgammonState, rules: BackgammonRules, dice: List[int]) -> List[TurnMove]:
        """
        Generate all legal turn moves after filtering according to rules.

        Args:
            state: Current game state.
            rules: Game rules engine.
            dice: List of dice values.

        Returns:
            Filtered list of legal TurnMove sequences.
        """
        all_moves = self.generate_all_turn_moves(state, rules, dice)
        legal_moves = rules.filter_turn_moves(all_moves, dice)
        return legal_moves 


class MoveTree:
    """Represents a tree of turn moves for easy iteration and analysis."""

    def __init__(self, turn_moves: List[TurnMove]) -> None:
        """
        Build a move tree from a list of TurnMove sequences.

        Args:
            turn_moves: List of TurnMove sequences to build the tree.
        """
        self.root: Dict[SingleMove, Dict] = self._build_tree([tmove.single_moves for tmove in turn_moves])
    
    def __repr__(self) -> str:
        return f"<MoveTree root_moves={len(self.root)}>"

    def _build_tree(self, sequences: List[List[SingleMove]]) -> Dict[SingleMove, Dict]:
        """
        Build a recursive dictionary tree from sequences of single moves.

        Args:
            sequences: List of sequences of SingleMove.

        Returns:
            Nested dictionary representing the move tree.
        """
        smove_tree: Dict[SingleMove, Dict] = {}
        if not sequences or len(sequences[0]) == 0:
            return smove_tree

        remaining: Dict[SingleMove, List[List[SingleMove]]] = {}
        seen: set[SingleMove] = set()

        for smove_seq in sequences:
            smove = smove_seq[0]
            if smove not in seen:
                smove_tree[smove] = {}
                remaining[smove] = []
                seen.add(smove)
            remaining[smove].append(smove_seq[1:])

        for smove, sub_seqs in remaining.items():
            smove_tree[smove] = self._build_tree(sub_seqs)

        return smove_tree

    def iter_paths(self) -> Iterator[List[SingleMove]]:
        """
        Iterate over all possible paths in the move tree.

        Yields:
            Lists of SingleMove representing each path from root to leaf.
        """
        def _iter(tree: Dict[SingleMove, Dict], path: List[SingleMove]) -> Iterator[List[SingleMove]]:
            if not tree:
                yield path
            for node, subtree in tree.items():
                yield from _iter(subtree, path + [node])

        return _iter(self.root, [])

    def iter_paths_stepwise(self) -> Iterator[Tuple[List[SingleMove], List[SingleMove]]]:
        """
        Stepwise iteration over the move tree.

        Yields:
            Tuple containing:
                - path: current path taken
                - options: next possible SingleMove options from the current node
        """
        def _gen(tree: Dict[SingleMove, Dict], path: List[SingleMove]) -> Iterator[Tuple[List[SingleMove], List[SingleMove]]]:
            if not tree:
                yield path, []
            else:
                options = list(tree.keys())
                yield path, options
                for node, subtree in tree.items():
                    yield from _gen(subtree, path + [node])

        return _gen(self.root, [])

    def __str__(self) -> str:
        """
        Return a readable string representation of the move tree.

        Returns:
            Multi-line string showing the tree hierarchy.
        """
        def _str(tree: Dict[SingleMove, Dict], prefix: str = "") -> List[str]:
            lines: List[str] = []
            for node, subtree in tree.items():
                lines.append(prefix + str(node))
                lines.extend(_str(subtree, prefix + " " * 8))
            return lines

        return "\n".join(_str(self.root))
