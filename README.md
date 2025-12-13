# WordleSolverExtension
For CPSC481 AI Project - Michael Joseph Lim  

# Wordle AI Solver & Tutor  
## -Heuristic and Data-Driven Search Agent    
This project implements an intelligent Wordle-solving agent capable of both full autonomous play and real time tutoring for human players playing wordle on their devices.  
The system combines concepts from state-space search, informed heuristics, and probabilistic reasoning to efficiently solve the official Wordle puzzle set (2,315 accepted answers).  
Built on top of an extended open-source solver (cited below), this project introduces:  
* Explicit informed search heuristics (entropy hueristic/expected candidate reduction, A*-style evaluation)  
* Bayesian belief-state updates  
* A unified strategy interface  
* A complete simulation pipeline for evaluating solver performance  
* An interactive GUI Tutor and an Auto Solve GUI  
* A full CLI framework for running experiments, running simulations, and generating analysis data  
The goal is to design an agent that solves Wordle with maximum efficiency — minimizing average guess count while keeping failures near zero.
# Features:  
### Multiple AI Stragies were implemented in order to seek a more efficient solution  
* BaselineFrequencyStrategy:  inherited from original repo- ositional letter-frequency heuristic  
* EntropyHeuristicStrategy: informed search heuristic maximizing information gain  
* BayesianBeliefStrategy: maintains explicit P(word | evidence)
* AStarEvaluationStrategy — A*-style f(n)=g(n)+h(n) over belief states
### Three Modes of Use  
* Autonomous Simulation Mode  
Runs all 2,315 official answers, outputs stats, CSV for modeling, and plots
*  Interactive Tutor Mode (CLI or GUI)  
Allows user to play Wordle yourself and let the agent recommend optimal guesses.
*  AutoSolve (GUI)
Ability to map the steps of applied strategy to a target word.
### Full Analytics Pipeline  
experiment_runner.py generates:  
* Mean guesses
* Failure counts
* Distribution histograms (guess distributions)
* Txt summaries
* CSV logs for modeling (google colab notebook)
Inspired by baseline/open-source repo
### Modular Architecture  
* Strategies interchange easily  
* Belief state updates centralized in solver  
* Separate CLI and GUI layers  
* Clean state space abstraction (states, actions, transitions, goal)
# Repository Structure (Core Files)  
```
/strategies.py         — All strategy classes. Our engine (baseline, entropy-hueristic, bayes, A*)
/wordle_solver.py      — Original solver engine (feedback logic, dictionary)
/puzzle.py             — Core Wordle constraint model
/wordle_agent.py       — Autonomous agent wrapper
/experiment_runner.py  — Simulation engine (ability to view simulated runs via command line) + CSV output
/tutorCli.py           — CLI tutor for real Wordle players
/ui/                   — Tkinter GUI implementation, wrapped around our revamped engine
    uiController.py
    wordleView.py
    wordleGameApp.py
```
# How it Works  
### State Representation    
* Each world state = set of candidate words consistent with feedback  
* Feedback (green/yellow/gray) prunes states  
* Strategies choose actions over this evolving belief state    
### Goal  
Solve the hidden Wordle word in the fewest expected guesses, lowest guess average.    
### Why Entropy as our default strategy?  
Entropy scoring partitions the belief state by feedback pattern and chooses the guess that maximizes expected information gain, yielding highly efficient reductions.  
<img width="960" height="540" alt="readme2" src="https://github.com/user-attachments/assets/97b968de-da0d-46c8-a68d-21a2e3e8f518" />  
### Google Colab recording our data:  
https://colab.research.google.com/drive/1pDSBOovB33FkzocuhYK-KggyTFtu7Uwa?usp=sharing#scrollTo=fLx9wfgwl0aC  
* Interpretation of our results
* Conclusion and validation of our method towards reaching our objective. 

# Example output (of simulation)   
```
Strategy: entropy
Mean guesses: 3.5401
Solved within 4 guesses: 90.45%
Failures ( >6 guesses ): 8 / 2315
```
# Findings:  
<img width="960" height="540" alt="readme1" src="https://github.com/user-attachments/assets/effbc19d-e541-494f-8520-8551e1943e31" />  

