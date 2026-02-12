import logging
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

from jarvis.audio import SpeechEngine, SpeechRecognizer
from jarvis.commands import CommandRouter
from jarvis.config import settings
from jarvis.llm import OllamaClient
from jarvis.memory import MemoryStore
from jarvis.plugins import load_plugins

logger = logging.getLogger(__name__)


class JarvisAssistant:
    def __init__(self) -> None:
        self.speech = SpeechEngine(rate=settings.speech_rate)
        self.recognizer = SpeechRecognizer(
            model_path=str(settings.model_path),
            sample_rate=settings.sample_rate,
            channels=settings.channels,
        )
        self.memory = MemoryStore(settings.sqlite_path, max_rows=settings.max_memory_rows)
        self.llm = OllamaClient(
            settings.ollama_url,
            settings.ollama_model,
            timeout=settings.ollama_timeout_seconds,
            retries=settings.ollama_retries,
        )
        self.router = CommandRouter()
        self.plugins = load_plugins()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jarvis-worker")
        self.shutdown_event = threading.Event()
        self._shutdown_lock = threading.Lock()
        self._futures: set[Future] = set()
        self._futures_lock = threading.Lock()

    def _reply(self, text: str) -> None:
        if not text:
            return
        logger.info("Jarvis reply: %s", text)
        print(f"Jarvis: {text}")
        try:
            self.speech.speak(text)
        except Exception:
            logger.exception("TTS failed")

    def _check_plugins(self, text: str) -> str | None:
        lower = text.lower()
        for plugin in self.plugins:
            try:
                if plugin.trigger in lower:
                    return plugin.execute(text)
            except Exception:
                logger.exception("Plugin execution failed: %s", getattr(plugin, "name", "unknown"))
        return None

    def _respond_with_llm(self, user_text: str, extra_context: str = "") -> str:
        history = self.memory.recent_messages(limit=settings.max_memory_messages)
        prompt = user_text if not extra_context else f"{user_text}\n\nContext:\n{extra_context}"
        return self.llm.generate(history, prompt)

    def handle_user_text(self, text: str) -> None:
        if not text or self.shutdown_event.is_set():
            return
        try:
            self.memory.add_message("user", text)

            plugin_result = self._check_plugins(text)
            if plugin_result:
                self.memory.add_message("assistant", plugin_result)
                self._reply(plugin_result)
                return

            command_result = self.router.handle(text)
            if command_result.handled:
                if command_result.data_for_llm:
                    llm_reply = self._respond_with_llm(text, command_result.data_for_llm)
                    full_response = f"{command_result.response}\n{llm_reply}" if command_result.response else llm_reply
                else:
                    full_response = command_result.response
                self.memory.add_message("assistant", full_response)
                self._reply(full_response)
                return

            llm_reply = self._respond_with_llm(text)
            self.memory.add_message("assistant", llm_reply)
            self._reply(llm_reply)
        except Exception:
            logger.exception("Failed to handle user text")
            self._reply("I ran into an error processing that request.")

    def _track_future(self, future: Future) -> None:
        with self._futures_lock:
            self._futures.add(future)
        future.add_done_callback(self._discard_future)

    def _discard_future(self, future: Future) -> None:
        with self._futures_lock:
            self._futures.discard(future)

    def shutdown(self) -> None:
        with self._shutdown_lock:
            if self.shutdown_event.is_set():
                return
            self.shutdown_event.set()

            self.recognizer.stop_background_listener()

            current = threading.current_thread().name
            in_worker = current.startswith("jarvis-worker")
            self.executor.shutdown(wait=not in_worker, cancel_futures=True)

            self.memory.close()
            self.speech.shutdown()

    def run(self) -> None:
        self._reply("Jarvis online. Say Jarvis to wake me.")
        self.recognizer.start_background_listener()

        while not self.shutdown_event.is_set():
            try:
                heard = self.recognizer.listen_once(timeout_seconds=1)
            except Exception:
                logger.exception("Listen failed")
                heard = ""

            if not heard:
                time.sleep(settings.listener_poll_seconds)
                continue

            logger.info("Heard: %s", heard)
            if settings.wake_word not in heard.lower():
                continue

            self._reply("Listening")
            command = self.recognizer.listen_once(timeout_seconds=8)
            if not command:
                self._reply("I did not catch that.")
                continue

            logger.info("Command: %s", command)
            if command.lower() in {"exit", "quit", "shutdown jarvis"}:
                self._reply("Shutting down.")
                self.shutdown()
                break

            if not self.shutdown_event.is_set():
                future = self.executor.submit(self.handle_user_text, command)
                self._track_future(future)
