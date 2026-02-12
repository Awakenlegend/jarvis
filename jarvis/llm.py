import logging
import time
from typing import Iterable, Tuple

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, url: str, model: str, timeout: int = 120, retries: int = 2) -> None:
        self.url = url
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def _build_prompt(self, history: Iterable[Tuple[str, str]], user_input: str) -> str:
        lines = [
            "You are Jarvis, a concise and helpful personal AI assistant.",
            "Use plain text responses.",
        ]
        for role, content in history:
            lines.append(f"{role.upper()}: {content}")
        lines.append(f"USER: {user_input}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)

    def generate(self, history: Iterable[Tuple[str, str]], user_input: str) -> str:
        payload = {
            "model": self.model,
            "prompt": self._build_prompt(history, user_input),
            "stream": False,
        }

        last_error = ""
        for attempt in range(self.retries + 1):
            try:
                response = requests.post(self.url, json=payload, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                text = data.get("response", "").strip()
                return text or "I could not generate a response."
            except Exception as exc:
                last_error = str(exc)
                logger.warning("Ollama request failed (attempt %s): %s", attempt + 1, exc)
                if attempt < self.retries:
                    time.sleep(0.5 * (attempt + 1))

        return f"I am having trouble reaching the local model right now: {last_error}"
