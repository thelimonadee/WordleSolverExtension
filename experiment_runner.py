#Our original file
"""
experiment_runner.py

Revamped CLI for running largescale Wordle sims with different strategies-
Draws from and inspired by given repo, updated with our strategies we thought of with the goal of our project:
Hueristics and Data driven AI for efficiently solving the game Wordle

- Uses WordleAgent (wraps the original Solver/Dictionary engine).
- Allows user to choose a strategy (BaselineFrequencyStrategy for now).
- Loops over all answer words and records performance, outputs png and txt (like original) + a csv we can use for reporting/analysis
- Outputs:
    - Console summary
    - TxT report (human-readable summary + distribution)
    - PNG bar chart (guess count distribution)
    - CSV with perword details (for notebooks/Colab/jupytr)

This is the main beginning point for the "automatic agent", our AI system part of our project
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
from datetime import datetime
from typing import Dict, List, Type

import matplotlib.pyplot as plt

from wordle_solver import Dictionary
from wordle_agent import WordleAgent, SimulationResult
from strategies import (
    Strategy,
    BaselineFrequencyStrategy,
    EntropyHeuristicStrategy,
    BayesianBeliefStrategy,
    AStarEvaluationStrategy,
)


# Map from CLI strategy names to strategy classes
# Somewhat follows methods of given repo but we further extended
# We stick with the word 'SLATE', just like the given repo as it is 'statistically' is a good candidate, 
# but this can be swapped with a diff starting word. I personally use (and tested)'ROAST' -> 'PINED' or 'PLANE' or'P----' (depending on feedback)
# inspired by Wheel of Fortunes 'RSTLNE' + mixture vowels
STRATEGY_REGISTRY: Dict[str, Type[Strategy]] = {
    "baseline": BaselineFrequencyStrategy,
    "entropy": EntropyHeuristicStrategy,
    "bayes": BayesianBeliefStrategy,
    "astar": AStarEvaluationStrategy,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Runs Wordle simulations with different AI strategies."
    )
    parser.add_argument(
        "-s",
        "--strategy",
        choices=STRATEGY_REGISTRY.keys(),
        default="baseline",
        help="Which strategy to use (default: baseline).",
    )
    parser.add_argument(
        "-w",
        "--starting-word",
        default="SLATE",
        help="Starting word to use for all games (default: SLATE).",
    )
    parser.add_argument(
        "-n",
        "--num-games",
        type=int,
        default=None,
        help="Number of games to run (default: all answers).",
    )
    parser.add_argument(
        "--max-guesses",
        type=int,
        default=6,
        help="Maximum guesses allowed per game (default: 6).",
    )
    parser.add_argument(
        "--no-intersecting",
        action="store_true",
        help="Disable original intersecting guess behavior.",
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Also write a CSV of per-game results.",
    )
    parser.add_argument(
        "--prefix",
        default="results",
        help="Prefix for output files (default: results).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each game result (like the original runner).",
    )
    return parser.parse_args()


def run_experiments(
    strategy_name: str,
    starting_word: str,
    num_games: int | None,
    max_guesses: int,
    use_intersecting: bool,
    verbose: bool = False,
) -> Dict:
    """
    Run simulations over the answer list using a chosen strategy.

    Returns a dict with:
        - 'results': List[SimulationResult]
        - 'distribution': {guess_count_or_fail: count}
        - 'avg_guesses': float (over solved games only)
        - 'solved': int
        - 'total': int
    """
    strategy_cls = STRATEGY_REGISTRY[strategy_name]

    # Uses the original Dictionary to get the official answer list.
    dictionary = Dictionary(use_intersecting)
    all_answers: List[str] = list(dictionary.answers)

    if num_games is not None:
        all_answers = all_answers[:num_games]

    total_games = len(all_answers)
    results: List[SimulationResult] = []

    # Distribution: how many words solved in k guesses (1-max_guesses) + 'fail'
    distribution: Dict[str, int] = {str(i): 0 for i in range(1, max_guesses + 1)}
    distribution["fail"] = 0

    total_guesses_for_avg = 0
    solved_count = 0

    print(
        f"Running {total_games} games with strategy '{strategy_name}' "
        f"and starting word '{starting_word.upper()}'..."
    )

    for idx, target in enumerate(all_answers, start=1):
        agent = WordleAgent(
            target_word=target,
            strategy_cls=strategy_cls,
            starting_word=starting_word,
            use_intersecting_guesses=use_intersecting,
        )
        result = agent.run_simulation(max_guesses=max_guesses)
        results.append(result)

        guess_count = len(result.guesses)

        if result.solved:
            solved_count += 1
            total_guesses_for_avg += guess_count
            key = str(guess_count)
        else:
            key = "fail"

        if key not in distribution:
            distribution[key] = 0
        distribution[key] += 1

        if verbose:
            status = "OK" if result.solved else "FAIL"
            guesses_str = ", ".join(result.guesses)
            print(
                f"[{idx:4d}/{total_games}] {status} "
                f"{result.target} in {guess_count} guesses: {guesses_str}"
            )

    avg_guesses = (
        total_guesses_for_avg / solved_count if solved_count > 0 else float("nan")
    )

    return {
        "results": results,
        "distribution": distribution,
        "avg_guesses": avg_guesses,
        "solved": solved_count,
        "total": total_games,
    }


def write_txt_report(
    prefix: str,
    strategy_name: str,
    starting_word: str,
    stats: Dict,
) -> str:
    """
    Writes a human-readable TXT summary of experiment results.
    Out-Returns the filename.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prefix}_{strategy_name}_{starting_word.upper()}_{timestamp}.txt"

    distribution = stats["distribution"]
    avg_guesses = stats["avg_guesses"]
    solved = stats["solved"]
    total = stats["total"]

    with open(filename, "w", encoding="utf-8") as f:
        f.write("Wordle Strategy Report\n")
        f.write("---------------------------------\n\n")
        f.write(f"Strategy:       {strategy_name}\n")
        f.write(f"Starting word:  {starting_word.upper()}\n")
        f.write(f"Total games:    {total}\n")
        f.write(f"Solved:         {solved}\n")
        f.write(f"Failures:       {distribution.get('fail', 0)}\n")
        f.write(f"Average guesses (solved only): {avg_guesses:.4f}\n\n")

        f.write("Guess count distribution:\n")
        for k in sorted(distribution.keys(), key=lambda x: (x == "fail", int(x) if x.isdigit() else 0)):
            f.write(f"  {k}: {distribution[k]}\n")

        f.write("\nNote:\n")
        f.write(
            "- This run uses the WordleAgent and Strategy abstraction on top of the original solver.\n"
        )
        f.write(
            "- BaselineFrequencyStrategy reproduces the original, given repo's letter frequency and intersecting logic.\n"
        )
        f.write(
            "- Other strategies (entropy, Bayesian, A* evaluation) can be plugged in and compared using this same pipeline\n"
        )

    return filename


