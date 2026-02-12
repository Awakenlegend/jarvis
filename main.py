import signal

from jarvis.assistant import JarvisAssistant
from jarvis.logging_utils import configure_logging


def main() -> None:
    configure_logging()
    assistant = JarvisAssistant()

    def _handle_shutdown(signum, frame):
        assistant.shutdown()

    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)

    assistant.run()


if __name__ == "__main__":
    main()
