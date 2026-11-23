"""실제 App(Qt 포함)으로 단계 사이클·기록 흐름 확인. 화면 없이(offscreen) 돈다."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtCore import QEvent  # noqa: E402
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
    # 닫힌 창의 deleteLater 를 실제로 처리 (이벤트 루프가 없는 테스트라 직접)
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


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


def test_처음엔_캐릭터_고르기_후_시작(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "e.sqlite3"))
    QApplication.processEvents()          # 처음 실행 → 캐릭터 고르기 창
    assert not app.started and app.onboarding is not None
    app.onboarding._picked("m")
    app.onboarding.finished.emit("m")
    assert app.started and app.character == "m"
    assert app.remaining() == 30_000_000
    close(app)


def test_했어요_하면_남은_수술비가_줄어듦(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "f.sqlite3"))
    app._on_started("f")
    app.show_next()                       # 1단계 눈 (-50만원)
    app.card._answer("done")
    app.show_next()                       # 2단계 턱 당기기 (-100만원)
    app.card._complete()
    assert app.remaining() == 30_000_000 - 500_000 - 1_000_000
    close(app)


def test_종료하면_DB_초기화(qapp, tmp_path):
    db = tmp_path / "g.sqlite3"
    app = App(qapp, 1.0, repo=Repo(db))
    app._on_started("f")
    app.show_next()                       # 1단계 눈 (작은 창)
    app.card._answer("done")
    app.on_quit()                         # aboutToQuit 에 연결된 처리
    close(app)
    r = Repo(db)
    for t in ("events", "cycles", "sessions", "settings"):
        assert r.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0
