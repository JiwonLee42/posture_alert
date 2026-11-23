"""진입점: 트레이 아이콘 + 5초 타이머 + 알림 창 연결.

실행:
    uv run posture-alert                     # 일반 모드
    POSTURE_DEBUG=1 uv run posture-alert     # 1분 = 1초 (20초마다 눈 알림 ...)
    uv run posture-alert --demo posture      # 바로 카드 띄우기 (eye/posture/stretch/stand)
    uv run posture-alert --shot out.png --demo posture   # 카드 스크린샷 저장 후 종료
"""
import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .engine.content import ASSETS, load_exercises, message_for, pick
from .engine.scheduler import Kind, Scheduler
from .platform import get_monitor
from .storage.repo import Repo
from .ui.popup import GuideCard, LightToast
from .ui.retro import STYLESHEET, WARNING, WARNING_PAL, load_fonts, sprite


def assets_dir() -> Path:
    # PyInstaller로 묶였을 때는 임시 폴더(_MEIPASS) 아래에 assets가 풀린다
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "assets" if base else ASSETS


def data_path() -> Path:
    d = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    d.mkdir(parents=True, exist_ok=True)
    return d / "posture_alert.sqlite3"


class App:
    def __init__(self, qapp: QApplication, speed: float):
        self.qapp = qapp
        self.assets = assets_dir()
        self.exercises = load_exercises(self.assets / "exercises.json")
        self.scheduler = Scheduler.create(speed)
        self.monitor = get_monitor()
        self.repo = Repo(data_path())
        self.card = None

        self.tray = QSystemTrayIcon(QIcon(sprite(WARNING, WARNING_PAL, 2)))
        self.tray.setToolTip("바른자세 알리미")
        menu = QMenu()
        menu.addAction("지금 자세 체크", lambda: self.show(Kind.POSTURE))
        menu.addAction("지금 스트레칭", lambda: self.show(Kind.STRETCH))
        menu.addSeparator()
        menu.addAction("종료", qapp.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(5000 if speed == 1 else 1000)

    def on_tick(self):
        if self.card is not None:  # 이미 떠 있으면 겹쳐 띄우지 않음
            return
        kind = self.scheduler.tick(self.monitor.snapshot())
        if kind:
            self.show(kind)

    def show(self, kind: Kind, alt: bool = False):
        if self.card is not None:
            self.card.close()
        now = datetime.now()
        msg = message_for(kind, now, self.scheduler.sitting_minutes(now))
        ex = pick(self.exercises, "seated_alt" if alt else kind.value)
        if kind is Kind.EYE:
            card = LightToast(msg, ex)
        else:
            card = GuideCard(msg, ex, self.assets, can_defer_stand=(kind is Kind.STAND and not alt))
            card.want_alternative.connect(lambda: QTimer.singleShot(0, lambda: self.show(kind, alt=True)))
        card.answered.connect(lambda r: self.on_answer(kind, ex.id, r))
        self._seq = getattr(self, "_seq", 0) + 1
        seq = self._seq
        card.destroyed.connect(lambda *_: self._clear(seq))
        self.card = card
        card.show_bottom_right()

    def _clear(self, seq: int):
        # 대체 동작으로 바꿀 때 이전 카드가 늦게 사라져도 새 카드를 지우지 않게
        if seq == self._seq:
            self.card = None

    def on_answer(self, kind: Kind, exercise_id: str, result: str):
        self.repo.record(kind.value, exercise_id, result)
        if result == "snooze":
            QTimer.singleShot(5 * 60 * 1000, lambda: self.show(kind))


def main() -> None:
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    load_fonts(assets_dir())
    qapp.setStyleSheet(STYLESHEET)

    speed = 60.0 if os.environ.get("POSTURE_DEBUG") == "1" else 1.0
    app = App(qapp, speed)

    args = sys.argv[1:]
    if "--demo" in args:
        kind = Kind(args[args.index("--demo") + 1])
        app.show(kind)
    if "--shot" in args:
        out = args[args.index("--shot") + 1]
        QTimer.singleShot(300, lambda: (app.card.grab().save(out), qapp.quit()))

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
