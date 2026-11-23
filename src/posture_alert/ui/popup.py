"""알림 창: Windows 95 '응용 프로그램 오류' 대화상자 스타일.

- GuideCard  : 메인 에러창 (그림 + 단계 + 타이머 + "이 자세가 되었나요?")
- GhostError : 알림을 무시할수록 뒤에 겹겹이 쌓이는 에러창
- LightToast : 눈 휴식용 작은 경고창 (8초 뒤 자동으로 닫힘)
- ReceiptWindow : 오늘의 척추 견적서
"""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from ..engine.billing import DISCLAIMER, Receipt, price_of, won
from ..engine.content import APP_NAME, APP_TAGLINE, Exercise, Message
from ..engine.stages import Stage
from .retro import (BAD_POSE, CHECK_ICON, CHECK_PAL, CHECKBOX_OFF, CHECKBOX_ON,
                    CHECKBOX_PAL, DARK, ERROR_ICON, ERROR_PAL, GOOD_POSE, NAVY,
                    POSE_PAL, WARNING, WARNING_PAL, retro_font, sprite)

IMG_W, IMG_H = 176, 200  # 그림 칸 크기 (기본 그림 400:372, 스트레칭 그림 세로형도 들어가게)
EXE = f"{APP_NAME}.exe"
ERROR_CODES = {
    "posture": "TURTLE_NECK_OVERFLOW",
    "stretch": "SHOULDER_LOCK_EXCEPTION",
    "stand": "SEAT_TIMEOUT_EXCEEDED",
}


class TitleBar(QWidget):
    closed = Signal()

    def __init__(self, title: str, parent: QWidget):
        super().__init__(parent)
        self.setFixedHeight(22)
        self._drag: QPoint | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 2, 2)
        label = QLabel(title)
        label.setObjectName("titleText")
        label.setFont(retro_font(12, bold=True))
        btn = QPushButton("×")
        btn.setObjectName("close")
        btn.setFixedSize(18, 16)
        btn.setFont(retro_font(12, bold=True))
        btn.clicked.connect(self.closed)
        lay.addWidget(label)
        lay.addStretch()
        lay.addWidget(btn)

    def paintEvent(self, _):
        QPainter(self).fillRect(self.rect(), QColor(NAVY))  # Win95: 단색 남색

    def mousePressEvent(self, e):
        self._drag = e.globalPosition().toPoint() - self.window().pos()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.window().move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None


