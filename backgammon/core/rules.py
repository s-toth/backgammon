# =========================================================
# --- core_rules.py ---
# =========================================================

from typing import List, Optional, Union
from dataclasses import dataclass

from .board import BOARD_START, BOARD_END, BAR_FIELD, HOME_START, HOME_END, HOME_MASK, OUTSIDE_HOME_MASK, FULL_BOARD_MASK, BEAR_OFF_ANCHOR, DIRECTION, NUM_OF_ALL_STONES
from .moves import SingleMoveType, SingleMove, TurnMove
from .state import BackgammonState

from utils.bitmask import set_bit, remove_from_mask, set_all_bits, shift_mask

# =========================================================

class Rule:
    """Base class for Backgammon rules."""

    def __init__(self, rule_id: str, description: str) -> None:
        """
        Initialize a rule.

        Args:
            rule_id: Unique identifier for the rule.
            description: Human-readable description.
        """
        self.id: str = rule_id
        self.description: str = description

    def check(self, state: BackgammonState, **kwargs) -> Union[bool, int, List[int]]:
        """
        Evaluate the rule on the given state.

        Args:
            state: Current game state.
            kwargs: Additional parameters required by the rule.

        Returns:
            The result of the rule (mask, boolean, or other value).

        Raises:
            NotImplementedError: Must be implemented in subclasses.
        """
        raise NotImplementedError


# --- Specific Rules ---

class BarPriorityRule(Rule):
    """R1: Player must re-enter stones from the bar first."""

    def __init__(self) -> None:
        super().__init__("R1", "Player must re-enter stones from the bar before moving any other stones.")

    def check(self, state: BackgammonState, **kwargs) -> int:
        """
        Return occupied mask if player has stones on the bar; otherwise all occupied positions.

        Args:
            state: Current game state.

        Returns:
            Bitmask representing positions that must be entered or occupied.
        """
        bar_index = BAR_FIELD[state.turn]
        if state.num_of_stones(bar_index, state.turn) > 0:
            return set_bit(bar_index)
        return state.masks['occupied']


class BearingOffEligibilityRule(Rule):
    """R2: Player may bear off only if all stones are in their home board."""

    def __init__(self) -> None:
        super().__init__("R2", "Player may bear off only if all stones are in their home board.")

    def check(self, state: BackgammonState, **kwargs) -> bool:
        """
        Check if all stones are inside home board.

        Args:
            state: Current game state.

        Returns:
            True if bearing off is allowed, False otherwise.
        """
        outside_home = OUTSIDE_HOME_MASK[state.turn]
        return (outside_home & state.masks['occupied']) == 0


class BearOffTargetRule(Rule):
    """R3: Checks if a move can bear off, including 'overshoot' logic."""

    def __init__(self) -> None:
        super().__init__("R3", "Checks if a move can bear off including overshoot logic.")

    def _no_stone_behind(self, start: int, state: BackgammonState) -> bool:
        """Check if there are no stones behind the start position."""
        player = state.turn
        home_mask = HOME_MASK[player]
        home_start, home_end = HOME_START[player], HOME_END[player]

        if player == 0:
            mask_behind = remove_from_mask(home_mask, set_all_bits(home_start, start))
        else:
            mask_behind = remove_from_mask(home_mask, set_all_bits(start, home_end))

        return (state.masks['occupied'] & mask_behind) == 0

    def check(self, state: BackgammonState, start: int, target: int, die: int, **kwargs) -> bool:
        """
        Determine if a stone can legally bear off.

        Args:
            state: Current game state.
            start: Starting point of the move.
            target: Target point of the move.
            die: Die used for the move.

        Returns:
            True if the move can bear off, False otherwise.
        """
        player = state.turn

        if target == BEAR_OFF_ANCHOR[player]:
            return True

        overshoot = (
            (player == 0 and target < BEAR_OFF_ANCHOR[player]) or
            (player == 1 and target > BEAR_OFF_ANCHOR[player])
        )

        if overshoot:
            if self._no_stone_behind(start, state):
                for p in range(HOME_START[player], HOME_END[player] + 1):
                    if state.num_of_stones(p, player) > 0:
                        exact = p + die * DIRECTION[player]
                        if exact == BEAR_OFF_ANCHOR[player]:
                            return False
                return True

        return False


class SingleHitRule(Rule):
    """R4: Target with exactly one opponent stone may be hit."""

    def __init__(self) -> None:
        super().__init__("R4", "Target point with exactly one opponent stone may be hit.")

    def check(self, state: BackgammonState, point: int, **kwargs) -> bool:
        """
        Check if the target point can be hit.

        Args:
            state: Current game state.
            point: Target point index.

        Returns:
            True if the point can be hit, False otherwise.
        """
        return state.num_of_stones(point, state.opp) == 1


class LegalMaskRule(Rule):
    """R5: Generate legal move mask given a die."""

    def __init__(self) -> None:
        super().__init__("R5", "Generate legal mask given a die.")

    def check(self, state: BackgammonState, die: int, **kwargs) -> int:
        """
        Generate the mask of legal moves for a given die.

        Args:
            state: Current game state.
            die: Die value.

        Returns:
            Bitmask of legal target points.
        """
        sm = BarPriorityRule().check(state)
        shifted = shift_mask(sm, die * DIRECTION[state.turn])
        shifted &= FULL_BOARD_MASK
        legal_mask = remove_from_mask(shifted, state.masks['blocked'])
        return legal_mask


