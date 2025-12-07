# ui/uiController.py
#
# GUI for "tutor" that wraps the same 'agent' used in tutorCli.py.
#
#   - The hidden Wordle solution produces a 'belief state' over all possible words.
#   - Underlying Solver + Dictionary maintain this belief state by pruning
#     candidates that are inconsistent with the user's feedback (evidence), that they would input manually.
#   - A Strategy (baseline / entropy hueristic / Bayesian / A*) is an 'informed search policy'
#     over this belief state, choosing the next guess to minimize expected effort.
#
#   = This file instantiates the same TutorSession used in tutorCli.py, which itself wraps:
#       -Solver  (state transition model / belief update)
#       -Dictionary (current candidate set, belief state)
#       -Strategy (decision rule: entropy heuristic, Bayesian, A* evaluation, etc.)
#   - Exposes that behavior through a Tk GUI: the user provides feedback, the
#     agent updates its belief state, and the chosen strategy proposes the next guess
#
#   By default, our main strategy is an implicit hueristic, entropy hueristic that we deemed most 'efficient'
#   -hueristic method: idea of estimating how far a state is from a goal 
#   -entropy hueristic: treatement of each "belief state" (remaining candidates) as a probability distribution
#    over answers and prefer gueses that reduce uncertainty the most in expectation 
#   -implicit hueristic: strategy scores guesses by how well they split/ partition candidate set (how much info
#    they are expected to provide). That scoring func behaves like an entropy-based h(n) defioned over belief states.

from __future__ import annotations

from typing import Optional

from tutorCli import STRATEGY_REGISTRY, TutorSession


