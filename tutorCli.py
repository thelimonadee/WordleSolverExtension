#Original file of our own - CLI runner of our implementation and solver. Tutorer in this case
"""
tutor_cli.py

Interactive "tutor mode" for Wordle, built on top of:
  - wordle_solver.py (original engine)
  - strategies.py (Baseline / Entropy / Bayesian / A*-ish strategies)
Inspired by the given repos interactive CLI tutorer + additional feedback listed below

Lets user play real Wordle in the browser or phone on todays puzzle while the AI:
  - Tracks the evolving belief state (remaining candidates)
  - Recommends the next guess using a chosen strategy noted by the user using the command for ex:
        tutorCli.py --strategy entropy --starting-word SLATE --prefix session_entropy
        -entropy strategy in this case
  - Shows remaining candidate counts
  - Saves a session summary (TXT + CSV) as well
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from typing import Dict, Type, List

from wordle_solver import Solver, Dictionary, LetterFeedback
from strategies import (
    Strategy,
    BaselineFrequencyStrategy,
    EntropyHeuristicStrategy,
    BayesianBeliefStrategy,
    AStarEvaluationStrategy,
)


STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    "baseline": BaselineFrequencyStrategy,
    "entropy": EntropyHeuristicStrategy,
    "bayes": BayesianBeliefStrategy,
    "astar": AStarEvaluationStrategy,
}


class TutorSession:
    """
    Wraps a Solver + Strategy for interactive tutor mode

    Unlike the automatic agent, there is no hidden target word.
    Feedback comes from the user with instructions provided, and that feedback is used to
    prune the candidate set and recommend the next guess.
    """

    def __init__(
        self,
        strategy_cls: Type[Strategy],
        starting_word: str,
        use_intersecting_guesses: bool = True,
    ) -> None:
        self.solver = Solver(target=None, use_intersecting=use_intersecting_guesses)
        self.dictionary: Dictionary = self.solver.puzzle.dictionary
        self.feedback: LetterFeedback = self.dictionary.feedback
        self.strategy: Strategy = strategy_cls(self.dictionary)
        self.starting_word = starting_word.upper()
        self.guesses: List[str] = []
        self.candidate_counts: List[int] = []
        self.initial_candidates = len(self.dictionary.answers)

    def remaining_candidates(self) -> int:
        return len(self.dictionary.answers)

    def recommend_next_guess(self) -> str:
        candidates = list(self.dictionary.answers)
        return self.strategy.select_guess(candidates, self.feedback, self.guesses)

    def record_guess(self, guess: str) -> None:
        # Ensure the dictionary applies the latest feedback to prune answers
        self.dictionary._update()  

        self.guesses.append(guess.upper())
        # record candidate count AFTER pruning
        self.candidate_counts.append(self.remaining_candidates())


#arguments to provide
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive Wordle tutor using pluggable AI strategies."
    )
    parser.add_argument(
        "-s",
        "--strategy",
        choices=STRATEGY_REGISTRY.keys(),
        default="baseline",
        help="Which strategy to use for recommendations (default: baseline).",
    )
    parser.add_argument(
        "-w",
        "--starting-word",
        default="SLATE",
        help="Starting word to suggest on the first move (default: SLATE).",
    )
    parser.add_argument(
        "--no-intersecting",
        action="store_true",
        help="Disable original intersecting guess behavior in the underlying engine.",
    )
    parser.add_argument(
        "--max-guesses",
        type=int,
        default=6,
        help="Maximum number of guesses to step through (default: 6).",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="If provided, save a TXT and CSV summary with this prefix.",
    )
    return parser.parse_args()


def save_session(prefix: str, strategy_name: str, session: TutorSession, solved: bool) -> None:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    base = f"{prefix}_tutor_{strategy_name}_{session.starting_word}_{timestamp}"

    txt_name = f"{base}.txt"
    csv_name = f"{base}.csv"

    # Txt summary
    with open(txt_name, "w", encoding="utf-8") as f:
        f.write("Wordle Tutor Session Summary\n")
        f.write("----------------------------\n\n")
        f.write(f"Strategy:        {strategy_name}\n")
        f.write(f"Starting word:   {session.starting_word}\n")
        f.write(f"Solved:          {'YES' if solved else 'NO'}\n")
        f.write(f"Total guesses:   {len(session.guesses)}\n")
        f.write(f"Initial answers: {session.initial_candidates}\n")
        f.write("\nGuess progression:\n")
        for idx, guess in enumerate(session.guesses, start=1):
            remaining = session.candidate_counts[idx - 1] if idx - 1 < len(session.candidate_counts) else -1
            f.write(f"  {idx}: {guess}  (remaining candidates after feedback: {remaining})\n")

    # CSV detail: step, guess, remaining_candidates
    with open(csv_name, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["step", "guess", "remaining_candidates"])
        for idx, guess in enumerate(session.guesses, start=1):
            remaining = session.candidate_counts[idx - 1] if idx - 1 < len(session.candidate_counts) else -1
            writer.writerow([idx, guess, remaining])

    print(f"\nSaved session summary to: {txt_name}")
    print(f"Saved session details to: {csv_name}")

# Instructions outputted intuitively, assumes user has played wordle but still simple to following along 
def main() -> None:
    args = parse_args()

    strategy_name = args.strategy
    strategy_cls = STRATEGY_REGISTRY[strategy_name]
    use_intersecting = not args.no_intersecting
    starting_word = args.starting_word.upper()

    print()
    print("==============================================")
    print("        Wordle Tutor - Interactive Mode       ")
    print("==============================================")
    print(f"Strategy:       {strategy_name}")
    print(f"Starting word:  {starting_word}")
    print("Instruction:")
    print("  - Play Wordle on your phone (or wherever) as usual.")
    print("  - After each guess, enter the feedback here (green/yellow).")
    print("  - This tutor will track remaining candidates and suggest a next guess for you.")
    print("  - CTRL+C at any time to quit.")
    print("==============================================\n")

    session = TutorSession(
        strategy_cls=strategy_cls,
        starting_word=starting_word,
        use_intersecting_guesses=use_intersecting,
    )

    solved = False
    max_guesses = args.max_guesses

    # First suggested guess is the starting word 
    # Sticking with SLATE 
    next_guess = starting_word

    try:
        step = 1
        while step <= max_guesses:
            print(f"\n--- Guess {step} ---")
            remaining = session.remaining_candidates()
            print(f"Remaining candidates BEFORE this guess: {remaining}")

            print(f"Recommended guess ({strategy_name}): {next_guess}")
            user_guess = input(
                "Enter the word you actually played in Wordle "
                f"(press ENTER to use {next_guess}): "
            ).strip().upper()

            if not user_guess:
                user_guess = next_guess

            # Wrong input accounting
            if len(user_guess) != 5 or not user_guess.isalpha():
                print("Please enter a valid 5-letter word (letters only).")
                continue 

            # Ask if this guess solved the puzzle.
            solved_input = input(
                f"Did this guess ({user_guess}) solve the puzzle (all green)? [y/n]: "
            ).strip().lower()
            if solved_input.startswith("y"):
                # Mark solved- in the engine, we can treat as all-green
                self_green = user_guess.upper()
                # Register guess with all green feedback
                session.solver.guess(user_guess, self_green, None)
                session.record_guess(user_guess)
                solved = True
                # (Im keeping the same celebration as given repo)
                print("\n🎉 Marked as solved! Great job.")
                break

            # Else, ask for detailed feedback
            # Ask user for detailed green and their positions 
            # Ask user for yellow letters 
            print(
                "\nEnter the feedback from Wordle:\n"
                "  - GREEN pattern: 5 characters, use '_' for non green positions.\n"
                "    Example:  _R_AN  (R and A and N are green, others not)\n"
                "  - YELLOW letters: type all yellow letters (any order), or press ENTER if none.\n"
                "    Example:  oe   (if O and E were yellow somewhere)\n"
            )

            green_pattern = input("GREEN pattern (e.g. _R_AN, or _____ if none): ").strip().upper()
            if not green_pattern:
                green_pattern = "_____"
            if len(green_pattern) != 5:
                print("Please enter exactly 5 characters for the GREEN pattern.")
                continue 

            yellow_letters = input("YELLOW letters (e.g. oe, or ENTER if none): ").strip().upper()
            if yellow_letters == "":
                yellow_letters = None

            # Feed feedback into the solver engine
            session.solver.guess(user_guess, green_pattern, yellow_letters)
            session.dictionary._update()
            # Record the guess after feedback has pruned candidates
            session.record_guess(user_guess)

            # Show updated state
            remaining_after = session.remaining_candidates()
            print(f"\nUpdated remaining candidates AFTER feedback: {remaining_after}")

            # Show some top candidate words (for insight).
            sample = list(session.dictionary.answers)[:10]
            if sample:
                print("Sample of remaining candidates:", ", ".join(sample))

            # Ask the strategy for the next recommended guess
            next_guess = session.recommend_next_guess()
            print(f"Next recommended guess ({strategy_name}): {next_guess}")

            step += 1

        if not solved:
            print("\nReached maximum number of guesses for this tutor session. Fail")
        else:
            print(f"\nSolved in {len(session.guesses)} guesses using strategy '{strategy_name}'.")

        # Optionally save session to files.
        if args.prefix:
            save_session(args.prefix, strategy_name, session, solved)

    except KeyboardInterrupt:
        print("\n\nSession interrupted by user (CTRL+C).")
        if args.prefix:
            save_session(args.prefix, strategy_name, session, solved)


if __name__ == "__main__":
    main()
