from datetime import datetime
from jarvis.plugins.base import Plugin


class TimePlugin(Plugin):
    name = "time"
    trigger = "time"

    def execute(self, text: str) -> str:
        return datetime.now().strftime("Current time is %Y-%m-%d %H:%M:%S")
