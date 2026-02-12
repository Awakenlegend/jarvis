import json
import logging
import queue
import threading
import time
from typing import Optional

import pyttsx3
import sounddevice as sd
from vosk import KaldiRecognizer, Model

logger = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self, rate: int = 180) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", rate)
        self._queue: queue.Queue[str] = queue.Queue(maxsize=64)
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._speak_loop, daemon=True, name="tts-worker")
        self._thread.start()

    def _speak_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.25)
            except queue.Empty:
                continue
            if not text:
                continue
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception:
                logger.exception("TTS playback failed")

    def speak(self, text: str) -> None:
        if not text or self._stop_event.is_set():
            return
        try:
            if self._queue.full():
                try:
                    self._queue.get_nowait()
                except queue.Empty:
                    pass
            self._queue.put_nowait(text)
        except queue.Full:
            logger.warning("TTS queue full; dropping speech")

    def shutdown(self) -> None:
        self._stop_event.set()
        try:
            self._queue.put_nowait("")
        except queue.Full:
            pass
        if self._thread.is_alive():
            self._thread.join(timeout=2)


class SpeechRecognizer:
    def __init__(self, model_path: str, sample_rate: int = 16000, channels: int = 1) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=128)
        self.text_queue: queue.Queue[str] = queue.Queue(maxsize=128)
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        self.stop_event = threading.Event()
        self.listener_thread: Optional[threading.Thread] = None
        self._queue_lock = threading.Lock()

    def _push_text(self, text: str) -> None:
        if not text:
            return
        with self._queue_lock:
            if self.text_queue.full():
                try:
                    self.text_queue.get_nowait()
                except queue.Empty:
                    pass
            self.text_queue.put_nowait(text)

    def _callback(self, indata, frames, time_info, status):
        if status:
            logger.warning("Audio stream status: %s", status)
        if self.stop_event.is_set():
            return
        try:
            self.audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            try:
                self.audio_queue.get_nowait()
                self.audio_queue.put_nowait(bytes(indata))
            except queue.Empty:
                pass
            except queue.Full:
                pass

    def _listen_loop(self) -> None:
        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=8000,
                dtype="int16",
                channels=self.channels,
                callback=self._callback,
            ):
                while not self.stop_event.is_set():
                    try:
                        data = self.audio_queue.get(timeout=0.25)
                    except queue.Empty:
                        time.sleep(0.01)
                        continue
                    try:
                        if self.recognizer.AcceptWaveform(data):
                            result = json.loads(self.recognizer.Result())
                            text = result.get("text", "").strip()
                            self._push_text(text)
                    except Exception:
                        logger.exception("Recognizer processing failed")
        except Exception:
            logger.exception("Background listener crashed")

    def start_background_listener(self) -> None:
        if self.listener_thread and self.listener_thread.is_alive():
            return
        self.stop_event.clear()
        self.listener_thread = threading.Thread(target=self._listen_loop, daemon=True, name="audio-listener")
        self.listener_thread.start()

    def stop_background_listener(self) -> None:
        self.stop_event.set()
        try:
            self.audio_queue.put_nowait(b"")
        except queue.Full:
            pass
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=3)

    def listen_once(self, timeout_seconds: Optional[int] = None) -> str:
        try:
            return self.text_queue.get(timeout=timeout_seconds).strip()
        except queue.Empty:
            return ""
