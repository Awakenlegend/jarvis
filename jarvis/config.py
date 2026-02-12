from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class Settings(BaseModel):
    wake_word: str = "jarvis"
    sample_rate: int = 16000
    channels: int = 1
    model_path: Path = Field(default_factory=lambda: Path("models/vosk-model-small-en-us-0.15"))
    sqlite_path: Path = Field(default_factory=lambda: Path("data/memory.db"))
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    ollama_model: str = "llama3.1:8b"
    speech_rate: int = 180
    max_memory_messages: int = 20
    max_memory_rows: int = 1000
    command_timeout_seconds: int = 20
    ollama_timeout_seconds: int = 45
    ollama_retries: int = 2
    search_retries: int = 2
    listener_poll_seconds: float = 0.25

    @field_validator("wake_word")
    @classmethod
    def validate_wake_word(cls, value: str) -> str:
        clean = value.strip().lower()
        if not clean:
            raise ValueError("wake_word cannot be empty")
        return clean

    @field_validator("sample_rate")
    @classmethod
    def validate_sample_rate(cls, value: int) -> int:
        if value not in {8000, 16000, 22050, 44100, 48000}:
            raise ValueError("sample_rate must be a common supported value")
        return value

    @field_validator("channels")
    @classmethod
    def validate_channels(cls, value: int) -> int:
        if value < 1 or value > 2:
            raise ValueError("channels must be 1 or 2")
        return value


settings = Settings()
