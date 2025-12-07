# main.py

from ui.tkApp import runApp
from ui.wordleGameApp import runGame

if __name__ == "__main__":
    # uncomment below for Assistant / tutor mode (GUI wrapped around strategies.py)
    runApp()

    
    # uncomment the next line for autonomous AI agent on to solve any target word :
    # runGame()
