# ui/wordleView.py

"""

Implements the Tkinter GUI for the Wordle AI Tutor, a visual
frontend that interacts with the UiController (uiController.py), 
which wraps the same AI agent and inference logic used in tutorCli.py.

pure presentation layer:

    - It displays the current recommended guess from the AI (the agent's action).
    - It collects user input:
          - an optional override guess,
          - whether the guess solved the puzzle,
          - GREEN pattern feedback,
          - YELLOW letter feedback.
    - It sends these inputs to the controller.
    - It displays candidate set shrinkage and solver progress in the history box.

Strategies

    - BaselineFrequencyStrategy  
          A simple heuristic that prioritizes high frequency letters.

    - EntropyHeuristicStrategy  
          Implements an entropy-based heuristic aligned with informed search principles.
          Estimates the expected reduction in uncertainty (information gain)
          caused by each guess, making it an implicit heuristic h(n) defined
          over the belief states.

    - BayesianBeliefStrategy  
          Performs Bayesian updating of P(word | evidence).  
          The belief state is literally a probability distribution conditioned
          on accumulated feedback.

    - AStarEvaluationStrategy  
          Applies an A*-style evaluation:  
              f(n) = g(n) + h(n)  
          where g(n) = number of guesses so far,  
          and h(n) estimates the remaining difficulty using Wordle-specific
          heuristics (ex: partition quality)

This GUI visualizes the interaction loop where the agent proposes an
action, the user supplies feeback, the belief shrinks, and a new informed
action is computed.
"""

import tkinter as tk