class _RetroWindow(QWidget):
    """테두리 없는 항상 위 창 + 회색 Win95 프레임."""

    def __init__(self, title: str):
        super().__init__(None, Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # 포커스 안 뺏음
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("window")
        outer.addWidget(frame)
        self.root = QVBoxLayout(frame)
        self.root.setContentsMargins(3, 3, 3, 3)
        self.root.setSpacing(0)
        self.title_bar = TitleBar(title, self)
        self.root.addWidget(self.title_bar)
        self.body = QVBoxLayout()
        self.body.setContentsMargins(14, 14, 14, 12)
        self.body.setSpacing(10)
        self.root.addLayout(self.body)

    def fit(self):
        """줄바꿈되는 글자까지 포함한 실제 필요 높이로 창 크기를 맞춘다.
        (adjustSize 만 쓰면 줄바꿈 높이를 덜 잡아서 아래 내용이 겹침)"""
        self.adjustSize()
        lay = self.layout()
        need = lay.totalHeightForWidth(self.width()) if lay.hasHeightForWidth() else -1
        need = max(need, lay.totalMinimumSize().height(), self.height())
        self.resize(self.width(), need)

    def bottom_right(self, offset: int = 0) -> QPoint:
        self.fit()
        geo = self.screen().availableGeometry()
        return QPoint(geo.right() - self.width() - 16 - offset,
                      geo.bottom() - self.height() - 16 - offset)

    def show_at(self, pos: QPoint):
        self.fit()
        self.move(pos)
        self.show()


def _label(text: str, px: int = 13, bold: bool = False, color: str | None = None) -> QLabel:
    lb = QLabel(text)
    lb.setFont(retro_font(px, bold))
    lb.setWordWrap(True)
    if color:
        lb.setStyleSheet(f"color:{color};")
    return lb


class Header:
    """아이콘 + 제목 + 본문 + 오류 코드. 완료 시 아이콘·문구를 바꿀 수 있게 참조를 들고 있음."""

    def __init__(self, layout, icon, title, body):
        self.layout, self.icon, self.title, self.body = layout, icon, title, body


def _error_header(msg: Message, icon=ERROR_ICON, pal=ERROR_PAL, code: str = "") -> QHBoxLayout:
    return _header(msg, icon, pal, code).layout


def _header(msg: Message, icon=ERROR_ICON, pal=ERROR_PAL, code: str = "") -> Header:
    row = QHBoxLayout()
    row.setSpacing(14)
    icon_lb = QLabel()
    icon_lb.setPixmap(sprite(icon, pal, 3))
    icon_lb.setAlignment(Qt.AlignmentFlag.AlignTop)
    text = QVBoxLayout()
    text.setSpacing(4)
    title = _label(msg.title, 15, bold=True)
    body = _label(msg.body, 13)
    text.addWidget(title)
    text.addWidget(body)
    if code:
        text.addWidget(_label(code, 11, color=DARK))
    row.addWidget(icon_lb)
    row.addLayout(text, 1)
    return Header(row, icon_lb, title, body)


def _tagline() -> QWidget:
    """그림 위의 큰 타이틀: 기억하자 / 척추수술 3000만원 (레퍼런스 그림처럼 두 줄 가운데 정렬)."""
    first, _, second = APP_TAGLINE.partition(" ")
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 4, 0, 2)
    v.setSpacing(2)
    for text, px in ((first, 18), (second, 24)):
        lb = _label(text, px, bold=True)
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(lb)
    return box


def _cycle_strip(cycle_no: int, current: Stage, checks: dict[Stage, bool]) -> QWidget:
    """사이클 진행 표시: '사이클 #3 · 2/8단계' + 단계 1~8 체크박스 (지금 단계는 남색 번호)."""
    box = QWidget()
    row = QHBoxLayout(box)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    row.addWidget(_label(f"사이클 #{cycle_no} · {int(current)}/{len(Stage)}단계", 12))
    row.addStretch()
    for st in Stage:
        cell = QVBoxLayout()
        cell.setSpacing(1)
        cb = QLabel()
        cb.setPixmap(_checkbox(checks.get(st, False)))
        cb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb.setToolTip(st.name)
        num = _label(str(int(st)), 11, color=NAVY if st == current else DARK)
        num.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if st == current:
            num.setStyleSheet(f"color:{NAVY}; text-decoration: underline;")
        cell.addWidget(cb)
        cell.addWidget(num)
        row.addLayout(cell)
    return box


def _checkbox(on: bool) -> QPixmap:
    return sprite(CHECKBOX_ON if on else CHECKBOX_OFF, CHECKBOX_PAL, 2)


def _button(text: str, primary: bool = False) -> QPushButton:
    b = QPushButton(text)
    b.setFont(retro_font(12))
    if primary:
        b.setObjectName("primary")
    return b


CHARACTERS = ("f", "m")  # assets/img/default/{f|m}_{bad|good}.png


