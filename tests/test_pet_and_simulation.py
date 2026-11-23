"""캐릭터(펫)·숫자 창 동작 + 하루 근무 시뮬레이션. 화면 없이(offscreen) 돈다."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from PySide6.QtCore import QEvent, QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from posture_alert.engine.billing import SURGERY_COST, remaining  # noqa: E402
from posture_alert.engine.scheduler import Kind, Scheduler, Snapshot  # noqa: E402
from posture_alert.main import App  # noqa: E402
from posture_alert.storage.repo import Repo  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def close(app):
    if app.card is not None:
        app.card._answer("skip")
    app.shutdown()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()


def started_app(qapp, tmp_path):
    app = App(qapp, 1.0, repo=Repo(tmp_path / "pet.sqlite3"))
    app._on_started("f")     # 여자 고르고 시작 (첫 알림 타이머는 이벤트 루프가 없어 안 돎)
    return app


# ---------- 하루 근무 시뮬레이션 (시계를 가짜로 돌림) ----------

def simulate_workday(answer, hours=8, every=30):
    """9시부터 hours시간, 30초마다 tick. 알림이 뜨면 answer(n) 의 결과(done/skip)를 기록한다.
    반환: (뜬 알림 수, 남은 수술비, 이벤트 목록)"""
    sch = Scheduler.for_cycle(every)
    t = datetime(2026, 1, 5, 9, 0)
    end = t + timedelta(hours=hours)
    events, n = [], 0
    while t < end:
        kind = sch.tick(Snapshot(now=t, idle_seconds=30))   # 30초째 가만히 → 타이핑 중 아님
        if kind is not None:
            n += 1
            events.append((kind.value, answer(n)))
        t += timedelta(seconds=30)
    return n, remaining(events), events


def test_성실하게_다_하면_수술비가_크게_줄어든다():
    n, left, _ = simulate_workday(lambda n: "done")
    assert 14 <= n <= 18             # 8시간 / 30분 + 일어나기 끼어들기
    assert left < SURGERY_COST
    assert left <= SURGERY_COST - 10 * 1_000_000


def test_전부_무시하면_3000만원_그대로():
    n, left, _ = simulate_workday(lambda n: "skip")
    assert n > 10 and left == SURGERY_COST


def test_가끔_무시해도_하는_쪽이_이기면_줄어든다():
    n, left, _ = simulate_workday(lambda n: "skip" if n % 3 == 0 else "done")
    assert left < SURGERY_COST


def test_오래_앉아있으면_일어나기가_끼어든다():
    _, _, events = simulate_workday(lambda n: "skip", hours=4)
    assert Kind.STAND.value in [k for k, _ in events]


def test_자리를_비우면_타이머가_초기화된다():
    sch = Scheduler.for_cycle(30)
    t = datetime(2026, 1, 5, 9, 0)
    sch.tick(Snapshot(now=t, idle_seconds=30))
    sch.tick(Snapshot(now=t + timedelta(minutes=25), idle_seconds=600))   # 10분 자리 비움
    assert sch.sitting_since is None
    # 돌아와서 다시 앉으면 30분을 처음부터 센다
    back = t + timedelta(minutes=26)
    sch.tick(Snapshot(now=back, idle_seconds=30))
    assert sch.tick(Snapshot(now=back + timedelta(minutes=10), idle_seconds=30)) is None


# ---------- 캐릭터(펫) ----------

def test_시작하면_캐릭터가_바른_자세로_뜬다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    assert app.pet is not None and app.pet.isVisible()
    assert app.pet.bad is False
    assert "만원" in app.pet.bubble.text()
    close(app)


def test_알림이_뜨면_거북목_자세_답하면_바른_자세(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    app.show_next()
    assert app.pet.bad is True and app.pet.bubble.text() == "자세 확인!"
    app.card._answer("done")
    QTest.qWait(50)          # 답한 뒤 갱신 타이머가 돌 시간 (윈도우 CI에서 타이밍이 달라서 넉넉히)
    assert app.pet.bad is False
    close(app)


def test_캐릭터를_누르면_숫자창이_열리고_다시_누르면_접힌다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    QTest.mouseClick(app.pet, Qt.MouseButton.LeftButton)
    assert app.mini is not None and app.mini.isVisible()
    assert "남은 수술비" in app.mini.money.text()
    QTest.mouseClick(app.pet, Qt.MouseButton.LeftButton)
    assert not app.mini.isVisible()
    close(app)


def test_캐릭터를_끌면_옮겨지고_숫자창은_안_열린다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    before = app.pet.pos()
    QTest.mousePress(app.pet, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    QTest.mouseMove(app.pet, QPoint(60, 40))
    QTest.mouseRelease(app.pet, Qt.MouseButton.LeftButton, pos=QPoint(60, 40))
    assert app.pet.pos() != before
    assert app.mini is None or not app.mini.isVisible()
    close(app)


def test_숫자창_X를_누르면_종료할지_물어본다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    QTest.mouseClick(app.pet, Qt.MouseButton.LeftButton)       # 숫자 창 열기
    app.mini._hide_clicked()                                    # X
    assert app.confirm is not None and app.confirm.isVisible()
    assert not app.mini.isVisible()
    assert app.receipt_win is None                              # 아직 영수증은 안 뜸
    app.confirm._no()                                           # 아니요 → 아무 일 없음
    assert app.pet.isVisible()
    close(app)


def test_종료_예를_누르면_영수증이_뜨고_닫으면_앱이_종료(qapp, tmp_path, monkeypatch):
    app = started_app(qapp, tmp_path)
    app.repo.record("posture", None, "done")
    quits = []
    monkeypatch.setattr(app.qapp, "quit", lambda: quits.append(1))
    QTest.mouseClick(app.pet, Qt.MouseButton.LeftButton)
    app.mini._hide_clicked()
    app.confirm._yes()
    assert app.receipt_win is not None and app.receipt_win.isVisible()
    assert quits == []                                          # 영수증을 보는 동안은 안 꺼짐
    app.receipt_win.close()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert quits == [1]
    close(app)


def test_트레이로_영수증을_열었다_닫아도_앱은_안_꺼진다(qapp, tmp_path, monkeypatch):
    app = started_app(qapp, tmp_path)
    quits = []
    monkeypatch.setattr(app.qapp, "quit", lambda: quits.append(1))
    app.show_receipt()
    app.receipt_win.close()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert quits == []
    close(app)


def test_종료_확인_중에는_알림이_뜨지_않는다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    app.ask_quit()
    app.show_next()                      # 알림 시각이 됐어도
    assert app.card is None              # 종료가 우선
    app.confirm._no()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    app.show_next()                      # 취소하면 다시 알림이 뜬다
    assert app.card is not None
    close(app)


def test_종료를_누르면_열린_알림도_같이_닫히고_수술비는_그대로(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    app.show_next()
    assert app.card is not None
    before = app.remaining()
    app.ask_quit()
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert app.card is None
    assert app.remaining() == before
    result = app.repo.conn.execute("SELECT result FROM events ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert result == "shown"
    close(app)


def test_트레이로_캐릭터를_숨기고_다시_보인다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    app.toggle_mini()
    assert not app.pet.isVisible()
    app.toggle_mini()
    assert app.pet.isVisible()
    close(app)


def test_앞_알림에_답_안_해도_다음_시각에_다음_단계로_넘어간다(qapp, tmp_path):
    app = started_app(qapp, tmp_path)
    app.fire(Kind.EYE)                       # 1단계
    first = app.cycle.position
    for _ in range(3):
        app.fire(Kind.EYE)                   # 답을 한 번도 안 눌러도
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.processEvents()
    assert app.cycle.position == first + 3   # 단계가 계속 넘어간다
    rows = app.repo.conn.execute("SELECT stage, result FROM events ORDER BY id").fetchall()
    assert [tuple(r) for r in rows][:3] == [(1, "timeout"), (2, "timeout"), (3, "timeout")]
    assert app.remaining() == SURGERY_COST   # 3000만원 위로는 안 올라감
    close(app)


def test_알림은_정확히_30분_간격이고_일어나기가_단계를_삼키지_않는다():
    sch = Scheduler.for_cycle(30)
    t = datetime(2026, 1, 5, 9, 0)
    fired = []
    while t < datetime(2026, 1, 5, 9, 0) + timedelta(hours=9):
        k = sch.tick(Snapshot(now=t, idle_seconds=30))
        if k is not None:
            fired.append((t, k))
        t += timedelta(seconds=30)
    gaps = {(b[0] - a[0]) for a, b in zip(fired, fired[1:])}
    assert gaps == {timedelta(minutes=30)}                    # 너무 자주 오지 않는다
    stands = [i for i, (_, k) in enumerate(fired) if k is Kind.STAND]
    assert stands == [2, 5, 8, 11, 14]                    # 3번에 한 번(90분마다)만 일어나기
    assert len(fired) - len(stands) >= 10                     # 나머지는 모두 단계 알림
