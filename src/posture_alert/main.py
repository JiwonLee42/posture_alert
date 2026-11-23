"""진입점: 트레이 아이콘 + 타이머 + 단계 사이클 + 알림 창 연결.

실행:
    uv run posture-alert                     # 일반 모드
    POSTURE_DEBUG=1 uv run posture-alert     # 1분 = 1초 (20초마다 눈 알림 ...)
    uv run posture-alert --demo posture      # 바로 카드 띄우기 (eye/posture/stretch/stand/receipt 또는 단계 번호 1~8)
    POSTURE_EVERY=20 uv run posture-alert    # 단계 하나당 간격(분), 기본 20
    uv run posture-alert --shot out.png --demo posture   # 카드 스크린샷 저장 후 종료
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QPoint, QStandardPaths, QTimer
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .engine.billing import build_receipt
from .engine.content import (APP_NAME, APP_TAGLINE, ASSETS, Message, load_exercises,
                             message_for, pick)
from .engine.stages import STAGES, Stage, StageCycle
from .engine.uptime import UptimeCounter
from .engine.scheduler import Kind, Scheduler
from .platform import get_monitor
from .storage.repo import Repo
from .ui.popup import CHARACTERS, GhostError, GuideCard, LightToast, ReceiptWindow
from .ui.retro import ERROR_ICON, ERROR_PAL, STYLESHEET, load_fonts, sprite


def assets_dir() -> Path:
    # PyInstaller로 묶였을 때는 임시 폴더(_MEIPASS) 아래에 assets가 풀린다
    base = getattr(sys, "_MEIPASS", None)
    return Path(base) / "assets" if base else ASSETS


def data_path() -> Path:
    d = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    d.mkdir(parents=True, exist_ok=True)
    return d / "posture_alert.sqlite3"


IGNORED = {"skip", "snooze", "timeout"}
MAX_GHOSTS = 6
CYCLE_EVERY_MINUTES = float(os.environ.get("POSTURE_EVERY", "20"))  # 단계 하나당 간격


class App:
    def __init__(self, qapp: QApplication, speed: float, repo: Repo | None = None):
        self.qapp = qapp
        self.speed = speed
        self.assets = assets_dir()
        self.exercises = {e.id: e for e in load_exercises(self.assets / "exercises.json")}
        self.scheduler = Scheduler.for_cycle(CYCLE_EVERY_MINUTES, speed)
        self.monitor = get_monitor()
        self.repo = repo or Repo(data_path())
        self.card = None
        self.ghosts: list[GhostError] = []
        self.receipt_win = None
        self.ignored_streak = 0   # 연속으로 무시한 횟수 → 에러창이 그만큼 쌓인다
        self._seq = 0
        # 기본 캐릭터: POSTURE_CHARACTER=f|m 으로 고정, 없으면 알림마다 번갈아
        self.character_pref = os.environ.get("POSTURE_CHARACTER")
        self._char_i = 0

        # 켜둔 시간: 메모리 카운터 + 분이 바뀔 때만 sessions 행에 UPDATE
        self.session_id = self.repo.start_session()
        self.uptime = UptimeCounter()
        # 단계 사이클: 마지막 사이클 위치를 DB에서 복원해 이어서 돈다
        latest = self.repo.latest_cycle()
        self.cycle = StageCycle(*latest) if latest else StageCycle()

        self.tray = QSystemTrayIcon(QIcon(sprite(ERROR_ICON, ERROR_PAL, 2)))
        menu = QMenu()
        menu.addAction("오늘 견적서 보기", self.show_receipt)
        menu.addSeparator()
        menu.addAction("다음 단계 바로 하기", self.show_next)
        menu.addAction("일어나기", lambda: self.show_stage(Stage.STAND_WATER, interrupt=True))
        menu.addSeparator()
        menu.addAction("종료", qapp.quit)
        self.tray.setContextMenu(menu)
        self._update_tooltip()
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_tick)
        self.timer.start(5000 if speed == 1 else 1000)

        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.on_uptime)
        self.uptime_timer.start(10_000)
        qapp.aboutToQuit.connect(self.save_uptime)

    # --- 켜둔 시간 ---
    def on_uptime(self):
        if self.uptime.poll() is not None:
            self.save_uptime()

    def save_uptime(self):
        self.repo.save_uptime(self.session_id, self.uptime.minutes)
        self._update_tooltip()

    def _update_tooltip(self):
        self.tray.setToolTip(f"{APP_NAME} - {APP_TAGLINE}\n켜둔 지 {self.uptime.minutes}분")

    # --- 스케줄 ---
    def on_tick(self):
        was_sitting = self.scheduler.sitting_time(datetime.now())
        kind = self.scheduler.tick(self.monitor.snapshot())
        # 30분 이상 앉아 있다가 자리를 비웠으면 "일어남"으로 방어 처리
        if self.scheduler.sitting_since is None and was_sitting >= timedelta(minutes=30) / self.speed:
            self.repo.record(Kind.STAND.value, None, "away")
        if kind is None or self.card is not None:  # 이미 떠 있으면 겹쳐 띄우지 않음
            return
        if kind is Kind.STAND:
            self.show_stage(Stage.STAND_WATER, interrupt=True)  # 오래 앉았으면 끼어들기
        else:
            self.show_next()

    # --- 단계 사이클 ---
    def advance_cycle(self) -> Stage:
        had_empty_cycle = self.cycle.cycle_no and self.cycle.position is None
        stage, new_cycle = self.cycle.advance()
        if new_cycle and not had_empty_cycle:
            self.cycle.cycle_no = self.repo.new_cycle(self.session_id)
        self.repo.set_position(self.cycle.cycle_no, stage)
        return stage

    def show_next(self):
        self.show_stage(self.advance_cycle())

    @property
    def character(self) -> str:
        if self.character_pref in CHARACTERS:
            return self.character_pref
        self._char_i += 1
        return CHARACTERS[self._char_i % len(CHARACTERS)]

    def receipt(self):
        return build_receipt(self.repo.events_today())

    def show_stage(self, stage: Stage, interrupt: bool = False, alt: bool = False):
        if self.card is not None:
            self.card.close()
        if not self.cycle.cycle_no:  # 아직 사이클이 없으면 하나 만든다
            self.cycle.cycle_no = self.repo.new_cycle(self.session_id)
        info = STAGES[stage]
        kind = Kind(info.kind)
        now = datetime.now()
        if interrupt:  # 오래 앉아서 끼어든 일어나기: 앉아 있던 시간 멘트
            msg = message_for(Kind.STAND, now, self.scheduler.sitting_minutes(now))
        else:
            msg = Message(info.title, info.body)
        ex = pick(list(self.exercises.values()), "seated_alt") if alt else self.exercises[info.exercise_id]
        cycle_no = self.cycle.cycle_no
        cycle_info = (cycle_no, stage, self.repo.cycle_checks(cycle_no))

        if kind is Kind.EYE:
            card = LightToast(msg, ex)
        else:
            card = GuideCard(msg, ex, kind.value, self.assets, receipt=self.receipt(),
                             can_defer_stand=(kind is Kind.STAND and not alt),
                             character=self.character, cycle=cycle_info)
        # POST: 알림을 띄우는 순간 기록 생성 (result='shown', completed=0)
        event_id = self.repo.create_event(kind.value, ex.id, stage=stage, cycle_id=cycle_no)
        if kind is not Kind.EYE:
            card.want_alternative.connect(lambda: self._switch_to_alt(event_id, stage))
        card.answered.connect(lambda r: self.on_answer(event_id, cycle_no, stage, r))
        self._seq += 1
        seq = self._seq
        card.destroyed.connect(lambda *_: self._clear(seq))
        self.card = card

        # 무시할수록 에러창이 왼쪽 위로 겹겹이 쌓인다 (레퍼런스의 에러 폭탄 느낌)
        base = card.bottom_right()
        self._close_ghosts()
        n = min(self.ignored_streak, MAX_GHOSTS)
        for i in range(n, 0, -1):
            g = GhostError(i)
            g.show_at(base - QPoint(26 * i, 26 * i))
            self.ghosts.append(g)
        card.show_at(base)

    def _close_ghosts(self):
        for g in self.ghosts:
            try:
                g.close()
            except RuntimeError:  # 사용자가 이미 닫은 창
                pass
        self.ghosts.clear()

    def _clear(self, seq: int):
        # 대체 동작으로 바꿀 때 이전 카드가 늦게 사라져도 새 카드를 지우지 않게
        if seq == self._seq:
            self.card = None

    def _switch_to_alt(self, event_id: int, stage: Stage):
        self.repo.answer(event_id, "switched")
        QTimer.singleShot(0, lambda: self.show_stage(stage, interrupt=True, alt=True))

    def on_answer(self, event_id: int, cycle_no: int, stage: Stage, result: str):
        # PATCH: events 행 업데이트 (done이면 completed=1, completed_at 기록)
        self.repo.answer(event_id, result)
        if result == "done":
            # PATCH: 사이클 행의 stage_N 컬럼 = 1 (했음)
            self.repo.mark_stage_done(cycle_no, stage)
            self.ignored_streak = 0
            self._close_ghosts()
        elif result in IGNORED:
            self.ignored_streak += 1
        if result == "snooze":  # 같은 단계를 5분 뒤 다시 (사이클은 진행 안 함)
            QTimer.singleShot(int(5 * 60 * 1000 / self.speed), lambda: self.show_stage(stage))

    def show_receipt(self):
        if self.receipt_win is not None:
            try:
                self.receipt_win.close()
            except RuntimeError:
                pass
        self.save_uptime()
        self.receipt_win = ReceiptWindow(self.receipt(), uptime_minutes=self.repo.uptime_today())
        self.receipt_win.show_at(self.receipt_win.bottom_right())


def save_shot(app: "App", out: str) -> None:
    """떠 있는 창들(겹친 에러창 포함)을 한 장의 이미지로 저장 (데모·문서용)."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPainter, QPixmap
    wins = [w for w in [*app.ghosts, app.card, app.receipt_win] if w is not None and w.isVisible()]
    rect = QRect()
    for w in wins:
        rect = rect.united(w.frameGeometry())
    pm = QPixmap(rect.size())
    pm.fill(QColor("#008080"))  # Win95 바탕화면 청록색
    p = QPainter(pm)
    for w in wins:
        p.drawPixmap(w.pos() - rect.topLeft(), w.grab())
    p.end()
    pm.save(out)