def pose_image(assets: Path, exercise_id: str, which: str, character: str = "f") -> QPixmap:
    """그림 고르는 순서:
    1) assets/img/{동작id}_{f|m}_{good|bad}.png (동작 + 캐릭터별 그림)
    2) assets/img/{동작id}_{good|bad}.png      (동작별 그림, 캐릭터 공통)
    3) assets/img/default/{f|m}_{good|bad}.png  (기본 캐릭터: 거북목 ✕ / 바른 자세 ○)
    4) 임시 픽셀 막대 인형
    """
    img = assets / "img"
    for f in (img / f"{exercise_id}_{character}_{which}.png",
              img / f"{exercise_id}_{which}.png",
              img / "default" / f"{character}_{which}.png"):
        if f.exists():
            return QPixmap(str(f)).scaled(IMG_W, IMG_H, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
    return sprite(GOOD_POSE if which == "good" else BAD_POSE, POSE_PAL, 9)


def image_panel(pm: QPixmap, caption: str) -> QWidget:
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(4)
    frame = QFrame()
    frame.setObjectName("sunken")
    frame.setFixedSize(IMG_W + 8, IMG_H + 8)
    fl = QVBoxLayout(frame)
    fl.setContentsMargins(4, 4, 4, 4)
    img = QLabel()
    img.setPixmap(pm)
    img.setAlignment(Qt.AlignmentFlag.AlignCenter)
    fl.addWidget(img)
    cap = _label(caption, 12, bold=True)
    cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cap.setMinimumHeight(18)
    v.addWidget(frame)
    v.addWidget(cap)
    box.setFixedHeight(IMG_H + 8 + 4 + 20)  # 그림 + 간격 + 캡션 (레이아웃이 줄이지 못하게)
    return box


class GuideCard(_RetroWindow):
    """메인 에러창."""
    answered = Signal(str)        # done / unsure / snooze / skip
    want_alternative = Signal()   # 일어나기 알림에서 "지금 못 일어나요"

    def __init__(self, msg: Message, ex: Exercise, kind: str, assets: Path,
                 receipt: Receipt | None = None, can_defer_stand: bool = False,
                 character: str = "f",
                 cycle: tuple[int, Stage, dict[Stage, bool]] | None = None):
        super().__init__(f"{EXE} - 응용 프로그램 오류")
        self.ex = ex
        self.setFixedWidth(440)
        self.title_bar.closed.connect(lambda: self._answer("skip"))

        price = price_of(kind)
        code = f"오류 코드 0x{price:05X} · {ERROR_CODES.get(kind, 'SPINE_ERROR')} · 청구 예정 {won(price)}"
        self.price = price
        self.header = _header(msg, code=code)
        self.body.addLayout(self.header.layout)

        self.body.addWidget(_tagline())
        self.cycle = cycle
        if cycle is not None:
            strip = _cycle_strip(*cycle)
            strip.setObjectName("cycleStrip")
            self.body.addWidget(strip)

        imgs = QHBoxLayout()
        imgs.addStretch()
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "bad", character), "✕ 지금"))
        imgs.addSpacing(12)
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "good", character), "○ 이렇게"))
        imgs.addStretch()
        self.body.addLayout(imgs)

        # 단계마다 Win95 체크박스: 타이머가 지나가면 하나씩 체크, 완료하면 전부 체크
        self.step_boxes: list[QLabel] = []
        steps_box = QVBoxLayout()
        steps_box.setSpacing(4)
        for i, text in enumerate(ex.steps, 1):
            row = QHBoxLayout()
            row.setSpacing(8)
            box = QLabel()
            box.setPixmap(_checkbox(False))
            box.setAlignment(Qt.AlignmentFlag.AlignTop)
            row.addWidget(box)
            row.addWidget(_label(f"{i}. {text}"), 1)
            steps_box.addLayout(row)
            self.step_boxes.append(box)
        self.steps = _label("")
        self.steps.hide()
        steps_box.addWidget(self.steps)
        self.body.addLayout(steps_box)

        self.progress = QProgressBar()
        self.progress.setRange(0, ex.total_seconds)
        self.progress.setValue(0)
        self.timer_label = _label("", 12)
        self.timer_label.setWordWrap(False)
        prow = QHBoxLayout()
        prow.addWidget(_label(f"{ex.name} 복구 중...", 12))
        prow.addWidget(self.progress, 1)
        prow.addWidget(self.timer_label)
        self.body.addLayout(prow)

        self.question = _label(f"{ex.check}  이 자세가 되었나요?", 13, bold=True)
        self.body.addWidget(self.question)

        if receipt is not None:
            self.body.addWidget(_label(
                f"오늘 방어 {won(receipt.saved_total)} · 청구 {won(receipt.billed_total)}",
                11, color=DARK))

        btns = QHBoxLayout()
        ok = _button(f"네, 맞췄어요 (+{won(price)})", primary=True)
        ok.clicked.connect(self._complete)
        if can_defer_stand:
            alt = _button("지금 못 일어나요")
            alt.clicked.connect(self._alternative)
        else:
            alt = _button("잘 모르겠어요")
            alt.clicked.connect(self._show_tip)
        later = _button("나중에 청구")
        later.clicked.connect(lambda: self._answer("snooze"))
        self.buttons = (ok, alt, later)
        for b in self.buttons:
            btns.addWidget(b)
        self.body.addLayout(btns)

        self._elapsed = 0
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(1000)
        self._render_time()

    def _on_tick(self):
        self._elapsed = min(self._elapsed + 1, self.ex.total_seconds)
        self.progress.setValue(self._elapsed)
        self._render_time()
        n = len(self.step_boxes)
        for i, box in enumerate(self.step_boxes):
            if self._elapsed >= self.ex.total_seconds * (i + 1) / n:
                box.setPixmap(_checkbox(True))
        if self._elapsed >= self.ex.total_seconds:
            self._tick.stop()

    def _render_time(self):
        left = self.ex.total_seconds - self._elapsed
        self.timer_label.setText(f"{left // 60:02d}:{left % 60:02d}")

    def _complete(self):
        """'네, 맞췄어요' → 완료 체크 화면을 1.6초 보여주고 닫힘."""
        if not self.isVisible():
            return
        self.answered.emit("done")
        self._tick.stop()
        self.progress.setValue(self.ex.total_seconds)
        self.timer_label.setText("완료")
        for box in self.step_boxes:
            box.setPixmap(_checkbox(True))
        if self.cycle is not None:  # 사이클 표시에도 이번 단계 체크
            no, cur, checks = self.cycle
            old = self.findChild(QWidget, "cycleStrip")
            new = _cycle_strip(no, cur, {**checks, cur: True})
            new.setObjectName("cycleStrip")
            if old is not None:
                old.parentWidget().layout().replaceWidget(old, new)
                old.deleteLater()
        self.header.icon.setPixmap(sprite(CHECK_ICON, CHECK_PAL, 3))
        self.header.title.setText("방어 완료!")
        self.header.body.setText(f"{self.ex.name} 완료로 기록했어요. 병원비 {won(self.price)}을 아꼈어요.")
        self.question.setText("✔ 오늘 기록에 체크했어요")
        self.question.setStyleSheet("color:#0b6b0b;")
        for b in self.buttons:
            b.setEnabled(False)
        self.title_bar.closed.disconnect()
        self.title_bar.closed.connect(self.close)
        QTimer.singleShot(1600, self.close)

    def _show_tip(self):
        self.steps.show()
        self.steps.setText("💡 " + (self.ex.tip or "거울이나 휴대폰 카메라로 옆모습을 확인해보세요."))
        self.answered.emit("unsure")

    def _alternative(self):
        self.want_alternative.emit()
        self.close()

    def _answer(self, result: str):
        self.answered.emit(result)
        self.close()


