"""SQLite 저장소: 알림 기록.

흐름 (REST로 치면 POST → PATCH):
1. 알림을 띄울 때   create_event()  → INSERT, result='shown', completed=0
2. 사용자가 응답할 때 patch_event()   → 같은 행을 UPDATE (완료면 completed=1, completed_at 기록)
"""
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ts           TEXT NOT NULL,      -- 알림을 띄운 시각
    kind         TEXT NOT NULL,      -- eye / posture / stretch / stand
    exercise_id  TEXT,
    result       TEXT NOT NULL,      -- shown / done / snooze / skip / timeout / unsure / switched / away
    completed    INTEGER NOT NULL DEFAULT 0,   -- 했으면 1 (체크 표시)
    completed_at TEXT                 -- 완료 체크한 시각
);
"""

# 예전 DB(컬럼 없던 버전)에 자동으로 추가할 컬럼
MIGRATIONS = {
    "completed": "ALTER TABLE events ADD COLUMN completed INTEGER NOT NULL DEFAULT 0",
    "completed_at": "ALTER TABLE events ADD COLUMN completed_at TEXT",
}

PATCHABLE = {"result", "completed", "completed_at", "exercise_id"}


def _now(ts: datetime | None = None) -> str:
    return (ts or datetime.now()).isoformat(timespec="seconds")


class Repo:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(events)")}
        for col, sql in MIGRATIONS.items():
            if col not in cols:
                self.conn.execute(sql)
        # 예전에 done으로 저장된 기록은 완료로 채워 넣음
        self.conn.execute(
            "UPDATE events SET completed = 1, completed_at = COALESCE(completed_at, ts) "
            "WHERE result IN ('done', 'away') AND completed = 0")
        self.conn.commit()

    # --- POST ---
    def create_event(self, kind: str, exercise_id: str | None,
                     ts: datetime | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO events (ts, kind, exercise_id, result) VALUES (?, ?, ?, 'shown')",
            (_now(ts), kind, exercise_id),
        )
        self.conn.commit()
        return cur.lastrowid

    # --- PATCH ---
    def patch_event(self, event_id: int, **fields) -> None:
        bad = set(fields) - PATCHABLE
        if bad:
            raise ValueError(f"수정할 수 없는 컬럼: {bad}")
        if not fields:
            return
        sets = ", ".join(f"{k} = ?" for k in fields)
        self.conn.execute(f"UPDATE events SET {sets} WHERE id = ?", (*fields.values(), event_id))
        self.conn.commit()

    def answer(self, event_id: int, result: str, ts: datetime | None = None) -> None:
        """응답 저장. done이면 완료 체크(completed=1, completed_at)까지 같이 PATCH."""
        if result == "done":
            self.patch_event(event_id, result=result, completed=1, completed_at=_now(ts))
        else:
            self.patch_event(event_id, result=result)

    def get(self, event_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        return dict(row) if row else None

    # --- 한 번에 끝나는 기록 (자리 비움 등) ---
    def record(self, kind: str, exercise_id: str | None, result: str,
               ts: datetime | None = None) -> None:
        done = result in ("done", "away")
        self.conn.execute(
            "INSERT INTO events (ts, kind, exercise_id, result, completed, completed_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (_now(ts), kind, exercise_id, result, int(done), _now(ts) if done else None),
        )
        self.conn.commit()

    # --- 조회 ---
    def count_today(self, result: str, kind: str | None = None,
                    today: datetime | None = None) -> int:
        day = (today or datetime.now()).date().isoformat()
        sql = "SELECT COUNT(*) FROM events WHERE ts LIKE ? AND result = ?"
        args: list = [f"{day}%", result]
        if kind:
            sql += " AND kind = ?"
            args.append(kind)
        return self.conn.execute(sql, args).fetchone()[0]

    def completed_today(self, today: datetime | None = None) -> int:
        day = (today or datetime.now()).date().isoformat()
        return self.conn.execute(
            "SELECT COUNT(*) FROM events WHERE ts LIKE ? AND completed = 1", (f"{day}%",)
        ).fetchone()[0]

    def events_today(self, today: datetime | None = None) -> list[tuple[str, str]]:
        day = (today or datetime.now()).date().isoformat()
        return [tuple(r) for r in self.conn.execute(
            "SELECT kind, result FROM events WHERE ts LIKE ? ORDER BY id", (f"{day}%",))]
