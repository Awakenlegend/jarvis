import logging
import sqlite3
import threading
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class MemoryStore:
    def __init__(self, db_path: Path, max_rows: int = 1000) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_rows = max_rows
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.conn.commit()

    def add_message(self, role: str, content: str) -> None:
        if not content:
            return
        with self.lock:
            cur = self.conn.cursor()
            cur.execute("INSERT INTO conversation(role, content) VALUES(?, ?)", (role, content))
            cur.execute(
                """
                DELETE FROM conversation
                WHERE id IN (
                    SELECT id FROM conversation ORDER BY id DESC LIMIT -1 OFFSET ?
                )
                """,
                (self.max_rows,),
            )
            self.conn.commit()

    def recent_messages(self, limit: int = 20) -> List[Tuple[str, str]]:
        safe_limit = max(1, min(limit, self.max_rows))
        with self.lock:
            cur = self.conn.cursor()
            cur.execute(
                "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
                (safe_limit,),
            )
            rows = cur.fetchall()
        return list(reversed(rows))

    def close(self) -> None:
        with self.lock:
            try:
                self.conn.close()
            except Exception:
                logger.exception("Failed to close memory store")