class UiController:
    """
    GUI controller that mirrors tutorCli.py behavior.

    Aarchitecture:
      - We reuse TutorSession from tutorCli.py:
          - TutorSession wraps the original Solver + Dictionary + Strategy from
            strategies.py (“agent” / decision maker).
          - Solver + Dictionary implement the environment dynamics and belief
            update: given (guess, feedback) they prune inconsistent worlds.
          - Strategy implements the "AI":
              - BaselineFrequencyStrategy: implicit heuristic over letter freq.
              - EntropyHeuristicStrategy: informed search heuristic that
                maximizes expected information gain (reduces entropy of the
                belief state).
              - BayesianBeliefStrategy: explicit probability distribution P(w)
                over candidate words, updated via Bayes-style filtering.
              - AStarEvaluationStrategy: A*-style f(n) = g(n) + h(n) over the
                belief state, where g = guesses so far and h estimates remaining
                difficulty from partition sizes.
      - This UiController just:
          - Creates / resets a TutorSession based on the chosen strategy.
          - For each turn:
                - Shows the agent’s recommended guess.
                - Lets the user accept or override that guess.
                - Accepts feedback in the same format as tutorCli.py
                  (GREEN pattern + YELLOW letters).
                - Passes that feedback into TutorSession (and therefore into
                  Solver + Dictionary).
                - Requests a new recommendation from the Strategy.
    """

    def __init__(self, view=None):
        self.view = view

        # Default strategy = entropy:
        #   - Treats guessing as an information gain problem and tries to
        #     minimize uncertainty in the belief state (high heuristic quality).
        self.strategy_name = "entropy"

        # Starting word (first action) is fixed to SLATE, as in tutorCli.py and throughout project
        self.starting_word = "SLATE"

        self.use_intersecting = True

        # Cap Wordle at 6 guesses.
        self.max_guesses = 6

        # Live TutorSession instance (Solver + Dictionary + Strategy)
        self.session: Optional[TutorSession] = None

        # The next recommended guess from the Strategy (liketutorCli's `next_guess`).
        self.next_guess: Optional[str] = None

        # UI / reporting.
        self.step = 0        
        self.solved = False  

    # ------------------------------------------------------------------
    # Create / reset the TutorSession (agent)
    # ------------------------------------------------------------------

    def _create_session(self):
        """
        TutorSession that wraps:
          - Solver   (transition model / belief update),
          - Dictionary (belief state over words),
          - Strategy (entropy / bayes / A* / baseline).

        GUI “binds” to a particular AI configuration:
          - strategy_name selects which informed search / probabilistic method
            to use (entropy heuristic, MAP via Bayesian belief, A* f(n), etc.).
          - starting_word defines the first action in the episode.
        """
        strategy_cls = STRATEGY_REGISTRY[self.strategy_name]
        self.session = TutorSession(
            strategy_cls=strategy_cls,
            starting_word=self.starting_word,
            use_intersecting_guesses=self.use_intersecting,
        )
        self.step = 0
        self.solved = False
        self.next_guess = self.starting_word.upper()

        if self.view:
            self.view.clearBoard()
            self.view.setStatus(
                f"Strategy: {self.strategy_name}, "
                f"starting word: {self.starting_word}, "
                f"initial candidates: {self.session.initial_candidates}"
            )
            # Show the initial recommended action (SLATE by default)
            self.view.showSuggestedGuess(self.next_guess)

    # ------------------------------------------------------------------
    # View wiring
    # ------------------------------------------------------------------

    def attachView(self, view):
        """
        Called from tkApp when the Tk view is constructed.
        """
        self.view = view
        self._create_session()

    # ------------------------------------------------------------------
    # Strategy managemnt (switch between entropy / bayes / A*)
    # ------------------------------------------------------------------

    def changeStrategy(self, name: str):
        """
        User selects strategy change from the dropdown (baseline / entropy / bayes / astar).

        Behavior:
          - Validate the name against STRATEGY_REGISTRY.
          - Rebuild the TutorSession with the new Strategy class.
          - Reset the belief state to the full answer set and restart from SLATE.

        Swaps out method while keeping the environment model (Solver + Dictionary) the same.
        """
        if name not in STRATEGY_REGISTRY:
            if self.view:
                self.view.setStatus(f"Unknown strategy '{name}'.")
            return

        self.strategy_name = name
        # Recreate the session with the new strategy (fresh belief and g(n)=0).
        self._create_session()

    # ------------------------------------------------------------------
    # Core flow (mirrors tutorCli loop structure)
    # ------------------------------------------------------------------

    def suggestGuess(self):
        """
        In the CLI version, each iteration prints the current recommended guess

        In the GUI- "Suggest Guess" button re-displays the most
        current recommendation (`next_guess`) and pre-fills the input field.
        """
        if not self.session or not self.next_guess:
            self._create_session()
        if self.view and self.next_guess:
            self.view.showSuggestedGuess(self.next_guess)

    def submitResult(
        self,
        actual_guess: str,
        solved_flag: bool,
        green_pattern: str,
        yellow_letters: Optional[str],
    ):
        """
        Calls by the GUI when the user hits "Submit Result".

        Like tutorCli.py:
          - actual_guess:
              The guess the user actually played. If blank, we fall back to the
              agent's recommended action (`next_guess`), just like pressing ENTER
              in the CLI version.
          - solved_flag:
              True if this guess solved the puzzle (all letters green).
              (Corresponds to the "Did this guess solve the puzzle?")
          - green_pattern:
              5-char string such as "_R_AN" or "_____" (no green).
              Encodes which positions are in the correct spot.
          - yellow_letters:
              String like "OE" for letters present but misplaced, or None / ""
              if there are no yellow letters.

        Flow:
          1) Determine which action was actually taken (user guess vs policy suggestion).
          2) Interpret the feedback as evidence:
               - all green (goal state reached), or
               - partial feedback (constraining the belief state).
          3) Call into Solver.guess(), which updates the belief state by
             removing inconsistent candidate worlds (filtering).
          4) Ask Strategy to compute the next best action given this updated
             belief state (entropy / MAP / A*).
          5) Reflect the new state and recommendation back to the GUI.
        """

        if self.session is None:
            self._create_session()

        assert self.session is not None

        # If we already reached a goal (user marked solved)
        if self.solved:
            if self.view:
                self.view.setStatus("Puzzle already marked as solved. Start a new session.")
            return

        # 1. Decides which guess is used (blank => use agent's recommended action).
        if not actual_guess:
            if not self.next_guess:
                if self.view:
                    self.view.setStatus("No suggested guess available.")
                return
            user_guess = self.next_guess
        else:
            user_guess = actual_guess.strip().upper()

        if len(user_guess) != 5 or not user_guess.isalpha():
            if self.view:
                self.view.setStatus("Guess must be a 5-letter alphabetic word.")
            return

        self.step += 1

        # 2. If the guess solved the puzzle, model this as an "all-green" pattern.
        if solved_flag:
            self_green = user_guess  # every position is correct

            self.session.solver.guess(user_guess, self_green, None)
            self.session.record_guess(user_guess)

            self.solved = True
            remaining = self.session.remaining_candidates()
            moves = len(self.session.guesses)

            if self.view:
                # details
                self.view.appendHistoryLine(
                    guess=user_guess,
                    green=self_green,
                    yellow="",
                    remaining=remaining,
                )
                # Summary message that ties back to evaluation metrics:
                #   - moves = depth of solution
                #   - initial_candidates = size of initial belief state.
                summary = (
                    f"Solved! Strategy '{self.strategy_name}' finished in "
                    f"{moves} move{'s' if moves != 1 else ''}. "
                    f"Initial candidates: {self.session.initial_candidates}, "
                    f"remaining: {remaining}."
                )
                # Append to history 
                self.view.appendSummaryMessage(summary)
                self.view.setStatus(summary)

            self.next_guess = None
            return

        # 3. Not solved: interpret GREEN pattern + YELLOW letters as soft evidence.
        green_pattern = green_pattern.strip().upper()
        if not green_pattern:
            green_pattern = "_____"
        if len(green_pattern) != 5:
            if self.view:
                self.view.setStatus("GREEN pattern must be exactly 5 characters (use '_' for non-green).")
            return

        if yellow_letters:
            yellow_letters = yellow_letters.strip().upper()
            if yellow_letters == "":
                yellow_letters = None
        else:
            yellow_letters = None

        # 4. Feed feedback into the Solver engine (same as CLI).
        #
        #   - Call is like applying a likelihood function
        #     P(feedback | w) that is 0 for inconsistent words and 1 for consistent.
        #   - The resulting candidate set is the normalized posterior over worlds
        self.session.solver.guess(user_guess, green_pattern, yellow_letters)
        self.session.dictionary._update()
        self.session.record_guess(user_guess)

        remaining_after = self.session.remaining_candidates()

        # 5. Update the GUI's to show the sequence of evidence and
        #    how the belief state is shrinking with each step.
        if self.view:
            self.view.appendHistoryLine(
                guess=user_guess,
                green=green_pattern,
                yellow=yellow_letters or "",
                remaining=remaining_after,
            )

        # 6. Asks the Strategy to choose the next action in belief space.
        #
        # Depending on strategy_name:
        #   - entropy: maximizes expected information gain (informed search).
        #   - bayes: returns a MAP word under the current posterior P(w).
        #   - astar: uses f(n) = g(n) + h(n) to approximate remaining search cost.
        #   - baseline: reuses the original letter-frequency heuristic.
        self.next_guess = self.session.recommend_next_guess()

        if self.view:
            if self.next_guess:
                self.view.showSuggestedGuess(self.next_guess)
                self.view.setStatus(
                    f"Remaining candidates: {remaining_after} "
                    f"(strategy={self.strategy_name})."
                )
            else:
                self.view.setStatus(
                    f"Remaining candidates: {remaining_after}. "
                    f"No further recommendation available."
                )
