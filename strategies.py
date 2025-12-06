# original file of our own - main engine
# strategies.py
"""
Strategy layer for Wordle AI.

This file defines:
  - Strategy: abstract interface for "how to pick the next guess"
  - BaselineFrequencyStrategy: wraps the original solver's frequency/intersecting behavior as a Strategy (Baseline 0).
  - EntropyHeuristicStrategy: 
        explicit informed search heuristic that chooses guesses by maximizing expected information 
        gain over the current belief state.
  - BayesianBeliefStrategy:      
        Implements “reasoning under uncertainty” by maintaining an explicit
        probability distribution P(w) over candidate answers and updating it
        after each feedback, selecting the MAP (maximum a posteriori) guess.
  - AStarEvaluationStrategy
        Applies the A* evaluation principle f(n) = g(n) + h(n) to the belief space,
        where g ~ guesses taken so far and h ` expected difficulty of remaining
        candidates based on partition sizes.

Tying back to what we've learned in class:
    - State-space / belief state:
        State = (candidates, feedback, guesses_so_far) where 'candidates' is the current set of possible hidden words.
    - Actions:
        Choose a guess word.
    - EntropyHeuristicStrategy:
        Implements an informed search heuristic by selecting the action that
        maximizes expected reduction in uncertainty (entropy) over the belief state.
    - BayesianBeliefStrategy:
        Probabilistic reasoning: updating beliefs via evidence, analogously to Bayesian Networks.
    - AStarEvaluationStrategy:
        Informed search (A*), combining accumulated cost (g)
        with a heuristic estimate of remaining difficulty (h) to guide action choice.

Architecture/Design
    -Modular strategy architecture to allow the comparison of different AI techniques mentioned above. 
"""

from __future__ import annotations

from typing import Sequence, Protocol, Dict, Tuple, List
import math

from wordle_solver import Dictionary, LetterFeedback


# ------------------------------------------------------------------------------------------------------
# Strategy interface

class Strategy(Protocol):
    """
    General interface for a Wordle decision chooser

    State Space:
      - The state is a belief state: (candidates, feedback, guesses_so_far)
      - Action: choose a guess word.
    """

    def select_guess(
        self,
        candidates: Sequence[str],
        feedback: LetterFeedback,
        guesses_so_far: Sequence[str],
    ) -> str:
        """
        Choose the next guess word, returned in UPPERCASE.

        :param candidates: current remaining candidate answers (belief state)
        :param feedback:   LetterFeedback from all prior guesses
        :param guesses_so_far: list of guesses made so far, in order
        """
        ...


# ---------------------------------------------------------------------------
# Baseline: original repo strategy wrapped as a Strategy
# ---------------------------------------------------------------------------

class BaselineFrequencyStrategy:
    """
    Strategy that delegates directly to the original Dictionary.next_guess() logic, from given repo.

    Reproduces the existing heuristic from the repo:
      - Letter-frequency-based scoring over answers.
      - Intersecting guesses when the candidate set is small

    Hence "Baseline" for comparison to our work to better from it.
    """

    def __init__(self, dictionary: Dictionary) -> None:
        # Keeps a reference to the shared Dictionary instance used by the Puzzle
        self._dictionary = dictionary

    def select_guess(
        self,
        candidates: Sequence[str],
        feedback: LetterFeedback,
        guesses_so_far: Sequence[str],
    ) -> str:
        """
        Chooses the next guess by deferring to Dictionary.next_guess().

        NOTe: Dictionary already maintains its own internal feedback and
        candidate list. 'candidates' is passed in for consistency with the
        Strategy interface but not used here. Our own
        """
        return self._dictionary.next_guess()


# ---------------------------------------------------------------------------
# Helper for Wordle feedback pattern (for entropy-based reasoning)
# ---------------------------------------------------------------------------

