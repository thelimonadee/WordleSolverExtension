# ui/wordleGameApp.py
#
# Auto solver agent:
# This is the "agent plays the whole game" mode:
#   - The user specifies a target word (a hidden solution, sometimes the solution of todays wordle) 
#     and picks a strategy.
#   - The system automatically:
#       - Maintains a belief state = current candidate set (allAnswers filtered by consistency with observed feedback).
#       - Applies the same Strategy classes defined in strategies.py
#         (BaselineFrequencyStrategy, EntropyHeuristicStrategy, BayesianBeliefStrategy,
#          AStarEvaluationStrategy) to choose the next guess.
#       - Uses the low-level _feedback_pattern() engine from strategies.py
#         to simulate the Wordle feedback (GREEN / YELLOW / GREY) for each guess.
#
# Extention of strategies.py:
#   - Reused the exact same Strategy implementations as tutorCli.py and the
#     WordleAgent:
#       - BaselineFrequencyStrategy: implicit heuristic over letter frequencies.
#       - EntropyHeuristicStrategy: entropy based heuristic that prefers guesses
#         with high expected information gain (uncertainty reduction).
#       - BayesianBeliefStrategy: explicitly maintains/uses a probability
#         distribution over candidate words.
#       - AStarEvaluationStrategy: A*-style evaluation f(n) = g(n) + h(n) over
#         the belief state (g = guesses so far, h = heuristic difficulty).
#   - Each Strategy expects a "Dictionary-like" object with an .answers list and,
#     for some strategies, a .next_guess() method. We provide that via DummyDictionary.
#
# Extension to tutorCli.py:
#   - tutorCli.py runs in interactive tutor mode:
#       - The user plays real Wordle elsewhere and provides feedback (GREEN/YELLOW).
#       • The agent (Solver + Dictionary + Strategy) updates the belief state and
#         recommends the next guess.
#   - This file runs instead is the auto-solver mode:
#       • There is no external Solver/Dictionary, instead we:
#           - keep a candidate list (candidates),
#           - compute feedback via _feedback_pattern,
#           - filter candidates directly in this file.
#       - The Strategy only sees the current candidate set + guess history,
#         exactly as in the CLI agent, so the behavior remains aligned with
#         the AI design, just with the environment loop "inlined" here.


import tkinter as tk
import random

from .core.wordList import loadWordList

from strategies import (
    BaselineFrequencyStrategy,
    EntropyHeuristicStrategy,
    BayesianBeliefStrategy,
    AStarEvaluationStrategy,
    _feedback_pattern,
)


class DummyDictionary:
    """
    Purpose: strategies can hold a '.answers' list and
    (for baseline) call 'next_guess()' if needed

    Keeps the Strategy interface consistent without pulling in the entire
    Solver/Dictionary stack
    """
    def __init__(self, answers):
        self.answers = list(answers)

    def next_guess(self):
        return random.choice(self.answers)


STRATEGY_REGISTRY = {
    "baseline": BaselineFrequencyStrategy,
    "entropy": EntropyHeuristicStrategy,
    "bayes": BayesianBeliefStrategy,
    "astar": AStarEvaluationStrategy,
}


