# =========================================================
# --- controller.py ---
# =========================================================

import os
import pty
import fcntl
import sys
import select
import subprocess
import time
import json
import re
import signal
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List

from cli.cliUtils import clear

from .parser import OutputParser
from .bot import GnuBGBot

# =========================================================

def strip_ansi(s: str) -> str:
    """
    Remove ANSI escape sequences from a string.

    Args:
        s: Input string possibly containing ANSI codes.

    Returns:
        String with ANSI codes removed.
    """
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    return ansi_escape.sub("", s)


class PromptDetector:
    """Detects GNUBG prompts in the output buffer."""

    def __init__(self, prompts: Optional[List[str]] = None) -> None:
        """
        Args:
            prompts: Optional list of prompt strings to detect.
        """
        self.prompts: List[str] = prompts or ["(Keine Partie)", "(sebastian)", "Are you sure you want to discard the current match?"]
        self.buffer: str = ""
    
    def reset(self) -> None:
        """Reset the buffer."""
        self.buffer = ""

    def feed(self, data: str) -> None:
        """Feed new data into the buffer after stripping ANSI codes."""
        data = strip_ansi(data)
        self.buffer += data

    def ready(self) -> bool:
        """
        Check if a prompt is present in the buffer.

        Returns:
            True if any prompt is found, False otherwise.
        """
        return any(p in self.buffer for p in self.prompts)

    def get_buffer(self) -> str:
        """
        Return buffer content up to and including the next prompt.

        Returns:
            Extracted buffer up to next prompt.
        """
        for p in self.prompts:
            if p in self.buffer:
                idx = self.buffer.index(p) + len(p)
                buf = self.buffer[:idx]
                self.buffer = self.buffer[idx:]
                return buf
        buf = self.buffer
        self.buffer = ""
        return buf


class GnuBGController:
    """Controller for GNUBG, supports interactive or bot-driven play."""

    def __init__(self, bot: Optional[GnuBGBot] = None, debug: bool = True, log_file: Optional[str] = None, prompts: Optional[List[str]] = None) -> None:
        """
        Initialize the controller.

        Args:
            bot: Optional GnuBGBot instance for automated moves.
            debug: Enable debug logging.
            log_file: Optional log file path.
            prompts: Optional list of prompt strings to detect.
        """
        self.bot: Optional[GnuBGBot] = bot
        self.debug: bool = debug
        self.log_file: Optional[str] = log_file
        self.log_entry_counter: int = 1

        self.proc: Optional[subprocess.Popen] = None
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self._gnubg_pid: Optional[int] = None

        self.last_command: Optional[str] = None
        self.prompt_detector: PromptDetector = PromptDetector(prompts)
        self.parser: OutputParser = OutputParser()

    # --------------------------------------------------
    # Lifecycle
    # --------------------------------------------------
    def start(self) -> None:
        """Start the GNUBG subprocess in a pseudo-terminal."""
        self.master_fd, self.slave_fd = pty.openpty()
        self.proc = subprocess.Popen(
            ["gnubg", "-t"],
            stdin=self.slave_fd,
            stdout=self.slave_fd,
            stderr=self.slave_fd,
        )
        self._gnubg_pid = self.proc.pid

        # Set master_fd non-blocking
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def stop(self) -> None:
        """Stop the GNUBG subprocess and close file descriptors."""
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

        if self.master_fd is not None:
            os.close(self.master_fd)
            self.master_fd = None

        if self.slave_fd is not None:
            os.close(self.slave_fd)
            self.slave_fd = None

    # --------------------------------------------------
    # IO helpers
    # --------------------------------------------------
    def send(self, cmd: Optional[str]) -> None:
        """
        Send a command to GNUBG.

        Args:
            cmd: Command string. Can be None.
        """
        if cmd == 'y':
            os.write(self.master_fd, b"y\n")
            time.sleep(0.05)
            os.write(self.master_fd, b"y\n")
                
        if not cmd:
            return
        os.write(self.master_fd, (cmd + "\n").encode())
        self.last_command = cmd

    def log_gnubg_entry(self, data: str, cmd: Optional[str] = None) -> None:
        """
        Log GNUBG output, command, and parsed data.

        Args:
            data: Raw GNUBG output.
            cmd: Command sent.
        """
        if not self.log_file:
            return

        parsed = self.parser.parse(data)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"ENTRY {self.log_entry_counter} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("INPUT:\n")
            f.write(str(cmd) if cmd else "<no input>")
            f.write("\n\nOUTPUT:\n")
            f.write(data)
            if not data.endswith("\n"):
                f.write("\n")
            f.write("\nPARSED_DATA:\n")
            f.write(json.dumps(parsed, indent=2, ensure_ascii=False))
            f.write("\n")

        self.log_entry_counter += 1

    def _filter_echo(self, data: str, last_command: Optional[str] = None) -> str:
        """Remove echoed command from the output if present."""
        if not last_command:
            return data
        lines = data.splitlines(keepends=True)
        if lines and lines[0].strip() == last_command.strip():
            lines = lines[1:]
        return "".join(lines)

    def _read_all(self, limit: int = 262144) -> str:
        """
        Read all available data from master_fd up to a byte limit.

        Args:
            limit: Maximum number of bytes to read.

        Returns:
            Cleaned string with ANSI codes removed.
        """
        chunks: List[bytes] = []
        size = 0
        while size < limit:
            try:
                data = os.read(self.master_fd, 8192)
                if not data:
                    break
                chunks.append(data)
                size += len(data)
            except BlockingIOError:
                break
        raw = b"".join(chunks).decode(errors="ignore")
        clean = strip_ansi(raw)
        return clean

    def _read_until_prompt(self) -> str:
        """
        Read data until a prompt is detected.

        Returns:
            Buffer containing text up to the next prompt.
        """
        while not self.prompt_detector.ready():
            try:
                data = os.read(self.master_fd, 8192)
                if not data:
                    break
                text = data.decode(errors="ignore")
                self.prompt_detector.feed(text)
            except BlockingIOError:
                time.sleep(0.01)
        buf = self.prompt_detector.get_buffer()
        self.prompt_detector.reset()
        return buf

    def _handle_output(self, data: str) -> None:
        """Process GNUBG output: filter echo, print, log, and reset last_command."""
        data = self._filter_echo(data, self.last_command)
        print(data)
        if self.debug and self.log_file:
            self.log_gnubg_entry(data, self.last_command)
        self.last_command = None

    # --------------------------------------------------
    # Run modes
    # --------------------------------------------------
    def run_interactive(self) -> None:
        """Run GNUBG interactively with user input."""
        try:
            while self.proc.poll() is None:
                data = self._read_all()
                if data:
                    self._handle_output(data)
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready:
                    cmd = sys.stdin.readline().rstrip("\n")
                    self.send(cmd)
        except KeyboardInterrupt:
            print("\n[CTRL-C] terminate gnubg…")
        finally:
            self.stop()

    def run_bot(self) -> None:
        """Run GNUBG controlled by a bot."""
        if not self.bot:
            raise RuntimeError("run_bot() requires a bot instance")
        try:
            while self.proc.poll() is None:
                data = self._read_until_prompt()
                if not data:
                    continue
                self._handle_output(data)
                cmd = self.bot.select_command(data)
                if cmd:
                    self.send(cmd)
        except KeyboardInterrupt:
            print("\n[CTRL-C] terminate gnubg…")
        finally:
            self.stop()

    def run(self) -> None:
        """Run GNUBG in bot mode or interactive mode depending on initialization."""
        if self.bot:
            self.run_bot()
        else:
            self.run_interactive()