def _feedback_pattern(guess: str, answer: str) -> Tuple[int, int, int, int, int]:
    """
    Compute the Wordle feedback pattern for (guess, answer).

    Returns a 5-tuple of ints:
      2 = green  (correct letter, correct position)
      1 = yellow (letter in word, wrong position)
      0 = gray   (letter not in word, or over-used)

    This implements the same feedback as Wordle:
      - First pass: mark greens, track remaining letter counts in the answer.
      - Second pass: for each non-green position, mark yellow if the letter is
        still available in the remaining counts, otherwise gray.

    This lets us:
      - Group candidate answers by pattern
      - Compute how a given guess partitions the belief state
      - Derive entropy / expected remaining uncertainty, as in informed search.
    """
    guess = guess.upper()
    answer = answer.upper()
    assert len(guess) == len(answer) == 5

    # First pass- mark greens, count remaining letters in answer
    pattern = [0] * 5
    remaining: Dict[str, int] = {}

    for i in range(5):
        g = guess[i]
        a = answer[i]
        if g == a:
            pattern[i] = 2  # green
        else:
            remaining[a] = remaining.get(a, 0) + 1

    # Second pass- yellows / grays for non-greens
    for i in range(5):
        if pattern[i] != 0:
            continue  # already green
        g = guess[i]
        if remaining.get(g, 0) > 0:
            pattern[i] = 1  # yellow
            remaining[g] -= 1
        else:
            pattern[i] = 0  # gray

    return tuple(pattern)  # hashable key for dicts


def _entropy_from_partition(counts: Sequence[int]) -> float:
    """
    Compute entropy, in bits, of a partition given cell sizes.

    counts: sizes of groups (ex: how many candidates share each feedback pattern).

    H = - sum_i p_i log2 p_i, where p_i = count_i / N.

    Entropy in AI:
      - The higher the entropy, the more evenly the belief state is spread.
      - A guess with high expected entropy 'reduction' is a strong/ informed heuristic.
    """
    total = sum(counts)
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts:
        if c == 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


# ---------------------------------------------------------------------------
# EntropyHeuristicStrategy: explicit informed-search policy
# ---------------------------------------------------------------------------

class EntropyHeuristicStrategy:
    """
    Explicit informed search strategy using an entropy heuristic.

    From the state-space / belief-state perspective:
      - State: set of remaining candidate answers (C), plus history (F, guesses).
      - Action: choose a guess word g.

    For each potential guess g, consider, for every candidate answer a in C:
      - The feedback pattern P = pattern(g, a)
      - This induces a partition of C into groups C_P by pattern.

    Then compute the entropy over these pattern groups:
      H(g) = - sum_P (|C_P| / |C|) * log2(|C_P| / |C|)

    Intuitivly:
      - A good guess should split the belief state into balanced, smaller pieces.
      - Maximizing H(g) ~ maximizing expected information gain (reducing uncertainty).

    Ties back to the "Informed Search" lecture where we are designing an
    explicit heuristic over the belief state, rather than relying on implicit
    heuristics like letter frequency alone.
    """

    def __init__(self, dictionary: Dictionary) -> None:

        self._dictionary = dictionary

    def _candidate_guess_pool(self, candidates: Sequence[str]) -> List[str]:
        """
        Decides which words to consider as potential guesses.

        For simplicity, we start by using the current candidate answers themselves as the action set.

          - We are searching in the belief-state space (remaining answers).
          - We are not using non-answer words as probes. Potential implementation later to other .txt 'guesses' maybe

        """
        # In future:
        #   if len(candidates) < threshold:
        #       return list(set(candidates) | set(self._dictionary.guesses))
        # For now, this is simple:
        return list(candidates)

    def select_guess(
        self,
        candidates: Sequence[str],
        feedback: LetterFeedback,
        guesses_so_far: Sequence[str],
    ) -> str:
        """
        Choose next guess by maximizing entropy over the partition induced by that guess on the current belief state.
        Some edge case:
          - If no candidates, fall back to Dictionary.next_guess().
          - If exactly one candidate, just returns it.
        """
        # empty / singleton candidate sets.
        if not candidates:
            # Fall backs(expected rarely)
            return self._dictionary.next_guess()

        if len(candidates) == 1:
            return candidates[0]

        # Builds the pool of words to evaluate as guesses.
        pool = self._candidate_guess_pool(candidates)

        best_guess = pool[0]
        best_entropy = -1.0

        # Evaluate each potential guess
        for guess in pool:
            # Partitions candidates by feedback pattern
            partitions: Dict[Tuple[int, int, int, int, int], int] = {}
            for ans in candidates:
                pat = _feedback_pattern(guess, ans)
                partitions[pat] = partitions.get(pat, 0) + 1

            # Computes entropy over these groups.
            h = _entropy_from_partition(partitions.values())

            # We pick the guess that maximizes entropy-
            # Tie-breaking = prefer guesses that are themselves in the candidate set and have not been played yet (simple, reasonable bias)
            if h > best_entropy:
                best_entropy = h
                best_guess = guess
            elif math.isclose(h, best_entropy, rel_tol=1e-9):
                # Optional simple tie break: prefer unseen candidates
                if guess in candidates and guess not in guesses_so_far:
                    # Only override if the current best_guess is worse
                    if best_guess not in candidates or best_guess in guesses_so_far:
                        best_guess = guess

        return best_guess.upper()