def main() -> None:
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("posture-alert")  # DB 폴더 이름 고정
    qapp.setQuitOnLastWindowClosed(False)
    load_fonts(assets_dir())
    qapp.setStyleSheet(STYLESHEET)

    speed = 60.0 if os.environ.get("POSTURE_DEBUG") == "1" else 1.0
    app = App(qapp, speed)

    args = sys.argv[1:]
    if "--demo" in args:
        # 데모: 실제 기록을 건드리지 않게 메모리 DB + 예시 기록
        app.repo = Repo(":memory:")
        app.session_id = app.repo.start_session()
        app.uptime.started -= 137 * 60  # 2시간 17분 켜둔 것처럼
        for k, r in [("posture", "done")] * 4 + [("stretch", "done")] * 2 + \
                    [("stand", "away"), ("eye", "done"), ("stand", "skip"), ("posture", "snooze")]:
            app.repo.record(k, None, r)
        app.cycle = StageCycle(app.repo.new_cycle(app.session_id))
        if "--ghosts" in args:
            app.ignored_streak = int(args[args.index("--ghosts") + 1])
        target = args[args.index("--demo") + 1]
        demo_stage = {"eye": Stage.EYE_FAR, "posture": Stage.CHIN_TUCK,
                      "stretch": Stage.SCAPULA_SQUEEZE, "stand": Stage.STAND_WATER}
        if target == "receipt":
            app.show_receipt()
        else:
            stage = Stage(int(target)) if target.isdigit() else demo_stage[target]
            for done in Stage:  # 앞 단계들은 했다고 체크해 둔 상태로
                if done < stage:
                    app.repo.mark_stage_done(app.cycle.cycle_no, done)
            app.cycle.position = stage
            app.show_stage(stage, interrupt=(target == "stand"))
            if "--complete" in args:  # 완료 체크 화면 미리보기
                app.card._complete()
    if "--shot" in args:
        out = args[args.index("--shot") + 1]
        QTimer.singleShot(300, lambda: (save_shot(app, out), qapp.quit()))

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