GHOST_LINES = [
    "거북목이 응답하지 않습니다.",
    "척추가 잘못된 작업을 수행하여 종료됩니다.",
    "목 디스크 공간이 부족합니다.",
    "어깨.dll 파일을 찾을 수 없습니다.",
    "허리가 예기치 않게 구부러졌습니다.",
    "치료비 한도를 초과했습니다.",
]


class GhostError(_RetroWindow):
    """무시한 알림 수만큼 뒤에 쌓이는 장식용 에러창."""

    def __init__(self, i: int):
        super().__init__(f"{EXE}")
        self.setFixedWidth(340)
        self.title_bar.closed.connect(self.close)
        self.body.addLayout(_error_header(Message("오류", GHOST_LINES[i % len(GHOST_LINES)])))
        row = QHBoxLayout()
        row.addStretch()
        ok = _button("확인")
        ok.clicked.connect(self.close)
        row.addWidget(ok)
        row.addStretch()
        self.body.addLayout(row)


class LightToast(_RetroWindow):
    """눈 휴식처럼 가벼운 알림: 노란 경고창, 8초 뒤 저절로 닫힘."""
    answered = Signal(str)

    def __init__(self, msg: Message, ex: Exercise, auto_close_ms: int = 8000):
        super().__init__(f"{EXE} - 경고")
        self.setFixedWidth(340)
        self.title_bar.closed.connect(lambda: self._answer("skip"))
        self.body.addLayout(_error_header(Message(msg.title, f"{msg.body}\n{ex.steps[0]}"),
                                          icon=WARNING, pal=WARNING_PAL))
        row = QHBoxLayout()
        row.addStretch()
        ok = _button("확인", primary=True)
        ok.clicked.connect(lambda: self._answer("done"))
        row.addWidget(ok)
        row.addStretch()
        self.body.addLayout(row)
        QTimer.singleShot(auto_close_ms, lambda: self._answer("timeout"))

    def _answer(self, result: str):
        if self.isVisible():
            self.answered.emit(result)
            self.close()


