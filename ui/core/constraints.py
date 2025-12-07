from .feedback import computeFeedback

def isWordConsistent(candidate: str, guess: str, observedFeedbackColors):
    """
    A candidate is consistent if, treating it as the secret, it would produce
    exactly the observed feedback for this guess.
    """
    return computeFeedback(candidate, guess) == observedFeedbackColors


def filterCandidates(candidates, guess, observedFeedbackColors):
    """
    Return all candidate words that are consistent with the given guess + feedback.
    """
    return [
        w for w in candidates
        if isWordConsistent(w, guess, observedFeedbackColors)
    ]

