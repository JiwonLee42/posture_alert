from datetime import datetime, timedelta

from posture_alert.engine.scheduler import Kind, Scheduler, Snapshot

T0 = datetime(2026, 11, 24, 9, 0)


def M(n):
    return timedelta(minutes=n)


def snap(minutes, idle=15, fs=False, meeting=False):
    return Snapshot(T0 + M(minutes), idle, fs, meeting)


def started():
    s = Scheduler.create()
    s.tick(snap(0))
    return s


def test_시작_직후엔_알림_없음():
    s = Scheduler.create()
    assert s.tick(snap(0)) is None


def test_20분엔_눈휴식():
    assert started().tick(snap(20)) is Kind.EYE


def test_30분엔_자세체크():
    s = started()
    s.tick(snap(20))
    assert s.tick(snap(30)) is Kind.POSTURE


def test_60분엔_스트레칭_하나만():
    assert started().tick(snap(60)) is Kind.STRETCH


def test_겹친_작은_알림은_같이_처리():
    s = started()
    s.tick(snap(60))
    assert s.tick(snap(61)) is None


def test_90분_연속_착석이면_일어나기():
    assert started().tick(snap(90)) is Kind.STAND


def test_일어나기는_30분마다_반복():
    s = started()
    assert s.tick(snap(90)) is Kind.STAND
    assert s.tick(snap(100)) is not Kind.STAND
    assert s.tick(snap(120)) is Kind.STAND


def test_자리비움이면_착석시간_초기화():
    s = started()
    s.tick(snap(50))
    s.tick(snap(55, idle=300))
    assert s.sitting_minutes(T0 + M(55)) == 0


def test_자리비움_후엔_타이머가_처음부터():
    s = started()
    s.tick(snap(55, idle=300))
    s.tick(snap(56))
    assert s.tick(snap(70)) is None
    assert s.tick(snap(76)) is Kind.EYE


def test_회의중엔_안띄우고_보류표시():
    s = started()
    assert s.tick(snap(30, meeting=True)) is None
    assert s.deferred


def test_회의_끝나면_바로_띄움():
    s = started()
    s.tick(snap(30, meeting=True))
    assert s.tick(snap(31)) is Kind.POSTURE
    assert not s.deferred


def test_전체화면이면_안띄움():
    assert started().tick(snap(30, fs=True)) is None


def test_타이핑중엔_기다림():
    s = started()
    assert s.tick(snap(30, idle=2)) is None
    assert s.tick(snap(30.2, idle=12)) is Kind.POSTURE


def test_디버그_속도():
    s = Scheduler.create(speed=60)
    t = datetime(2026, 1, 1)
    s.tick(Snapshot(t, 15))
    assert s.tick(Snapshot(t + timedelta(seconds=20), 15)) is Kind.EYE


def test_사이클_모드는_20분마다_한번():
    s = Scheduler.for_cycle(20)
    s.tick(snap(0))
    fired = [m for m in range(1, 81) if s.tick(snap(m))]
    assert fired == [20, 40, 60, 80]


def test_사이클_모드도_90분_착석이면_일어나기():
    s = Scheduler.for_cycle(20)
    s.tick(snap(0))
    kinds = {m: s.tick(snap(m)) for m in range(1, 91)}
    assert kinds[90] is Kind.STAND


def test_초단위_테스트_간격():
    s = Scheduler.for_cycle(3 / 60)  # 3초
    s.typing_grace_seconds = 0
    t = datetime(2026, 1, 1)
    s.tick(Snapshot(t, 0))
    fired = [sec for sec in range(1, 10) if s.tick(Snapshot(t + timedelta(seconds=sec), 0))]
    assert fired == [3, 6, 9]
