"""SQLite 저장소: 알림 기록.

흐름 (REST로 치면 POST → PATCH):
1. 알림을 띄울 때   create_event()  → INSERT, result='shown', completed=0
2. 사용자가 응답할 때 patch_event()   → 같은 행을 UPDATE (완료면 completed=1, completed_at 기록)
"""
import sqlite3
from datetime import datetime
from pathlib import Path

from ..engine.stages import STAGES, Stage

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

# 단계 마스터: 단계 번호(enum 값), 자세(동작 id), 멘트
STAGES_SCHEMA = """
CREATE TABLE IF NOT EXISTS stages (
    id          INTEGER PRIMARY KEY,   -- Stage enum 값 1~8
    code        TEXT NOT NULL,         -- EYE_FAR, CHIN_TUCK ...
    exercise_id TEXT NOT NULL,         -- 자세 (exercises.json)
    kind        TEXT NOT NULL,         -- eye / posture / stretch / stand
    title       TEXT NOT NULL,         -- 멘트 제목
    body        TEXT NOT NULL          -- 멘트 본문
);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,   -- character, onboarded_at ...
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at     TEXT NOT NULL,              -- 앱을 켠 시각
    last_seen_at   TEXT NOT NULL,              -- 마지막으로 기록한 시각
    uptime_minutes INTEGER NOT NULL DEFAULT 0  -- 켠 뒤로 지난 분
);
"""


def _cycles_schema() -> str:
    """사이클 1바퀴 = 1행. 단계마다 했는지(boolean) 컬럼 stage_1 ~ stage_8."""
    stage_cols = ",\n".join(
        f"    {s.column} INTEGER NOT NULL DEFAULT 0 CHECK ({s.column} IN (0, 1))" for s in Stage)
    return f"""
CREATE TABLE IF NOT EXISTS cycles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    started_at TEXT NOT NULL,
    position   INTEGER NOT NULL DEFAULT 0,   -- 마지막으로 보여준 단계 (0 = 아직 없음)
{stage_cols}
);
"""


# 예전 DB(컬럼 없던 버전)에 자동으로 추가할 컬럼
MIGRATIONS = {
    "completed": "ALTER TABLE events ADD COLUMN completed INTEGER NOT NULL DEFAULT 0",
    "completed_at": "ALTER TABLE events ADD COLUMN completed_at TEXT",
    "stage": "ALTER TABLE events ADD COLUMN stage INTEGER",
    "cycle_id": "ALTER TABLE events ADD COLUMN cycle_id INTEGER",
}

PATCHABLE = {"result", "completed", "completed_at", "exercise_id"}


def _now(ts: datetime | None = None) -> str:
    return (ts or datetime.now()).isoformat(timespec="seconds")