# ---------------------------------------------------------------------------
# BayesianBeliefStrategy: explicit probabilistic reasoning
# ---------------------------------------------------------------------------
"""
BayesianBeliefStrategy implements the "reasoning under uncertainty", following lecture kind of by 
maintaining an explicit belief distribution over the hidden answer words.

    - Each candidate word is treated as a possible "world" (complete, hypothetical state of underlying reality that could be true)
    - Feedback from a guess acts as evidence
    - We update P(w) using Bayes':
        P(w | F) (*proportional to symbol here*) P(F | w) * P(w)
        where P(F | w) is 1 if w would generate feedback F, else 0.
    - This turns Wordle into a Bayesian belief update problem, kind of like the slippery-road example in 
      Bayesian Networks slides.

Strategy (version1?):
    - Maintain P(w) as a uniform distribution over the current belief state
    - Eliminate inconsistent 'worlds' (P(w)=0) based on guess/feedback pattern
    - Normalize P(w)
    - Choose the guess with highest posterior probability (MAP estimate)

Look into slides for:
    - Belief-state maintenance
    - Bayesian update given evidence
    - Probabilistic inference
"""
class BayesianBeliefStrategy:
    """
    Bayesian belief-state strategy (v1):
        - Maintains a probability distribution over candidate words
        - Updates probabilities using Bayes' rule after each guess
        - Selects the guess with maximum posterior probability (MAP)

 Lectures: "Bayesian Networks" and "Reasoning Under Uncertainty"
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self._dictionary = dictionary
        self._belief: Dict[str, float] = {}  # P(w) over candidate answers

    def _recompute_uniform_prior(self, candidates: Sequence[str]) -> None:
        """
        If our candidate set shrinks or is recomputed, ensure belief has entries
        matching this set. Any removed words disappear from belief.
        """
        n = len(candidates)
        if n == 0:
            self._belief = {}
            return

        #Uniform distribution over candidates
        uniform_p = 1.0 / n
        self._belief = {w: uniform_p for w in candidates}

    def _normalize(self) -> None:
        """Normalizes belief distribution so sum P(w) = 1."""
        total = sum(self._belief.values())
        if total == 0:
            # degenerate case -> redistribute uniformly
            n = len(self._belief)
            if n == 0:
                return
            uniform = 1.0 / n
            for w in self._belief:
                self._belief[w] = uniform
            return

        for w in self._belief:
            self._belief[w] /= total

    def _update_belief_after_guess(
        self,
        guess: str,
        feedback: LetterFeedback,
        candidates: Sequence[str],
    ) -> None:
        """
        Applying Bayes' rule:

            P(w | F) **(proportional to)** P(F | w) * P(w)

        Wordle's "likelihood" P(F | w) is deterministic:
            - 1 if the answer w would produce exactly feedback F for guess
            - 0 otherwise.
        """
        # Convert feedback (in LetterFeedback form) into a canonical pattern via underlying solver/dictionary
        #
        # In this project, the Wordle engine (given repo) already applies a deterministic pruning step: any word inconsistent with the feedback
        # F is removed from the candidate set. In Bayesian, this is like using a likelihood:
        #
        #       P(F | w) = 1  if w is consistent with feedback F
        #                  0  otherwise
        #
        # After pruning, the candidates list consists only of "possible worlds" with P(F | w) = 1 under that deterministic model.
        #
        # In BayesianBeliefStrategy (our version, v1), we treat all surviving candidates as equally likely and assign a uniform 
        # posterior over them:
        #
        #       P(w | F) **(proportional to)** P(F | w) * P(w)
        #                 = 1 * P(w)   for surviving words
        #
        # and we choose P(w) to be uniform over the current belief state.
        #
        # This is our simple starting point, but makes the belief distribution explicit and sets up the architecture for better priors 
        # or softer likelihoods in future versions (frequency-based P(w), noisy feedback models, etc)
        #
        # Essentially: our v1 recomputes a uniform distribution over the pruned candidate set

        self._recompute_uniform_prior(candidates)
        self._normalize()

    def select_guess(
        self,
        candidates: Sequence[str],
        feedback: LetterFeedback,
        guesses_so_far: Sequence[str],
    ) -> str:
        """
        Main decision rule:
            - Update P(w) over the remaining candidates.
            - Choose w with maximum posterior probability (MAP word).

        Since v1 uses a uniform prior after pruning:
            MAP returns any remaining candidate with maximum probability
        """
        if not candidates:
            return self._dictionary.next_guess()  # fallsback

        # First turn OR any time candidate list resets
        if not self._belief or len(self._belief) != len(candidates):
            self._recompute_uniform_prior(candidates)

        # Update belief based on latest evidence (pruned candidate set)
        if guesses_so_far:
            last_guess = guesses_so_far[-1]
            self._update_belief_after_guess(last_guess, feedback, candidates)

        # Normalize posterior
        self._normalize()

        # MAP estimate = word with highest probability
        # self._belief.items() -> (word, probability)
        best_word = max(self._belief.items(), key=lambda item: item[1])[0]

        return best_word.upper()


# ---------------------------------------------------------------------------
# AStarEvaluationStrategy: Informed Search / A* applied to Wordle
# ---------------------------------------------------------------------------
"""
Lecuture topic look into: "State Space Representation" and "Informed Search (A*)", applied to Wordle

