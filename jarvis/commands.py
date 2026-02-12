from dataclasses import dataclass

from jarvis.automation import open_app, open_file, open_web, run_shell
from jarvis.config import settings
from jarvis.pdf_tools import extract_pdf_text
from jarvis.search import web_search


@dataclass
class CommandResult:
    handled: bool
    response: str
    data_for_llm: str = ""


class CommandRouter:
    def handle(self, text: str) -> CommandResult:
        clean = text.strip()
        lower = clean.lower()

        if lower.startswith("open app "):
            app = clean[9:].strip()
            return CommandResult(True, open_app(app))

        if lower.startswith("open file "):
            path = clean[10:].strip()
            return CommandResult(True, open_file(path))

        if lower.startswith("open website "):
            url = clean[13:].strip()
            return CommandResult(True, open_web(url))

        if lower.startswith("search web "):
            query = clean[11:].strip()
            results = web_search(query, retries=settings.search_retries)
            return CommandResult(True, f"Web search for '{query}':\n{results}", data_for_llm=results)

        if lower.startswith("run command "):
            cmd = clean[12:].strip()
            return CommandResult(True, run_shell(cmd, timeout=settings.command_timeout_seconds))

        if lower.startswith("read pdf "):
            path = clean[9:].strip()
            if not path.lower().endswith(".pdf"):
                return CommandResult(True, "Please provide a valid PDF file path.")
            try:
                text_data = extract_pdf_text(path)
                clipped = text_data[:8000]
                return CommandResult(
                    True,
                    "PDF text extracted. I will summarize it.",
                    data_for_llm=f"Summarize this PDF content:\n{clipped}",
                )
            except Exception as exc:
                return CommandResult(True, f"PDF read failed: {exc}")

        return CommandResult(False, "")