* Entropy heuristic produced the lowest average guess count.  
* Bayesian and A* methods showed stable, consistent reasoning from belief states.    
* Baseline frequency heuristic performed well but was outperformed in deep uncertainty cases. Still a safe option, but we believe our heuristic is more efficient.     
* Combining heuristics with data driven inference yields a meaningfully more efficient solver.      
 
# Running our Wordle AI System:

This project extends the original Wordle solver (cited down below) with a modular AI strategy layer (Baseline, Entropy, Bayesian, A*) and provides two ways to use the system:
1. Autonomous Simulation Mode (run many games, compute averages, export results)
2. Interactive Tutor Mode (play real Wordle with AI guidance)

Below are the commands you can run in VS Code or any terminal inside the project directory.

## 1. Autonomous Simulation Mode:
Runs the AI agent automatically on many target words (nyt list of words, similar to the original repo’s wordle_runner.py) and outputs:
* per-game results,
* overall stats (mean guesses, distribution),
* a TXT summary, a PNG bar chart,
* a CSV results file (for statistic/Colab analysis)

commands:

```
python experiment_runner.py --strategy baseline --starting-word SLATE --csv
```
```
python experiment_runner.py --strategy entropy --starting-word SLATE --csv
```
```
python experiment_runner.py --strategy bayes --starting-word SLATE --csv
```
```
python experiment_runner.py --strategy astar --starting-word SLATE --csv
```

Strategy Description Recap:
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

# 3). Running the GUI (AI Tutor and Autonomous solver agent)  
Included within this project are 2 graphical interfaces built on top of the AI strategies implemented (baseline (extension of open-source repo), entropy huersitic, bayes, astar). This GUI wraps around the engine aforementioned above, strategies.py, and visualizes tutorCli.py form the CLI to GUI. 

### A). Wordle AI Tutor  
This opens a desktop window where you manually enter the GREEN pattern, YELLOW letters, and whether the guess solved the puzzle.  
The AI maintains the candidate set and recommends the next move mirroring tutorCli.py but in a graphical interface.  
To run the tutor mode:  
1. Open navigate to project folder then navigate to main.py
2. Uncomment: **runApp()** and ensure autonomous solver line is commented: **# runGame()**  
3. In the terminal:
```
python main.py
```
You should now see the Wordle AI Tutor window which should be familiar from tutorCli.py.  
### B). Autonomous AI Agent solver  
This GUI lets the agent solve a chosen target word automatically with no manual  user feedback needed.
It uses the same strategies as the simulation code but presents the run visually, step by step, with remaining candidate counts.    
1. Open navigate to project folder then navigate to main.py  
2. Uncomment: **runGame()** and ensure AI tutor line is commented: **# runApp()**    
3. In the terminal:  
```
python main.py
```
You will then see the Auto solver window where you type a 5 letter target word and select a strategy. 


# ORIGINAL SOURCE CITATION AND ACKNOWLEDGMENT:

This project extends and builds upon the open-source Wordle solver by Josh Stephenson:  
Stephenson, Josh. wordle-solver (GitHub Repository).  
Available at: https://github.com/joshstephenson/Wordle-Solver  
Accessed: December 2025.

My groupmembers and I do not claim authorship of the underlying solver logic All such components remain the intellectual work of the original author.

Our contribution consists of an AI Strategy Layer built on top of the existing solver, including:  
* A modular Strategy interface
* BaselineFrequencyStrategy wrapper
* EntropyHeuristicStrategy (informed search)
* BayesianBeliefStrategy (belief-state + Bayes updates)
* AStarEvaluationStrategy (A*-style evaluation)
* Experiment runner with our own automated analysis (TXT/CSV/PNG outputs)
* Our own Interactive tutor CLI using pluggable strategies

This extension is intended for academic use as part of a university AI course project.

## Additonal References-    
* Russell & Norvig. Artificial Intelligence: A Modern Approach (4th ed.)  
* Panangadan, A. CPSC 481 AI Lecture Slides (2025)  

