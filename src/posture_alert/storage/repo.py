"""SQLite 저장소: 알림 응답 기록."""
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    kind        TEXT NOT NULL,      -- eye / posture / stretch / stand
    exercise_id TEXT,
    result      TEXT NOT NULL       -- done / snooze / skip / unsure / away
);
"""


class Repo:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path))
        self.conn.executescript(SCHEMA)

    def record(self, kind: str, exercise_id: str | None, result: str,
               ts: datetime | None = None) -> None:
        self.conn.execute(
            "INSERT INTO events (ts, kind, exercise_id, result) VALUES (?, ?, ?, ?)",
            ((ts or datetime.now()).isoformat(timespec="seconds"), kind, exercise_id, result),
        )
        self.conn.commit()

    def count_today(self, result: str, kind: str | None = None,
                    today: datetime | None = None) -> int:
        day = (today or datetime.now()).date().isoformat()
        sql = "SELECT COUNT(*) FROM events WHERE ts LIKE ? AND result = ?"
        args: list = [f"{day}%", result]
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        return self.conn.execute(sql, args).fetchone()[0]
