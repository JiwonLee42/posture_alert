from posture_alert.engine.uptime import UptimeCounter


class FakeClock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_켤때부터_분만_센다():
    c = FakeClock()
    u = UptimeCounter(clock=c)
    assert u.minutes == 0
    c.t += 59
    assert u.minutes == 0
    c.t += 1
    assert u.minutes == 1
    c.t += 60 * 36 + 30
    assert u.minutes == 37


def test_분이_바뀔때만_저장할_값을_준다():
    c = FakeClock()
    u = UptimeCounter(clock=c)
    assert u.poll() is None
    c.t += 61
    assert u.poll() == 1
    c.t += 10
    assert u.poll() is None
    c.t += 120
    assert u.poll() == 3
