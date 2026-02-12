import logging
import os
import platform
import shlex
import subprocess
import webbrowser
from pathlib import Path

logger = logging.getLogger(__name__)


DANGEROUS_TOKENS = {";", "&&", "||", "|", "`", "$(", ">", "<"}


def _has_dangerous_token(command: str) -> bool:
    return any(token in command for token in DANGEROUS_TOKENS)


def open_app(app_name: str) -> str:
    app_name = app_name.strip()
    if not app_name:
        return "Application name is required."
    system = platform.system().lower()
    try:
        if system == "darwin":
            subprocess.Popen(["open", "-a", app_name])
        elif system == "windows":
            os.startfile(app_name)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([app_name])
        return f"Opened application: {app_name}"
    except Exception as exc:
        logger.exception("Failed to open app")
        return f"Failed to open application {app_name}: {exc}"


def open_file(path: str) -> str:
    target = Path(path).expanduser().resolve()
    if not target.exists():
        return f"File not found: {target}"
    system = platform.system().lower()
    try:
        if system == "darwin":
            subprocess.Popen(["open", str(target)])
        elif system == "windows":
            os.startfile(str(target))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return f"Opened file: {target}"
    except Exception as exc:
        logger.exception("Failed to open file")
        return f"Failed to open file {target}: {exc}"


def open_web(url: str) -> str:
    clean = url.strip()
    if not clean:
        return "Website URL is required."
    if not clean.startswith(("http://", "https://")):
        clean = f"https://{clean}"
    try:
        webbrowser.open(clean)
        return f"Opened website: {clean}"
    except Exception as exc:
        logger.exception("Failed to open website")
        return f"Failed to open website: {exc}"


def run_shell(command: str, timeout: int = 20) -> str:
    clean = command.strip()
    if not clean:
        return "Command is empty."
    if _has_dangerous_token(clean):
        return "Blocked unsafe shell command."

    try:
        args = shlex.split(clean)
    except ValueError:
        return "Invalid command syntax."

    if not args:
        return "Command is empty."

    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout or completed.stderr).strip()
        return output or "Command finished with no output."
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except FileNotFoundError:
        return f"Command not found: {args[0]}"
    except Exception as exc:
        logger.exception("Command failed")
        return f"Command failed: {exc}"
