# =========================================================
# --- cli_cliUtils.py ---
# =========================================================
import os
import time

# =========================================================

class ExitGame(Exception):
    """
    Custom exception to indicate that the player wants to quit the game.
    Raised by `safe_input` when the user types 'q', 'quit', or presses Ctrl+C.
    """
    pass


def safe_input(prompt: str) -> str:
    """
    Prompt the user for input safely, handling keyboard interrupts
    and quit commands.

    Args:
        prompt (str): The input prompt to display.

    Raises:
        ExitGame: If the user presses Ctrl+C or enters 'q'/'quit'.

    Returns:
        str: The sanitized user input (stripped of leading/trailing whitespace).
    """
    try:
        inp: str = input(prompt).strip()
    except KeyboardInterrupt:
        raise ExitGame()
    if inp.lower() in ("q", "quit"):
        raise ExitGame()
    return inp


def interruptible_sleep(seconds: float) -> None:
    """
    Sleep for a given number of seconds in small intervals,
    allowing interruptions or responsive UI updates.

    Args:
        seconds (float): Total duration to sleep in seconds.
    """
    start: float = time.time()
    while time.time() - start < seconds:
        time.sleep(0.05)


def clear() -> None:
    """
    Clear the terminal screen.
    Uses 'cls' on Windows and 'clear' on Unix-based systems.
    """
    os.system('cls' if os.name == 'nt' else 'clear')