class WordleView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller

        root.title("Wordle AI Tutor")
        root.geometry("700x600")

        mainFrame = tk.Frame(root, padx=10, pady=10)
        mainFrame.pack(fill=tk.BOTH, expand=True)

        # ------------------------------------------------------------------
        # Title
        # ------------------------------------------------------------------
        titleLabel = tk.Label(
            mainFrame,
            text="Wordle AI Tutor",
            font=("Helvetica", 16, "bold"),
        )
        titleLabel.pack(pady=5)

        # ------------------------------------------------------------------
        # Step 1: Strategy selection
        # ------------------------------------------------------------------
        strategyFrame = tk.Frame(mainFrame)
        strategyFrame.pack(pady=5)

        step1Label = tk.Label(
            strategyFrame,
            text="1). Choose a strategy:",
            font=("Helvetica", 11, "bold"),
        )
        step1Label.pack(pady=(0, 3))

        rowFrame = tk.Frame(strategyFrame)
        rowFrame.pack()

        tk.Label(rowFrame, text="Strategy:").pack(side=tk.LEFT, padx=(0, 4))

        self.strategyVar = tk.StringVar(value="entropy")
        strategyMenu = tk.OptionMenu(
            rowFrame,
            self.strategyVar,
            "baseline",
            "entropy",
            "bayes",
            "astar",
        )
        strategyMenu.pack(side=tk.LEFT, padx=4)

        applyButton = tk.Button(
            rowFrame,
            text="Apply",
            command=self._onApplyStrategy,
        )
        applyButton.pack(side=tk.LEFT, padx=4)

        descLabel = tk.Label(
            strategyFrame,
            text=(
                "Entropy (default) is the heuristic method that we deemed often provides "
                "the most efficient early pruning of the search space."
            ),
            wraplength=500,
            justify="center",
            fg="gray",
            font=("Helvetica", 9),
        )
        descLabel.pack(pady=(2, 0))

        # ------------------------------------------------------------------
        # Suggested guess
        # ------------------------------------------------------------------
        self.suggestLabel = tk.Label(
            mainFrame,
            text="Suggested guess: SLATE",
            font=("Helvetica", 14),
        )
        self.suggestLabel.pack(pady=(12, 6))

        # ------------------------------------------------------------------
        # Step 2: Actual guess
        # ------------------------------------------------------------------
        step2Label = tk.Label(
            mainFrame,
            text="2). Actual guess (leave blank to use suggested word above):",
            font=("Helvetica", 11, "bold"),
        )
        step2Label.pack()

        self.actualGuessEntry = tk.Entry(
            mainFrame,
            width=12,
            font=("Consolas", 14),
            justify="center",
        )
        self.actualGuessEntry.pack(pady=(3, 8))

        # ------------------------------------------------------------------
        # Step 3: Solved checkbox
        # ------------------------------------------------------------------
        solvedFrame = tk.Frame(mainFrame)
        solvedFrame.pack(pady=(2, 10))

        step3Label = tk.Label(
            solvedFrame,
            text="3). Did this word solve the game?",
            font=("Helvetica", 11, "bold"),
        )
        step3Label.pack(side=tk.LEFT)

        self.solvedVar = tk.BooleanVar(value=False)
        solvedCheck = tk.Checkbutton(
            solvedFrame,
            variable=self.solvedVar,
        )
        solvedCheck.pack(side=tk.LEFT, padx=(10, 0))  # right beside text

        # ------------------------------------------------------------------
        # Step 4: GREEN + YELLOW input 
        # ------------------------------------------------------------------
        step4Label = tk.Label(
            mainFrame,
            text="4). Feedback from Wordle:",
            font=("Helvetica", 11, "bold"),
        )
        step4Label.pack(pady=(5, 2))

        feedbackFrame = tk.Frame(mainFrame)
        feedbackFrame.pack(pady=4)

        # --- header row ---
        headers = tk.Frame(feedbackFrame)
        headers.pack()

        tk.Label(
            headers,
            text="GREEN pattern   (ex: _R_AN or _ _ _ _ _)",
            font=("Helvetica", 10),
        ).grid(row=0, column=0, padx=20)

        tk.Label(
            headers,
            text="YELLOW letters (type yellow letters)",
            font=("Helvetica", 10),
        ).grid(row=0, column=1, padx=20)

        # entry row
        entries = tk.Frame(feedbackFrame)
        entries.pack()

        self.greenEntry = tk.Entry(
            entries,
            width=12,
            font=("Consolas", 14),
            justify="center",
        )
        self.greenEntry.grid(row=1, column=0, padx=20, pady=4)

        self.yellowEntry = tk.Entry(
            entries,
            width=12,
            font=("Consolas", 14),
            justify="center",
        )
        self.yellowEntry.grid(row=1, column=1, padx=20, pady=4)

        # ------------------------------------------------------------------
        # Button
        # ------------------------------------------------------------------
        buttonFrame = tk.Frame(mainFrame)
        buttonFrame.pack(pady=6)

        suggestButton = tk.Button(
            buttonFrame,
            text="Suggest Guess",
            command=self._onSuggestGuess,
        )
        suggestButton.pack(side=tk.LEFT, padx=5)

        submitButton = tk.Button(
            buttonFrame,
            text="Submit Result",
            command=self._onSubmitResult,
        )
        submitButton.pack(side=tk.LEFT, padx=5)

        # ------------------------------------------------------------------
        # History box
        # ------------------------------------------------------------------
        self.historyBox = tk.Listbox(mainFrame, height=7)
        self.historyBox.pack(fill=tk.BOTH, expand=True, pady=8)

        # ------------------------------------------------------------------
        # Status line
        # ------------------------------------------------------------------
        self.statusLabel = tk.Label(mainFrame, text="Ready", fg="gray")
        self.statusLabel.pack(pady=3)

    # ------- Methods called by controller ----------------------------

    def showSuggestedGuess(self, guess: str):
        self.suggestLabel.config(text=f"Suggested guess: {guess}")
        self.actualGuessEntry.delete(0, tk.END)
        self.actualGuessEntry.insert(0, guess)
        self.actualGuessEntry.focus_set()

    def setStatus(self, text: str):
        self.statusLabel.config(text=text)

    def clearBoard(self):
        self.historyBox.delete(0, tk.END)
        self.actualGuessEntry.delete(0, tk.END)
        self.greenEntry.delete(0, tk.END)
        self.yellowEntry.delete(0, tk.END)
        self.solvedVar.set(False)
        self.suggestLabel.config(text="Suggested guess: ----")

    def appendHistoryLine(self, guess: str, green: str, yellow: str, remaining: int):
        line = f"{guess}  [GREEN={green}, YELLOW={yellow}, REM={remaining}]"
        self.historyBox.insert(tk.END, line)
        self.historyBox.see(tk.END)

    def appendSummaryMessage(self, text: str):
        self.historyBox.insert(tk.END, f"== {text}")
        self.historyBox.see(tk.END)

    # ------- Internal callbacks -----------------------------

    def _onSuggestGuess(self):
        self.controller.suggestGuess()

    def _onSubmitResult(self):
        actual_guess = self.actualGuessEntry.get().strip().upper()
        solved_flag = self.solvedVar.get()
        green_pattern = self.greenEntry.get().strip().upper()
        yellow_letters = self.yellowEntry.get().strip().upper()
        if yellow_letters == "":
            yellow_letters = None

        self.controller.submitResult(
            actual_guess=actual_guess,
            solved_flag=solved_flag,
            green_pattern=green_pattern,
            yellow_letters=yellow_letters,
        )

        self.greenEntry.delete(0, tk.END)
        self.yellowEntry.delete(0, tk.END)
        self.solvedVar.set(False)

    def _onApplyStrategy(self):
        name = self.strategyVar.get()
        self.controller.changeStrategy(name)
