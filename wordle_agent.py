# From repo that we are further extending. Credits/Reference listed in README 
# wordle_agent.py
"""
WordleAgent: wraps the existing Solver/Dictionary engine with a pluggable Strategy. 
Our own framewokr. 

This is the "automatic agent" used in simulation mode:
  - It knows the hidden target word.
  - It repeatedly chooses guesses via a Strategy.
  - It uses the original solver's feedback logic to update the belief state.
  - It stops when the target is found or a max number of guesses is reached.

Later, the same Strategy/Dictionary mechanics can be reused for "tutor mode"
(without a known target), where feedback comes from the human player.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Type, TypeVar

from wordle_solver import Solver, Dictionary, LetterFeedback
from strategies import Strategy, BaselineFrequencyStrategy

# Generic type variable for a Strategy class
S = TypeVar("S", bound=Strategy)


@dataclass
class SimulationResult:
    """
    Data returned by a single simulated game.

    Attributes:
        target:   the hidden answer word for this game
        guesses:  list of guesses made, in order
        solved:   True if the agent found the target within max_guesses
    """
    target: str
    guesses: List[str]
    solved: bool


class WordleAgent:
    """
    WordleAgent couples:
      - the existing Solver (engine: feedback, pruning)
      - a Strategy (decision policy: which guess to try next).

    In state-space terms:
      - The underlying Puzzle/Dictionary maintain the belief state:
          candidates = remaining answers
          feedback   = constraints derived from past guesses
      - The Strategy maps that belief state to an action (next guess).
    """

    def __init__(
        self,
        target_word: str,
        strategy_cls: Type[S] = BaselineFrequencyStrategy,
        starting_word: str | None = "SLATE",
        use_intersecting_guesses: bool = True,
    ) -> None:
        """
        :param target_word:           the answer we want to solve (simulation mode)
        :param strategy_cls:          which Strategy class to use
        :param starting_word:         initial guess to use (e.g., 'SLATE'), or None
        :param use_intersecting_guesses:
                                      whether to allow the original intersecting-guess
                                      behavior in the underlying Dictionary
        """
        self._target = target_word.upper()

        # Create the original Solver engine, which knows the target.
        self._solver = Solver(self._target, use_intersecting_guesses)

        # The Solver owns a Puzzle, which owns a Dictionary and LetterFeedback.
        self._dictionary: Dictionary = self._solver.puzzle.dictionary
        self._feedback: LetterFeedback = self._dictionary.feedback

        # Instantiate the chosen Strategy, giving it access to the Dictionary.
        self._strategy: Strategy = strategy_cls(self._dictionary)

        # Optional fixed starting word (useful for fair comparisons)
        self._starting_word = starting_word.upper() if starting_word else None

    @property
    def target(self) -> str:
        return self._target

    def run_simulation(self, max_guesses: int = 6) -> SimulationResult:
        """
        Run a single simulated game until the agent solves the puzzle
        or exhausts 'max_guesses'.

        Uses the chosen Strategy to pick each guess, while the Solver:
          - Computes feedback (green/yellow/gray) given the true target
          - Updates the internal LetterFeedback and Dictionary

        Returns:
            SimulationResult with the target, guesses, and solved flag.
        """
        guesses: List[str] = []

        # --- First guess -----------------------------------------------------
        if self._starting_word:
            guess = self._starting_word
        else:
            # If no fixed starting word, let the strategy choose.
            self._dictionary._update()  # ensure candidates are pruned before selection
            candidates = list(self._dictionary.answers)
            guess = self._strategy.select_guess(candidates, self._feedback, guesses)

        # --- Main game loop --------------------------------------------------
        while len(guesses) < max_guesses:
            guess = guess.upper()
            guesses.append(guess)

            # Register the guess with the Puzzle/Dictionary (removes it from pools).
            self._solver.puzzle.add_guess(guess)

            # Check for success
            if guess == self._target:
                return SimulationResult(target=self._target, guesses=guesses, solved=True)

            # Use the original solver's feedback logic to update LetterFeedback.
            # This applies green/yellow/gray based on the true target.
            self._solver._process_guess(guess)  # type: ignore[attr-defined]

            # Before the next decision, make sure the Dictionary prunes candidates
            # using the newly updated feedback.
            #
            # NOTE: _update() is a "private" helper in the original repo; we call
            # it here intentionally to keep the candidate set in sync for custom
            # strategies that look at 'candidates'.
            self._dictionary._update()  # type: ignore[attr-defined]
            candidates = list(self._dictionary.answers)

            # Ask the Strategy to pick the next guess based on the current
            # belief state (candidates + feedback + guesses_so_far).
            guess = self._strategy.select_guess(candidates, self._feedback, guesses)

        # If we exit the loop, we did not find the target within max_guesses.
        return SimulationResult(target=self._target, guesses=guesses, solved=False)