SEARCH:
Each moment in Wordle can be modeled as a search state:
    - State   = current belief state (set of remaining candidate words)
    - Action  = choosing a guess word
    - Result  = the next belief state after applying Wordle feedback
    - Goal    = belief state size = 1 (or guess == answer)

From the 'environment’s' perspective, the puzzle is PARTIALLY OBSERVABLE, but the agent maintains a BELIEF STATE (candidate set), 
making actions grounded in the "search over beliefs" idea from that lecture

A* APPLIED:
A* uses the evaluation function:
        f(n) = g(n) + h(n)
Here:
    g(n) = cost so far  ~ number of guesses already made
    h(n) = estimated cost-to-go  ~ how hard the remaining uncertainty is

Wordle adaptation:
    For each possible guess g:
        - Partition the candidate set C by the feedback pattern produced
          against each candidate answer.
        - Let C_p be the size of each partition.
        - Compute a heuristic:
                h(g) ~ E[ log2 |C_p| ]
          -> approximates the future difficulty of the subproblem.
          (Similar intuitively to entropy, but framed as A*)

    Then evaluate:
            f(g) = g_cost + 1 + h(g)

    The guess with minimal f(g) is selected.

HOW THIS IS A*ish:
We dont construct a full search tree (too expensive), but we apply the A* principle of combining:
    - actual cost so far (g)
    - estimated future cost (h)
