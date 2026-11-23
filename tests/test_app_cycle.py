"""실제 App(Qt 포함)으로 단계 사이클·기록 흐름 확인. 화면 없이(offscreen) 돈다."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from posture_alert.engine.stages import Stage  # noqa: E402
from posture_alert.main import App  # noqa: E402
from posture_alert.storage.repo import Repo  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def close(app):
    if app.card is not None:
        app.card._answer("skip")
    app.shutdown()
    QApplication.processEvents()  # deleteLater 처리 (창 정리)


def test_알림마다_다음_단계로_사이클(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "a.sqlite3"))
    shown = []
    for _ in range(10):
        app.show_next()
        shown.append(app.cycle.position)
        app.card._answer("skip")
    assert shown == [*Stage, Stage.EYE_FAR, Stage.CHIN_TUCK]
    cycles = app.repo.conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0]
    assert cycles == 2
    close(app)


def test_했어요는_사이클_컬럼을_1로(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "b.sqlite3"))
    app.show_next()                      # 1단계 (눈: 작은 창)
    app.card._answer("done")
    app.show_next()                      # 2단계 (턱 당기기)
    app.card._complete()
    app.show_next()                      # 3단계는 미룸
    app.card._answer("snooze")
    row = app.repo.get_cycle(app.cycle.cycle_no)
    assert (row["stage_1"], row["stage_2"], row["stage_3"]) == (1, 1, 0)
    ev = app.repo.conn.execute(
        "SELECT stage, result, completed FROM events ORDER BY id").fetchall()
    assert [tuple(e) for e in ev] == [(1, "done", 1), (2, "done", 1), (3, "snooze", 0)]
    close(app)


def test_다시_켜면_이어서_돈다(qapp, tmp_path):
    db = tmp_path / "c.sqlite3"
    app = App(qapp, 1.0, repo=Repo(db))
    for _ in range(3):
        app.show_next()
        app.card._answer("skip")
    no = app.cycle.cycle_no
    close(app)

    app2 = App(qapp, 1.0, repo=Repo(db))
    app2.show_next()
    assert (app2.cycle.cycle_no, app2.cycle.position) == (no, Stage.SHOULDER_OPEN + 1)
    close(app2)


def test_켜둔_시간을_세션에_저장(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "d.sqlite3"))
    app.uptime.started -= 5 * 60 + 10
    app.on_uptime()
    row = app.repo.conn.execute(
        "SELECT uptime_minutes FROM sessions WHERE id = ?", (app.session_id,)).fetchone()
    assert row[0] == 5
    close(app)