def write_csv_results(
    prefix: str,
    strategy_name: str,
    starting_word: str,
    stats: Dict,
) -> str:
    """
    Writes pergame results to a CSV for later analysis in a notebook.
    Out-Returns the filename.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prefix}_{strategy_name}_{starting_word.upper()}_{timestamp}.csv"

    results: List[SimulationResult] = stats["results"]

    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["target", "guess_count", "solved", "guesses"])
        for r in results:
            writer.writerow(
                [
                    r.target,
                    len(r.guesses),
                    int(r.solved),
                    ";".join(r.guesses),
                ]
            )

    return filename


def write_png_histogram(
    prefix: str,
    strategy_name: str,
    starting_word: str,
    stats: Dict,
) -> str:
    """
    Writes a bar chart (PNG) of the guess-count distribution. Like the given repo, for just a quick easy to see comparison
    Out-Returns the filename.
    """
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    filename = f"{prefix}_{strategy_name}_{starting_word.upper()}_{timestamp}.png"

    distribution = stats["distribution"]

    # Separate successes (numeric keys) from failures
    keys_numeric = sorted(
        [k for k in distribution.keys() if k.isdigit()], key=lambda x: int(x)
    )
    counts_numeric = [distribution[k] for k in keys_numeric]

    # Preps labels and counts (including 'fail' if present)
    labels = keys_numeric[:]
    counts = counts_numeric[:]

    if "fail" in distribution:
        labels.append("fail")
        counts.append(distribution["fail"])

    fig, ax = plt.subplots(1, 1)
    ax.bar(range(len(labels)), counts, tick_label=labels)
    ax.set_xlabel("Guesses per answer (or 'fail')")
    ax.set_ylabel("Number of words")
    ax.set_title(
        f"Strategy: {strategy_name}, Start: {starting_word.upper()} "
        f"(avg={stats['avg_guesses']:.4f}, solved={stats['solved']}/{stats['total']})"
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, count in enumerate(counts):
        ax.text(i, count + 0.5, str(count), ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(filename)
    plt.close(fig)

    return filename


def main() -> None:
    args = parse_args()

    strategy_name = args.strategy
    starting_word = args.starting_word
    max_guesses = args.max_guesses
    use_intersecting = not args.no_intersecting

    stats = run_experiments(
        strategy_name=strategy_name,
        starting_word=starting_word,
        num_games=args.num_games,
        max_guesses=max_guesses,
        use_intersecting=use_intersecting,
        verbose=args.verbose,
    )

    txt_file = write_txt_report(
        prefix=args.prefix,
        strategy_name=strategy_name,
        starting_word=starting_word,
        stats=stats,
    )
    print(f"Wrote TXT report: {txt_file}")

    png_file = write_png_histogram(
        prefix=args.prefix,
        strategy_name=strategy_name,
        starting_word=starting_word,
        stats=stats,
    )
    print(f"Wrote PNG histogram: {png_file}")

    if args.csv:
        csv_file = write_csv_results(
            prefix=args.prefix,
            strategy_name=strategy_name,
            starting_word=starting_word,
            stats=stats,
        )
        print(f"Wrote CSV results: {csv_file}")


if __name__ == "__main__":
    main()