class ReceiptWindow(_RetroWindow):
    """오늘의 척추 견적서."""
    WIDTH = 30  # 영수증 한 줄 글자 수 (고정폭)

    def __init__(self, receipt: Receipt, now: datetime | None = None, uptime_minutes: int | None = None):
        super().__init__(f"{APP_NAME} 견적서.txt - 메모장")
        self.setFixedWidth(360)
        self.title_bar.closed.connect(self.close)
        paper = QFrame()
        paper.setObjectName("sunken")
        v = QVBoxLayout(paper)
        v.setContentsMargins(12, 10, 12, 10)
        text = QLabel(self._render(receipt, now or datetime.now(), uptime_minutes))
        mono = retro_font(13)
        mono.setFamilies(["Galmuri11", "D2Coding", "Menlo", "Consolas"])
        text.setFont(mono)
        text.setStyleSheet("color:black;")
        v.addWidget(text)
        self.body.addWidget(paper)
        self.body.addWidget(_label(DISCLAIMER, 11, color=DARK))
        row = QHBoxLayout()
        row.addStretch()
        ok = _button("확인", primary=True)
        ok.clicked.connect(self.close)
        row.addWidget(ok)
        row.addStretch()
        self.body.addLayout(row)

    @classmethod
    def _render(cls, r: Receipt, now: datetime, uptime_minutes: int | None = None) -> str:
        w = cls.WIDTH
        days = "월화수목금토일"
        out = [f"{APP_NAME} 견적서".center(w - 6), APP_TAGLINE.center(w - 8), f"{now:%Y-%m-%d} ({days[now.weekday()]}) {now:%H:%M}".center(w),
               "-" * w]
        if uptime_minutes is not None:
            h, m = divmod(uptime_minutes, 60)
            out += [f"오늘 켜둔 시간  {h}시간 {m}분" if h else f"오늘 켜둔 시간  {m}분", "-" * w]
        out += ["[방어 내역]"]
        out += [f"{l.name} x{l.count}  {won(l.amount)}" for l in r.saved] or ["  (없음)"]
        out += ["", "[청구 내역]"]
        out += [f"{l.name} x{l.count}  {won(l.amount)}" for l in r.billed] or ["  (없음)"]
        out += ["-" * w, f"방어 합계   {won(r.saved_total)}", f"청구 합계   {won(r.billed_total)}",
                "=" * w]
        sign = "+" if r.balance >= 0 else "-"
        out.append(f"오늘의 척추 수익 {sign}{won(abs(r.balance))}")
        chickens = r.balance // 20_000
        if chickens > 0:
            out.append(f"치킨 {chickens}마리 벌었습니다 🍗")
        elif r.balance < 0:
            out.append("정형외과 VIP 등급까지 한 걸음 🏥")
        return "\n".join(out)
