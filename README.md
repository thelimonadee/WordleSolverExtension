# WordleSolverExtension
For CPSC481 AI Project  
*** Instructions on how to run these files for now ****

# Running our Wordle AI System:

This project extends the original Wordle solver (cited down below) with a modular AI strategy layer (Baseline, Entropy, Bayesian, A*) and provides two ways to use the system:
1. Autonomous Simulation Mode (run many games, compute averages, export results)
2. Interactive Tutor Mode (play real Wordle with AI guidance)

Below are the commands you can run in VS Code or any terminal inside the project directory.

## 1. Autonomous Simulation Mode:
Runs the AI agent automatically on many target words (similar to the original repo’s wordle_runner.py) and outputs:
* per-game results,
* overall stats (mean guesses, distribution),
* a TXT summary, a PNG bar chart,
* a CSV results file (for statistic/Colab analysis)

commands:

```
python experiment_runner.py --strategy baseline --starting-word SLATE
```
```
python experiment_runner.py --strategy entropy --starting-word SLATE
```
```
python experiment_runner.py --strategy bayes    --starting-word SLATE 
```
```
python experiment_runner.py --strategy astar    --starting-word SLATE 
```

Strategy Desc:
* baseline- Original solver behavior (letter frequency + intersecting). Comparisons sake
* entropy- Informed search maximizing expected information gain
* bayes- Bayesian belief-state update + MAP selection
* astar- A* guided evaluation f(n) = g(n) + h(n) on belief states

Some other commands:
Run a fixed number of games:
```
python experiment_runner.py --strategy bayes --num-games 200
```

Run ALL 2315 NYT answers:
```
python experiment_runner.py --strategy astar --csv
```

## 2. Interactive Tutor Mode
Lets you play Wordle (on NYT website, phone, or wherever (5 letters)) while the AI:
* tracks remaining candidates
* suggests the optimal next guess
* shows examples of candidates
* exports session logs (TXT + CSV), summary 

Commands to start:
Choose a strat ex, default =baseline:
```
python tutor_cli.py
```
```    
python tutorCli.py --strategy entropy
```
```
python tutorCli.py --strategy bayes
```
```
python tutorCli.py --strategy astar
```

Ability to choose a different starting word:
```
python tutorCli.py --strategy entropy --starting-word CRANE
```

After running, follow the guided instructions and play 'guided' by the AI/strategy.

## WHERE TO RUN THESE COMMANDS
Open your terminal in VS Code inside the folder containing:
* experiment_runner.py
* tutor_cli.py
* strategies.py
* wordle_agent.py
* wordle_solver.py


# ORIGINAL SOURCE CITATION AND ACKNOWLEDGMENT:

This project extends and builds upon the open-source Wordle solver by Josh Stephenson:  
Stephenson, Josh. wordle-solver (GitHub Repository).  
Available at: https://github.com/joshstephenson/Wordle-Solver  
Accessed: December 2025.

My groupmembers and I do not claim authorship of the underlying solver logic All such components remain the intellectual work of the original author.

Our contribution consists of an AI Strategy Layer built on top of the existing solver, including:
-A modular Strategy interface
-BaselineFrequencyStrategy wrapper
-EntropyHeuristicStrategy (informed search)
-BayesianBeliefStrategy (belief-state + Bayes updates)
-AStarEvaluationStrategy (A*-style evaluation)
-Experiment runner with our own automated analysis (TXT/CSV/PNG outputs)
-Our own Interactive tutor CLI using pluggable strategies

This extension is intended for academic use as part of a university AI course project.

(Citations for report later:

We extend the open-source Wordle solver by Stephenson (2022), available at https://github.com/joshstephenson/Wordle-Solver 

OR for the reference page: 

Stephenson, J. (2022). *Wordle-Solver* [Source code]. GitHub.
https://github.com/joshstephenson/Wordle-Solver )