class DiceHelperRule(Rule):
    """R6: Process dice (expand doubles)."""

    def __init__(self) -> None:
        super().__init__("R6", "Process dice, expand doubles to four moves.")

    def check(self, state: Optional[BackgammonState], dice: List[int], **kwargs) -> List[int]:
        """
        Expand doubles to four dice values.

        Args:
            state: Not used here, included for interface consistency.
            dice: Current dice rolled.

        Returns:
            List of dice values (expanded if double).
        """
        if len(dice) == 2 and dice[0] == dice[1]:
            return [dice[0]] * 4
        return dice


class FilterTurnMovesRule(Rule):
    """R7: Filter turn moves to enforce maximum moves and highest die usage."""

    def __init__(self) -> None:
        super().__init__("R7", "Filter turn moves to enforce maximum moves and highest die usage.")

    def check(self, turn_moves: List[TurnMove], dice: List[int], **kwargs) -> List[TurnMove]:
        """
        Filter turn moves according to game rules.

        Args:
            turn_moves: List of possible TurnMove sequences.
            dice: Current dice values.

        Returns:
            Filtered list of TurnMoves.
        """
        if not turn_moves:
            return []

        max_len = max(len(tmove) for tmove in turn_moves)
        turn_moves = [tmove for tmove in turn_moves if len(tmove) == max_len]

        if max_len == 1:
            dice_set = set(smove.die for tmove in turn_moves for smove in tmove)
            big = max(dice_set)
            turn_moves = [tmove for tmove in turn_moves
                          if tmove.single_moves and tmove.single_moves[0].die == big]

        return turn_moves


@dataclass(frozen=True)
class GameResult:
    """Encapsulates the outcome of a completed game."""

    winner: int
    points: int
    cube_value: int
    type: str  # WIN / GAMMON / BACKGAMMON


class GameOverRule(Rule):
    """R8: Check if game is over, including Gammon/Backgammon logic."""

    def __init__(self) -> None:
        super().__init__("R8", "Check if game is over and return GameResult if so.")

    def check(self, state: BackgammonState, cube_value: int) -> Optional[GameResult]:
        """
        Determine if the game is over.

        Args:
            state: Current game state.
            cube_value: Current doubling cube value.

        Returns:
            GameResult if the game is over, None otherwise.
        """
        for player in (0, 1):
            if state.bear_off_stones[player] == NUM_OF_ALL_STONES[player]:
                opponent = 1 - player

                gammon = (state.bear_off_stones[opponent] == 0)
                occ = state._occ_mask[opponent]
                additional = (state.num_of_stones(BAR_FIELD[opponent], opponent) > 0 or (occ & HOME_MASK[player] != 0))
                backgammon = gammon & additional

                if backgammon:
                    mult = 3
                    kind = "BACKGAMMON"
                elif gammon:
                    mult = 2
                    kind = "GAMMON"
                else:
                    mult = 1
                    kind = "WIN"

                points = mult * cube_value
                return GameResult(player, points, cube_value, kind)

        return None


class BackgammonRules:
    """Aggregates all rules and provides a convenient interface for game logic."""

    def __init__(self) -> None:
        """Initialize all rule instances."""
        self.R1 = BarPriorityRule()
        self.R2 = BearingOffEligibilityRule()
        self.R3 = BearOffTargetRule()
        self.R4 = SingleHitRule()
        self.R5 = LegalMaskRule()
        self.R6 = DiceHelperRule()
        self.R7 = FilterTurnMovesRule()
        self.R8 = GameOverRule()

        self.rules = [self.R1, self.R2, self.R3, self.R4, self.R5, self.R6, self.R7, self.R8]

    def allowed_start_points_mask(self, state: BackgammonState) -> int:
        """Return mask of allowed start points (Bar priority)."""
        return self.R1.check(state)

    def bearing_off_allowed(self, state: BackgammonState) -> bool:
        """Return True if player may bear off."""
        return self.R2.check(state)

    def bear_off_target(self, state: BackgammonState, start: int, target: int, die: int) -> bool:
        """Return True if a move can bear off."""
        return self.R3.check(state, start=start, target=target, die=die)

    def hittable_target(self, state: BackgammonState, point: int) -> bool:
        """Return True if the target point may be hit."""
        return self.R4.check(state, point=point)

    def generate_legal_mask(self, state: BackgammonState, die: int) -> int:
        """Return bitmask of legal targets for the die."""
        return self.R5.check(state, die=die)

    def process_dice(self, dice: List[int]) -> List[int]:
        """Process dice roll and expand doubles."""
        return self.R6.check(None, dice=dice)

    def filter_turn_moves(self, turn_moves: List[TurnMove], dice: List[int]) -> List[TurnMove]:
        """Filter generated turn moves according to rules."""
        return self.R7.check(turn_moves, dice)

    def game_over(self, state: BackgammonState, cube_value: int) -> Optional[GameResult]:
        """Check if the game is over and return GameResult."""
        return self.R8.check(state, cube_value)

    # Debug / Logging
    def debug_rule(self, rule: Rule, **kwargs):
        """Evaluate a rule and print debug output."""
        result = rule.check(**kwargs)
        print(f"[DEBUG] Rule {rule.id}: {rule.description} -> {result}")
        return result
