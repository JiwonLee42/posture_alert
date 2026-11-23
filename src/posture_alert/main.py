"""진입점: 트레이 아이콘 + 타이머 + 단계 사이클 + 알림 창 연결.

실행:
    uv run posture-alert                     # 일반 모드
    POSTURE_DEBUG=1 uv run posture-alert     # 1분 = 1초 (20초마다 다음 단계 ...)
    POSTURE_EVERY_SECONDS=3 uv run posture-alert   # 테스트: 3초마다 다음 단계
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

from .engine.billing import build_receipt, remaining
from .engine.content import APP_NAME, APP_TAGLINE, ASSETS, load_exercises, pick
from .engine.stages import STAGES, Stage, StageCycle
from .engine.uptime import UptimeCounter
from .engine.scheduler import Kind, Scheduler
from .platform import get_monitor
from .storage.repo import Repo
from .ui.popup import CHARACTERS, GhostError, GuideCard, LightToast, Onboarding, ReceiptWindow
from .ui.retro import ERROR_ICON, ERROR_PAL, STYLESHEET, load_fonts, retro_font, sprite


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
CYCLE_EVERY_MINUTES = float(os.environ.get("POSTURE_EVERY", "20"))  # 단계 하나당 간격(분)
# 테스트용: POSTURE_EVERY_SECONDS=3 이면 3초마다 다음 단계 (타이핑 중 대기도 끔)
TEST_EVERY_SECONDS = float(os.environ.get("POSTURE_EVERY_SECONDS", "0"))
# 종료할 때 DB 기록을 모두 지움 (POSTURE_KEEP_DATA=1 이면 남김)
RESET_ON_EXIT = os.environ.get("POSTURE_KEEP_DATA") != "1"


class App:
    def __init__(self, qapp: QApplication, speed: float, repo: Repo | None = None):
        self.qapp = qapp
        self.speed = speed
        self.assets = assets_dir()
        self.exercises = {e.id: e for e in load_exercises(self.assets / "exercises.json")}
        if TEST_EVERY_SECONDS:
            self.scheduler = Scheduler.for_cycle(TEST_EVERY_SECONDS / 60)
            self.scheduler.typing_grace_seconds = 0  # 마우스를 움직이고 있어도 바로 뜨게
        else:
            self.scheduler = Scheduler.for_cycle(CYCLE_EVERY_MINUTES, speed)
        self.monitor = get_monitor()
        self.repo = repo or Repo(data_path())
        self.card = None
        self.ghosts: list[GhostError] = []
        self.receipt_win = None
        self.ignored_streak = 0   # 연속으로 무시한 횟수 → 에러창이 그만큼 쌓인다
        self._seq = 0
        # 캐릭터: POSTURE_CHARACTER=f|m 이 있으면 그걸, 아니면 처음 실행 때 고른 값
        self.character_pref = os.environ.get("POSTURE_CHARACTER")
        self.onboarding = None
        # 닫힌 창은 Qt 가 실제로 지울 때(destroyed)까지 붙잡아 둔다.
        # 닫자마자 Python 참조를 끊으면 Python 이 먼저 지워서 크래시 ("shared QObject was deleted directly")
        self._alive: set = set()

        # 켜둔 시간: 메모리 카운터 + 분이 바뀔 때만 sessions 행에 UPDATE
        self.session_id = self.repo.start_session()
        self.uptime = UptimeCounter()
        # 단계 사이클: 마지막 사이클 위치를 DB에서 복원해 이어서 돈다
        latest = self.repo.latest_cycle()
        self.cycle = StageCycle(*latest) if latest else StageCycle()

        self.tray = QSystemTrayIcon(QIcon(sprite(ERROR_ICON, ERROR_PAL, 2)))
        # 메뉴는 self 에 붙잡아 둬야 함: 지역 변수면 __init__ 이 끝날 때 Python 이 지워서
        # 트레이 메뉴가 사라지거나 종료 시 크래시 ("shared QObject was deleted directly")
        self.menu = menu = QMenu()
        menu.addAction("오늘 견적서 보기", self.show_receipt)
        menu.addSeparator()
        menu.addAction("다음 단계 바로 하기", self.show_next)
        menu.addAction("일어나기", lambda: self.show_stage(Stage.STAND_WATER, interrupt=True))
        menu.addSeparator()
        menu.addAction("종료", qapp.quit)
        self.tray.setContextMenu(self.menu)
        self._update_tooltip()
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.on_tick)
        # 몇 초마다 "띄울 때 됐나?" 확인할지: 평소 5초, 빠른 모드 1초, 초 단위 테스트 0.5초
        self.timer.start(500 if TEST_EVERY_SECONDS else 5000 if speed == 1 else 1000)

        self.uptime_timer = QTimer()
        self.uptime_timer.timeout.connect(self.on_uptime)
        self.uptime_timer.start(10_000)
        qapp.aboutToQuit.connect(self.on_quit)

        if not self.started:
            QTimer.singleShot(0, self.show_onboarding)

    # --- 켜둔 시간 ---
    def on_uptime(self):
        if self.uptime.poll() is not None:
            self.save_uptime()

    def on_quit(self):
        self.shutdown()
        if RESET_ON_EXIT:
            self.repo.reset()

    def shutdown(self):
        """타이머·창·트레이 정리 (종료 시, 테스트 정리용)."""
        self.save_uptime()
        self.timer.stop()
        self.uptime_timer.stop()
        if self.card is not None:
            self.card.close()
        self._close_ghosts()
        if self.onboarding is not None:
            self.onboarding.close()
        self.tray.hide()
        self.tray.setContextMenu(None)

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
        if kind is None or self.card is not None or not self.started:  # 시작 전·이미 떠 있으면 안 띄움
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
        return self.repo.get_setting("character", "f")

    @property
    def started(self) -> bool:
        return self.repo.get_setting("character") is not None

    def remaining(self) -> int:
        """시작한 뒤의 기록으로 계산한 남은 수술비 (3,000만원 → 0원)."""
        return remaining(self.repo.events_since(self.repo.get_setting("started_at")))

    # --- 처음 실행: 캐릭터 고르기 → 시작 ---
    def _retain(self, w):
        self._alive.add(w)
        w.destroyed.connect(lambda *_, w=w: self._alive.discard(w))
        return w

    def show_onboarding(self):
        if self.started or self.onboarding is not None:  # 그 사이 이미 시작했으면 안 띄움
            return
        self.onboarding = self._retain(Onboarding(self.assets))
        self.onboarding.finished.connect(self._on_started)
        self.onboarding.center()
        self.onboarding.show()

    def _on_started(self, character: str):
        self.repo.set_setting("character", character)
        self.repo.set_setting("started_at", datetime.now().isoformat(timespec="seconds"))
        if self.onboarding is not None:
            self.onboarding.close()  # _alive 가 붙잡고 있다가 destroyed 때 놓음
        self.onboarding = None

    def receipt(self):
        return build_receipt(self.repo.events_today())

    def show_stage(self, stage: Stage, interrupt: bool = False, alt: bool = False):
        if self.card is not None:
            self.card.close()
        if not self.cycle.cycle_no:  # 아직 사이클이 없으면 하나 만든다
            self.cycle.cycle_no = self.repo.new_cycle(self.session_id)
        info = STAGES[stage]
        kind = Kind(info.kind)
        ex = pick(list(self.exercises.values()), "seated_alt") if alt else self.exercises[info.exercise_id]
        cycle_no = self.cycle.cycle_no
        left = self.remaining()

        if kind is Kind.EYE:
            card = LightToast(ex, left)
        else:
            card = GuideCard(ex, kind.value, self.assets, left, character=self.character,
                             can_defer_stand=(kind is Kind.STAND and not alt))
        # POST: 알림을 띄우는 순간 기록 생성 (result='shown', completed=0)
        event_id = self.repo.create_event(kind.value, ex.id, stage=stage, cycle_id=cycle_no)
        if kind is not Kind.EYE:
            card.want_alternative.connect(lambda: self._switch_to_alt(event_id, stage))
        card.answered.connect(lambda r: self.on_answer(event_id, cycle_no, stage, r))
        self._seq += 1
        seq = self._seq
        card.destroyed.connect(lambda *_: self._clear(seq))
        self.card = self._retain(card)

        # 무시할수록 에러창이 왼쪽 위로 겹겹이 쌓인다 (레퍼런스의 에러 폭탄 느낌)
        base = card.bottom_right()
        self._close_ghosts()
        n = min(self.ignored_streak, MAX_GHOSTS)
        for i in range(n, 0, -1):
            g = self._retain(GhostError(i))
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
        self.receipt_win = self._retain(ReceiptWindow(self.receipt(), uptime_minutes=self.repo.uptime_today()))
        self.receipt_win.show_at(self.receipt_win.bottom_right())


def save_shot(app: "App", out: str) -> None:
    """떠 있는 창들(겹친 에러창 포함)을 한 장의 이미지로 저장 (데모·문서용)."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QPainter, QPixmap
    wins = [w for w in [*app.ghosts, app.card, app.receipt_win, app.onboarding]
            if w is not None and w.isVisible()]
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
    qapp.setFont(retro_font(12))  # 따로 지정 안 한 글자도 설치된 폰트로 (기본 "Sans Serif" 찾느라 느려지는 것 방지)
    qapp.setStyleSheet(STYLESHEET)

    speed = 60.0 if os.environ.get("POSTURE_DEBUG") == "1" else 1.0
    args = sys.argv[1:]
    # 데모: 실제 기록을 건드리지 않게 처음부터 메모리 DB 사용
    app = App(qapp, speed, repo=Repo(":memory:") if "--demo" in args else None)

    if "--demo" in args:
        target = args[args.index("--demo") + 1]
        app.uptime.started -= 137 * 60  # 2시간 17분 켜둔 것처럼
        if target != "onboarding":
            # 시작한 상태 + 수술비 1,500만원 남은 상태로 (거북목 교정 15번 = -1,500만원)
            app.repo.set_setting("character", app.character_pref or "f")
            app.repo.set_setting("started_at", "2000-01-01T00:00:00")
            for _ in range(15):
                app.repo.record("posture", None, "done")
        app.cycle = StageCycle(app.repo.new_cycle(app.session_id))
        if "--ghosts" in args:
            app.ignored_streak = int(args[args.index("--ghosts") + 1])
        demo_stage = {"eye": Stage.EYE_FAR, "posture": Stage.CHIN_TUCK,
                      "stretch": Stage.SCAPULA_SQUEEZE, "stand": Stage.STAND_WATER}
        if target == "onboarding":
            if "--pick" in args:  # 두 번째 화면(시작할게요)까지 넘긴 상태
                QTimer.singleShot(0, lambda: app.onboarding._picked(args[args.index("--pick") + 1]))
        elif target == "receipt":
            app.show_receipt()
        else:
            stage = Stage(int(target)) if target.isdigit() else demo_stage[target]
            app.cycle.position = stage
            app.show_stage(stage, interrupt=(target == "stand"))
            if "--complete" in args:  # 했어요 누른 화면 미리보기
                app.card._complete()
    if "--shot" in args:
        out = args[args.index("--shot") + 1]
        QTimer.singleShot(400, lambda: (save_shot(app, out), qapp.quit()))

    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
