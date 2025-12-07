from .constraints import filterCandidates

class GameState:
    def __init__(self, initialCandidates):
        self.candidateSet = list(initialCandidates)
        self.history = []  # list of (guess, feedbackColors)

    def applyFeedback(self, guess, feedbackColors):
        self.history.append((guess, feedbackColors))
        self.candidateSet = filterCandidates(self.candidateSet, guess, feedbackColors)

    def remainingCandidates(self):
        return len(self.candidateSet)
