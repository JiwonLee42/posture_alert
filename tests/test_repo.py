import sqlite3
from datetime import datetime

import pytest

from posture_alert.storage.repo import Repo

DAY = datetime(2026, 11, 24, 10)


def test_오늘_완료_횟수():
    r = Repo(":memory:")
    r.record("posture", "chin_tuck", "done", ts=DAY)
    r.record("posture", "chin_tuck", "skip", ts=DAY)
    r.record("stand", None, "away", ts=DAY)
    r.record("posture", "chin_tuck", "done", ts=datetime(2026, 11, 23, 10))
    assert r.count_today("done", today=DAY) == 1
    assert r.count_today("away", kind="stand", today=DAY) == 1
    assert r.completed_today(today=DAY) == 2


def test_알림_띄우면_shown_미완료로_생성():
    r = Repo(":memory:")
    eid = r.create_event("posture", "chin_tuck", ts=DAY)
    row = r.get(eid)
    assert row["result"] == "shown"
    assert row["completed"] == 0 and row["completed_at"] is None


def test_했어요_누르면_같은_행을_완료로_PATCH():
    r = Repo(":memory:")
    eid = r.create_event("posture", "chin_tuck", ts=DAY)
    r.answer(eid, "done", ts=datetime(2026, 11, 24, 10, 1))
    row = r.get(eid)
    assert row["result"] == "done"
    assert row["completed"] == 1
    assert row["completed_at"] == "2026-11-24T10:01:00"
    assert r.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1  # 새 행 안 생김


def test_미루면_완료_아님():
    r = Repo(":memory:")
    eid = r.create_event("stand", "stand_water", ts=DAY)
    r.answer(eid, "snooze")
    assert r.get(eid)["completed"] == 0


def test_허용되지_않은_컬럼은_PATCH_불가():
    r = Repo(":memory:")
    eid = r.create_event("posture", None)
    with pytest.raises(ValueError):
        r.patch_event(eid, kind="eye")


def test_예전_DB에_컬럼_자동_추가(tmp_path):
    db = tmp_path / "old.sqlite3"
    c = sqlite3.connect(db)
    c.executescript("""
        CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL,
            kind TEXT NOT NULL, exercise_id TEXT, result TEXT NOT NULL);
        INSERT INTO events (ts, kind, exercise_id, result)
            VALUES ('2026-11-24T09:00:00', 'posture', 'chin_tuck', 'done');
    """)
    c.close()
    r = Repo(db)
    row = r.get(1)
    assert row["completed"] == 1
    assert row["completed_at"] == "2026-11-24T09:00:00"


# --- 단계 사이클 / 세션 ---
from posture_alert.engine.stages import Stage  # noqa: E402


def test_stages_테이블에_8단계_시드():
    r = Repo(":memory:")
    rows = r.conn.execute("SELECT id, code, exercise_id FROM stages ORDER BY id").fetchall()
    assert [tuple(x) for x in rows][:2] == [(1, "EYE_FAR", "eye_far"), (2, "CHIN_TUCK", "chin_tuck")]
    assert len(rows) == 8


def test_사이클_행에_단계별_boolean_컬럼():
    r = Repo(":memory:")
    cid = r.new_cycle(None, ts=DAY)
    assert all(v is False for v in r.cycle_checks(cid).values())
    r.mark_stage_done(cid, Stage.NECK_SIDE)
    checks = r.cycle_checks(cid)
    assert checks[Stage.NECK_SIDE] is True
    assert sum(checks.values()) == 1
    assert r.get_cycle(cid)["stage_4"] == 1


def test_사이클_위치_저장과_복원():
    r = Repo(":memory:")
    assert r.latest_cycle() is None
    cid = r.new_cycle(None)
    assert r.latest_cycle() == (cid, None)
    r.set_position(cid, Stage.SEAT_BACK)
    assert r.latest_cycle() == (cid, Stage.SEAT_BACK)


def test_boolean_컬럼엔_0_1만():
    r = Repo(":memory:")
    cid = r.new_cycle(None)
    with pytest.raises(sqlite3.IntegrityError):
        r.conn.execute("UPDATE cycles SET stage_1 = 5 WHERE id = ?", (cid,))


def test_켜둔_시간_분_저장():
    r = Repo(":memory:")
    sid = r.start_session(ts=DAY)
    r.save_uptime(sid, 37, ts=datetime(2026, 11, 24, 10, 37))
    sid2 = r.start_session(ts=datetime(2026, 11, 24, 14))
    r.save_uptime(sid2, 5)
    assert r.uptime_today(today=DAY) == 42


def test_이벤트에_단계와_사이클_기록():
    r = Repo(":memory:")
    cid = r.new_cycle(None)
    eid = r.create_event("posture", "chin_tuck", stage=Stage.CHIN_TUCK, cycle_id=cid)
    row = r.get(eid)
    assert row["stage"] == 2 and row["cycle_id"] == cid
