"""SQLite-backed URL deduplication for normalized items."""

import sqlite3
from datetime import datetime
from pathlib import Path

from src.models import Item

_SCHEMA = """
CREATE TABLE IF NOT EXISTS seen (
    url_hash TEXT PRIMARY KEY,
    url TEXT NOT NULL,
    source TEXT,
    first_seen TEXT NOT NULL
)
"""


class SeenDB:
    """Thin sqlite3 wrapper that records seen URLs and answers is_new()."""

    def __init__(self, db_path: str | Path):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def is_new(self, item: Item) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen WHERE url_hash = ?", (item.id,)
        ).fetchone()
        if row is not None:
            return False
        self._conn.execute(
            "INSERT INTO seen (url_hash, url, source, first_seen) VALUES (?, ?, ?, ?)",
            (
                item.id,
                item.url,
                item.source,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        return True

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