class AutoSolverUI:
    """
    Auto-solver window:

      - Treats Wordle as a deterministic search problem with a hidden goal state
        (the target word typed by the user).
      - The search state is the 'belief state' (set of candidate words).
      - At each step:
          1. Use a chosen Strategy as an informed search policy to pick an action (guess).
          2. Simulate feedback via `_feedback_pattern(guess, target)`.
          3. Filter the candidate set to words consistent with that feedback.
          4. Repeat until the goal is found or 6 steps are used.

      Essentially running our agent end to end without user input,
      using the same heuristics as in experiment_runner.py and tutorCli.py.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Wordle Auto Solver")

        # Loads from nyt-answers.txt via core.wordList
        self.allAnswers = loadWordList(listType="answers")

        self._buildLayout()

    def _buildLayout(self):
        self.root.geometry("540x480")

        mainFrame = tk.Frame(self.root, padx=10, pady=10)
        mainFrame.pack(fill=tk.BOTH, expand=True)

        titleLabel = tk.Label(
            mainFrame,
            text="Wordle Auto Solver",
            font=("Helvetica", 16)
        )
        titleLabel.pack(pady=5)

        controlFrame = tk.Frame(mainFrame)
        controlFrame.pack(pady=5, fill=tk.X)

        tk.Label(controlFrame, text="Target word:").pack(side=tk.LEFT)
        self.targetEntry = tk.Entry(
            controlFrame,
            width=8,
            font=("Consolas", 14)
        )
        self.targetEntry.pack(side=tk.LEFT, padx=5)

        tk.Label(controlFrame, text="Strategy:").pack(side=tk.LEFT, padx=(10, 0))

        #entropy = default
        self.strategyVar = tk.StringVar(value="entropy")
        strategyMenu = tk.OptionMenu(
            controlFrame,
            self.strategyVar,
            "baseline",
            "entropy",
            "bayes",
            "astar",
        )
        strategyMenu.pack(side=tk.LEFT, padx=5)

        runButton = tk.Button(
            controlFrame,
            text="Run Auto-Solve",
            command=self._onRun
        )
        runButton.pack(side=tk.LEFT, padx=10)

        self.logBox = tk.Listbox(mainFrame, height=16)
        self.logBox.pack(fill=tk.BOTH, expand=True, pady=5)

        self.statusLabel = tk.Label(mainFrame, text="Enter target and run.", fg="gray")
        self.statusLabel.pack(pady=5)

    # ------------- small helpers ----------------------------------------

    def _setStatus(self, text: str, error: bool = False):
        if error:
            self.statusLabel.config(text=text, fg="red")
        else:
            self.statusLabel.config(text=text, fg="gray")

    def _log(self, line: str):
        self.logBox.insert(tk.END, line)
        self.logBox.see(tk.END)

    @staticmethod
    def _pattern_tuple_to_gy_string(pattern):
        """
        Convert the internal numeric feedback tuple (0/1/2) into a user readable
        'g/y/.' string, stems from original gui we had

        2 -> 'g' (GREEN / correct position)
        1 -> 'y' (YELLOW / wrong position but present)
        0 -> '.' (GREY / not in the word)
        """
        chars = []
        for v in pattern:
            if v == 2:
                chars.append("g")
            elif v == 1:
                chars.append("y")
            else:
                chars.append(".")
        return "".join(chars)

    # ------------- main auto-solve logic --------------------------------

    def _onRun(self):
        """
        Core autosolver loop:

          1. Read the target word and strategy choice from the GUI
          2. Initialize candidates = full answer set and a DummyDictionary
          3. For up to 6 guesses:
               a. If first step, force SLATE (fixed starting point).
               b. Other, call strategy.select_guess(candidates, feedback=None,
                  guesses_so_far=).
               c. Compute feedback = _feedback_pattern(guess, target).
               d. Filter candidates to those with identical feedback vs guess
               e. Log guess, pattern, remaining, and a sample of remaining words
               f. If pattern is all GREEN, we solved -> stop
          4. Update status with success/failure info.
        """
        self.logBox.delete(0, tk.END)

        target = self.targetEntry.get().strip().lower()
        if len(target) != 5 or not target.isalpha():
            self._setStatus("Target must be a 5-letter word.", error=True)
            return

        if target not in self.allAnswers:
            self._setStatus("Target not in answer list.", error=True)
            return

        strategy_name = self.strategyVar.get()
        if strategy_name not in STRATEGY_REGISTRY:
            self._setStatus(f"Unknown strategy '{strategy_name}'.", error=True)
            return

        candidates = list(self.allAnswers)
        dummy_dict = DummyDictionary(candidates)

        strategy_cls = STRATEGY_REGISTRY[strategy_name]
        strategy = strategy_cls(dummy_dict)

        guesses_so_far = []
        # starts and for consistency- SLATE
        starting_word = "slate"  

        self._setStatus(
            f"Running auto-solve for '{target.upper()}' using "
            f"{strategy_name.upper()} (start=SLATE)..."
        )

        max_guesses = 6
        for step in range(1, max_guesses + 1):
            # Step 1 use SLATE as first guess
            if step == 1:
                guess = starting_word
            else:
                guess = strategy.select_guess(
                    candidates,
                    feedback=None,
                    guesses_so_far=guesses_so_far,
                )
            guess = guess.lower()

            pat_tuple = _feedback_pattern(guess, target)
            pat_str = self._pattern_tuple_to_gy_string(pat_tuple)

            new_candidates = [
                w for w in candidates
                if _feedback_pattern(guess, w) == pat_tuple
            ]

            self._log(
                f"{step}. {guess.upper()}  [{pat_str}]  -> remaining={len(new_candidates)}"
            )
            sample = ", ".join(new_candidates[:8])
            if sample:
                self._log(f"    sample: {sample}")

            guesses_so_far.append(guess)
            candidates = new_candidates
            dummy_dict.answers = candidates

            if all(v == 2 for v in pat_tuple):
                self._setStatus(
                    f"Solved '{target.upper()}' in {step} guesses using "
                    f"{strategy_name.upper()} (start=SLATE)."
                )
                return

        self._setStatus(
            f"Failed to solve '{target.upper()}' within {max_guesses} guesses "
            f"using {strategy_name.upper()} (start=SLATE).",
            error=True,
        )


def runGame():
    root = tk.Tk()
    app = AutoSolverUI(root)
    root.mainloop()
