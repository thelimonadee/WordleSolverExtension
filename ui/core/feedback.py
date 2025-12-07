from enum import Enum, auto

class FeedbackColor(Enum):
    GREY = auto()
    YELLOW = auto()
    GREEN = auto()


def computeFeedback(secret: str, guess: str):
    """
    Compute Wordle-style feedback for a given secret and guess.
    Returns a list[FeedbackColor] of length 5.
    """
    secret = secret.lower()
    guess = guess.lower()
    if len(secret) != 5 or len(guess) != 5:
        raise ValueError("secret and guess must both be length 5")

    feedback = [FeedbackColor.GREY] * 5
    secretUsed = [False] * 5  # which secret positions are already matched

    # First pass: mark greens
    for i in range(5):
        if guess[i] == secret[i]:
            feedback[i] = FeedbackColor.GREEN
            secretUsed[i] = True

    # Second pass: mark yellows
    for i in range(5):
        if feedback[i] == FeedbackColor.GREEN:
            continue
        letter = guess[i]
        for j in range(5):
            if not secretUsed[j] and secret[j] == letter:
                feedback[i] = FeedbackColor.YELLOW
                secretUsed[j] = True
                break

    return feedback


def patternToColors(pattern: str):
    """
    Convert a pattern like 'g.y..' into a list[FeedbackColor].
    g = green, y = yellow, . or x = grey
    """
    mapping = {
        'g': FeedbackColor.GREEN,
        'y': FeedbackColor.YELLOW,
        '.': FeedbackColor.GREY,
        'x': FeedbackColor.GREY,
    }
    pattern = pattern.strip().lower()
    if len(pattern) != 5:
        raise ValueError("Pattern must be length 5")
    return [mapping[ch] for ch in pattern]
