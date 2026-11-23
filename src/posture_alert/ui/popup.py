"""알림 창: Windows 95 대화상자 스타일의 가이드 카드."""
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QLinearGradient, QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from ..engine.content import Exercise, Message
from .retro import (BAD_POSE, BLUE, GOOD_POSE, NAVY, POSE_PAL, WARNING,
                    WARNING_PAL, retro_font, sprite)

IMG_SIZE = 128


class TitleBar(QWidget):
    closed = Signal()

    def __init__(self, title: str, parent: QWidget):
        super().__init__(parent)
        self.setFixedHeight(24)
        self._drag: QPoint | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 3, 2)
        label = QLabel(title)
        label.setObjectName("titleText")
        label.setFont(retro_font(13, bold=True))
        btn = QPushButton("×")
        btn.setObjectName("close")
        btn.setFixedSize(20, 18)
        btn.setFont(retro_font(13, bold=True))
        btn.clicked.connect(self.closed)
        lay.addWidget(label)
        lay.addStretch()
        lay.addWidget(btn)

    def paintEvent(self, _):
        p = QPainter(self)
        g = QLinearGradient(0, 0, self.width(), 0)
        g.setColorAt(0, QColor(NAVY))
        g.setColorAt(1, QColor(BLUE))
        p.fillRect(self.rect(), g)

    # 제목 표시줄을 잡고 창 끌기
    def mousePressEvent(self, e):
        self._drag = e.globalPosition().toPoint() - self.window().pos()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.window().move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None


def pose_image(assets: Path, exercise_id: str, which: str) -> QPixmap:
    """assets/img/{id}_{good|bad}.png 가 있으면 쓰고, 없으면 임시 픽셀 그림."""
    f = assets / "img" / f"{exercise_id}_{which}.png"
    if f.exists():
        return QPixmap(str(f)).scaled(IMG_SIZE, IMG_SIZE, Qt.AspectRatioMode.KeepAspectRatio,
                                      Qt.TransformationMode.FastTransformation)
    return sprite(GOOD_POSE if which == "good" else BAD_POSE, POSE_PAL, 9)


def image_panel(pm: QPixmap, caption: str) -> QWidget:
    box = QWidget()
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(4)
    frame = QFrame()
    frame.setObjectName("sunken")
    frame.setFixedSize(IMG_SIZE + 8, IMG_SIZE + 8)
    img = QLabel(frame)
    img.setPixmap(pm)
    img.setAlignment(Qt.AlignmentFlag.AlignCenter)
    img.setGeometry(4, 4, IMG_SIZE, IMG_SIZE)
    cap = QLabel(caption)
    cap.setObjectName("caption")
    cap.setFont(retro_font(12, bold=True))
    cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
    v.addWidget(frame)
    v.addWidget(cap)
    return box


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
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(10)
        self.root.addLayout(self.body)

    def show_bottom_right(self, offset: int = 0):
        self.adjustSize()
        geo = self.screen().availableGeometry()
        self.move(geo.right() - self.width() - 16 - offset,
                  geo.bottom() - self.height() - 16 - offset)
        self.show()


def _header(msg: Message) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(12)
    icon = QLabel()
    icon.setPixmap(sprite(WARNING, WARNING_PAL, 3))
    icon.setAlignment(Qt.AlignmentFlag.AlignTop)
    text = QVBoxLayout()
    t = QLabel(msg.title)
    t.setFont(retro_font(15, bold=True))
    b = QLabel(msg.body)
    b.setFont(retro_font(13))
    b.setWordWrap(True)
    text.addWidget(t)
    text.addWidget(b)
    row.addWidget(icon)
    row.addLayout(text, 1)
    return row


class GuideCard(_RetroWindow):
    """그림 + 단계 + 타이머 + '이 자세가 되었나요?' 확인."""
    answered = Signal(str)        # done / unsure / snooze / skip
    want_alternative = Signal()   # 일어나기 알림에서 "지금 못 일어나요"

    def __init__(self, msg: Message, ex: Exercise, assets: Path, can_defer_stand: bool = False):
        super().__init__(f"바른자세 알리미 - {ex.name}")
        self.ex = ex
        self.setFixedWidth(400)
        self.title_bar.closed.connect(lambda: self._answer("skip"))

        self.body.addLayout(_header(msg))

        imgs = QHBoxLayout()
        imgs.addStretch()
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "bad"), "✕ 지금"))
        imgs.addSpacing(12)
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "good"), "○ 이렇게"))
        imgs.addStretch()
        self.body.addLayout(imgs)

        self.steps = QLabel("\n".join(f"{i}. {s}" for i, s in enumerate(ex.steps, 1)))
        self.steps.setFont(retro_font(13))
        self.steps.setWordWrap(True)
        self.body.addWidget(self.steps)

        self.progress = QProgressBar()
        self.progress.setRange(0, ex.total_seconds)
        self.progress.setValue(0)
        self.timer_label = QLabel()
        self.timer_label.setFont(retro_font(12))
        prow = QHBoxLayout()
        prow.addWidget(self.progress, 1)
        prow.addWidget(self.timer_label)
        self.body.addLayout(prow)

        self.question = QLabel(f"{ex.check}  이 자세가 되었나요?")
        self.question.setFont(retro_font(13, bold=True))
        self.question.setWordWrap(True)
        self.body.addWidget(self.question)

        btns = QHBoxLayout()
        ok = QPushButton("네, 맞췄어요")
        ok.setObjectName("primary")
        ok.clicked.connect(lambda: self._answer("done"))
        if can_defer_stand:
            alt = QPushButton("지금 못 일어나요")
            alt.clicked.connect(self._alternative)
        else:
            alt = QPushButton("잘 모르겠어요")
            alt.clicked.connect(self._show_tip)
        later = QPushButton("5분 뒤")
        later.clicked.connect(lambda: self._answer("snooze"))
        for b in (ok, alt, later):
            b.setFont(retro_font(12))
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
        if self._elapsed >= self.ex.total_seconds:
            self._tick.stop()

    def _render_time(self):
        left = self.ex.total_seconds - self._elapsed
        self.timer_label.setText(f"{left // 60:02d}:{left % 60:02d}")

    def _show_tip(self):
        self.steps.setText("💡 " + (self.ex.tip or "거울이나 휴대폰 카메라로 옆모습을 확인해보세요."))
        self.answered.emit("unsure")

    def _alternative(self):
        self.want_alternative.emit()
        self.close()

    def _answer(self, result: str):
        self.answered.emit(result)
        self.close()


class LightToast(_RetroWindow):
    """눈 휴식처럼 가벼운 알림: 작게 띄우고 8초 뒤 저절로 닫힘."""
    answered = Signal(str)

    def __init__(self, msg: Message, ex: Exercise, auto_close_ms: int = 8000):
        super().__init__("바른자세 알리미")
        self.setFixedWidth(320)
        self.title_bar.closed.connect(lambda: self._answer("skip"))
        self.body.addLayout(_header(Message(msg.title, f"{msg.body}\n{ex.steps[0]}")))
        row = QHBoxLayout()
        row.addStretch()
        ok = QPushButton("확인")
        ok.setObjectName("primary")
        ok.setFont(retro_font(12))
        ok.clicked.connect(lambda: self._answer("done"))
        row.addWidget(ok)
        row.addStretch()
        self.body.addLayout(row)
        QTimer.singleShot(auto_close_ms, lambda: self._answer("timeout"))

    def _answer(self, result: str):
        if self.isVisible():
            self.answered.emit(result)
            self.close()
