from pathlib import Path

# Project root = two directories up from this file
ROOT_DIR = Path(__file__).resolve().parents[2]

def loadWordList(filePath: str | Path = None, listType="answers"):
    """
    added to load NYT word lists from the project root

    """

    # No path provided, choose based on listType
    if filePath is None:
        if listType == "answers":
            filePath = ROOT_DIR / "nyt-answers.txt"
        elif listType == "guesses":
            filePath = ROOT_DIR / "nyt-guesses.txt"
        else:
            raise ValueError(f"Unknown listType: {listType}")
    else:
        filePath = Path(filePath)

    # Load
    with open(filePath, "r") as file:
        words = [
            line.strip().lower()
            for line in file
            if len(line.strip()) == 5
        ]

    return words
