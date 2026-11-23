from datetime import datetime

from posture_alert.storage.repo import Repo


def test_오늘_완료_횟수():
    r = Repo(":memory:")
    day = datetime(2026, 11, 24, 10)
    r.record("posture", "chin_tuck", "done", ts=day)
    r.record("posture", "chin_tuck", "skip", ts=day)
    r.record("stand", None, "away", ts=day)
    r.record("posture", "chin_tuck", "done", ts=datetime(2026, 11, 23, 10))
    assert r.count_today("done", today=day) == 1
    assert r.count_today("away", kind="stand", today=day) == 1