def choose_mode() -> str:
    """
    Ask user for start mode.

    Returns:
        'bot' or 'interactive' depending on user input.
    """
    welcome = "\nWelcome to GnuBG 🎲🎲 Controller 🤖 !"
    clear()
    print(welcome)
    print("="*len(welcome))
    print("\n")

    while True:
        print("Select start mode:\n")
        print("1) Bot mode\n2) Interactive mode\n")
        choice = input("Enter 1 or 2: ").strip()
        if choice == "1":
            clear()
            return "bot"
        elif choice == "2":
            clear()
            return "interactive"
        else:
            print("Invalid choice. Please enter 1 or 2.\n")


if __name__ == "__main__":
    """
    Main entry point for running the GNUBG Controller.

    - Initializes log directories and files.
    - Instantiates bot if needed.
    - Lets user choose mode (bot or interactive).
    - Starts GNUBG subprocess and runs the chosen mode.
    """
    SCRIPT_DIR: str = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR: str = os.path.join(SCRIPT_DIR, "logs")  
    os.makedirs(LOG_DIR, exist_ok=True)        

    LOG_FILE: str = os.path.join(LOG_DIR, "gnubg_game.log")
    BOT_LOG_FILE: str = os.path.join(LOG_DIR, "bot_engine.log") 

    # Instantiate bot with its own log
    my_bot: GnuBGBot = GnuBGBot(log_file=BOT_LOG_FILE)

    # Clear log files at start
    open(LOG_FILE, "w").close()  
    open(BOT_LOG_FILE, "w").close()

    # Mode selection: 'bot' or 'interactive'
    try:
        mode: str = choose_mode()
    
        # Initialize controller with or without bot
        controller: GnuBGController
        if mode == "bot":
            controller = GnuBGController(bot=my_bot, log_file=LOG_FILE)
        else:
            controller = GnuBGController(bot=None, log_file=LOG_FILE)

        # Start GNUBG process and run chosen mode
        controller.start()
        controller.run()
    except KeyboardInterrupt:
        print("\n[CTRL-C] terminate …")
