from abc import ABC, abstractmethod


class Plugin(ABC):
    name: str
    trigger: str

    @abstractmethod
    def execute(self, text: str) -> str:
        raise NotImplementedError