to choose actions that minimize the total expected effort.

Involves: Heuristic evaluation, some state-space formulation, and A* search principles applied to belief states

"""


class AStarEvaluationStrategy:
    """
    A* evaluation strategy on the belief state.

        - Each "state" as a belief state: the current candidate set C plus the history of guesses
        - g(n)  = cost so far  ~ number of guesses already used
        - h(n)  = heuristic cost-to-go  ~ expected difficulty of the remaining search, approximated by how lopsided the partitions are.
        - f(n)  = g(n) + h(n).

    Implementation:
        - For each potential guess g:
            - Partition the candidate set C by feedback pattern P = pattern(g, a).
            - Let |C_P| be the size of each partition.
            - Define h(g) ` E[log2 |C_P|] over patterns (smaller is better)
            ` Define f(g) = g_cost + 1 (this move) + h(g).
        - We select the guess with minimal f(g).

    Keeps the same state-space / belief-state view as EntropyHeuristicStrategy but uses an A*-like cost function instead 
    """

    def __init__(self, dictionary: Dictionary) -> None:
        self._dictionary = dictionary

    def _candidate_guess_pool(self, candidates: Sequence[str]) -> List[str]:
        """
        Decides which words to consider as potential guesses

        Starts by using the current candidate answers themselves as the action set. 
        Keeps computation manageable while demoing A* evaluation idea.
        """
        return list(candidates)

    def select_guess(
        self,
        candidates: Sequence[str],
        feedback: LetterFeedback,
        guesses_so_far: Sequence[str],
    ) -> str:
        """
        Chooses the next guess by minimizing an A*-style score:

            f(g) = g_cost + 1 + E_P[log2 |C_P|]

        where:
            - g_cost = number of guesses used so far
            - C      = current candidate set
            - C_P    = subset of C that would produce pattern P for this guess
            - E_P[ ] is expectation over patterns with probability |C_P| / |C|.
        """
        # Edge cases
        # fallback
        if not candidates:
            return self._dictionary.next_guess() 

        if len(candidates) == 1:
            return candidates[0]

        pool = self._candidate_guess_pool(candidates)
        g_cost = len(guesses_so_far)

        best_guess = pool[0]
        best_f = float("inf")

        N = len(candidates)

        for guess in pool:
            # Partition candidates by feedback pattern for this guess
            partitions: Dict[Tuple[int, int, int, int, int], int] = {}
            for ans in candidates:
                pat = _feedback_pattern(guess, ans)
                partitions[pat] = partitions.get(pat, 0) + 1

            # Approximate "remaining difficulty":
            #   h(g) ~ sum_P (|C_P| / N) * log2(|C_P|)
            # Prefer guesses that, on average, leave us in smaller subproblems (smaller |C_P|).
            expected_log_size = 0.0
            for c in partitions.values():
                if c <= 0:
                    continue
                p = c / N
                expected_log_size += p * math.log2(c)

            f_score = g_cost + 1 + expected_log_size

            # Minimize f(g)
            if f_score < best_f:
                best_f = f_score
                best_guess = guess
            elif math.isclose(f_score, best_f, rel_tol=1e-9):
                # Tie breaker: prefer guesses that are candidates and not yet played
                if guess in candidates and guess not in guesses_so_far:
                    if best_guess not in candidates or best_guess in guesses_so_far:
                        best_guess = guess

        return best_guess.upper()
    
# ---------------------------------------------------------------------------
# Placeholders for future strategies (still deciding on optimization/weight tuning)
# From the results we already have 2 strategies better than the baseline, given repos, approach
# ---------------------------------------------------------------------------

