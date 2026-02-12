import platform
from jarvis.plugins.base import Plugin


class SystemInfoPlugin(Plugin):
    name = "system_info"
    trigger = "system info"

    def execute(self, text: str) -> str:
        return f"System: {platform.system()} {platform.release()} | Machine: {platform.machine()}"