class Repo:
    def __init__(self, path: Path | str):
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA + STAGES_SCHEMA + _cycles_schema())
        self._migrate()
        self._seed_stages()

    def _migrate(self) -> None:
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(events)")}
        for col, sql in MIGRATIONS.items():
            if col not in cols:
                self.conn.execute(sql)
        # 단계가 늘어나면 사이클 테이블에도 컬럼 추가
        cycle_cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(cycles)")}
        for st in Stage:
            if st.column not in cycle_cols:
                self.conn.execute(
                    f"ALTER TABLE cycles ADD COLUMN {st.column} INTEGER NOT NULL DEFAULT 0")
        # 예전에 done으로 저장된 기록은 완료로 채워 넣음
        self.conn.execute(
            "UPDATE events SET completed = 1, completed_at = COALESCE(completed_at, ts) "
            "WHERE result IN ('done', 'away') AND completed = 0")
        self.conn.commit()

    def _seed_stages(self) -> None:
        """코드의 Stage enum + STAGES 를 stages 테이블에 반영 (켤 때마다 덮어씀)."""
        self.conn.executemany(
            "INSERT OR REPLACE INTO stages (id, code, exercise_id, kind, title, body) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [(st.value, st.name, i.exercise_id, i.kind, i.title, i.body)
             for st, i in STAGES.items()],
        )
        self.conn.commit()

    # --- 초기화 ---
    RESET_TABLES = ("events", "cycles", "sessions", "settings")

    def reset(self) -> None:
        """기록 행을 모두 지워 처음 상태로 (테이블 구조와 stages 단계 정의는 유지).
        AUTOINCREMENT 번호도 1부터 다시 시작하게 sqlite_sequence 도 비운다."""
        with self.conn:  # 한 트랜잭션: 중간에 실패하면 아무것도 안 지워짐
            for t in self.RESET_TABLES:
                self.conn.execute(f"DELETE FROM {t}")
            self.conn.execute(
                f"DELETE FROM sqlite_sequence WHERE name IN ({','.join('?' * len(self.RESET_TABLES))})",
                self.RESET_TABLES)
        self._seed_stages()

    # --- 설정 (처음 실행 때 고른 캐릭터 등) ---
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        self.conn.commit()

    def events_since(self, ts: str | None) -> list[tuple[str, str]]:
        """ts(시작한 시각) 이후의 (kind, result) 전부 → 남은 수술비 계산용."""
        return [tuple(r) for r in self.conn.execute(
            "SELECT kind, result FROM events WHERE ts >= ? ORDER BY id", (ts or "",))]

    # --- 세션: 앱을 켜둔 시간 ---
    def start_session(self, ts: datetime | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO sessions (started_at, last_seen_at) VALUES (?, ?)", (_now(ts), _now(ts)))
        self.conn.commit()
        return cur.lastrowid

    def save_uptime(self, session_id: int, minutes: int, ts: datetime | None = None) -> None:
        self.conn.execute(
            "UPDATE sessions SET uptime_minutes = ?, last_seen_at = ? WHERE id = ?",
            (minutes, _now(ts), session_id))
        self.conn.commit()

    def uptime_today(self, today: datetime | None = None) -> int:
        day = (today or datetime.now()).date().isoformat()
        return self.conn.execute(
            "SELECT COALESCE(SUM(uptime_minutes), 0) FROM sessions WHERE started_at LIKE ?",
            (f"{day}%",)).fetchone()[0]

    # --- 사이클: 단계별 했는지(boolean) ---
    def latest_cycle(self) -> tuple[int, Stage | None] | None:
        row = self.conn.execute("SELECT id, position FROM cycles ORDER BY id DESC LIMIT 1").fetchone()
        if row is None:
            return None
        return row["id"], (Stage(row["position"]) if row["position"] else None)

    def new_cycle(self, session_id: int | None, ts: datetime | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO cycles (session_id, started_at) VALUES (?, ?)", (session_id, _now(ts)))
        self.conn.commit()
        return cur.lastrowid

    def set_position(self, cycle_id: int, stage: Stage) -> None:
        self.conn.execute("UPDATE cycles SET position = ? WHERE id = ?", (int(stage), cycle_id))
        self.conn.commit()

    def mark_stage_done(self, cycle_id: int, stage: Stage) -> None:
        """PATCH: 해당 사이클 행의 stage_N 컬럼을 1(했음)로."""
        col = Stage(stage).column  # enum 에서만 만들어지므로 SQL에 넣어도 안전
        self.conn.execute(f"UPDATE cycles SET {col} = 1 WHERE id = ?", (cycle_id,))
        self.conn.commit()

    def get_cycle(self, cycle_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM cycles WHERE id = ?", (cycle_id,)).fetchone()
        return dict(row) if row else None

    def cycle_checks(self, cycle_id: int) -> dict[Stage, bool]:
        row = self.get_cycle(cycle_id) or {}
        return {st: bool(row.get(st.column, 0)) for st in Stage}

    # --- POST ---
    def create_event(self, kind: str, exercise_id: str | None,
                     ts: datetime | None = None, stage: Stage | None = None,
                     cycle_id: int | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO events (ts, kind, exercise_id, result, stage, cycle_id) "
            "VALUES (?, ?, ?, 'shown', ?, ?)",
            (_now(ts), kind, exercise_id, int(stage) if stage else None, cycle_id),
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
