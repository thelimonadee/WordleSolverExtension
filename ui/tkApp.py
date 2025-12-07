import tkinter as tk
from .uiController import UiController
from .wordleView import WordleView

def runApp():
    root = tk.Tk()
    root.title("Wordle AI Assistant")

    controller = UiController()
    view = WordleView(root, controller)
    controller.attachView(view)

    root.mainloop()
