"""알림 창: Windows 95 '응용 프로그램 오류' 대화상자 스타일.

- GuideCard  : 메인 알림 창 (큰 제목 + 남은 수술비 + ✕/○ 그림 + 버튼)
- Onboarding : 처음 실행 때 여자/남자 고르기 → 시작
- GhostError : 알림을 무시할수록 뒤에 겹겹이 쌓이는 에러창
- LightToast : 눈 휴식용 작은 경고창 (8초 뒤 자동으로 닫힘)
- ReceiptWindow : 오늘의 척추 견적서
"""
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QStackedWidget, QToolButton,
                               QVBoxLayout, QWidget)

from ..engine.billing import DISCLAIMER, SURGERY_COST, Receipt, price_of, won
from ..engine.content import APP_NAME, APP_TAGLINE, Exercise, Message
from .retro import (BAD_POSE, DARK, ERROR_ICON, ERROR_PAL, GOOD_POSE, NAVY,
                    POSE_PAL, WARNING, WARNING_PAL, retro_font, sprite)

# ---- 화면 조절용 설정값 (여기 숫자만 바꾸면 됨) ----
CARD_W = 420             # 알림 창 폭
TITLE_PX = 30            # 맨 위 "척추수술3000" 글자 크기
IMG_W, IMG_H = 176, 200  # 그림 칸 크기 (기본 그림 400:372, 스트레칭 그림 세로형도 들어가게)
BUTTON_W = 140           # 버튼 폭 (가운데 정렬, 모두 같은 폭)
BUTTON_W_3 = 118         # 버튼이 3개일 때(일어나기: 했어요/못 일어나요/나중에) 폭
BUTTON_GAP = 12          # 버튼 사이 간격
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


def _big_title(px: int = TITLE_PX) -> QLabel:
    lb = _label(APP_NAME, px, bold=True)
    lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lb


class AmountBar(QWidget):
    """남은 수술비: '남은 수술비 1,500만원' + 3,000만원 → 0원 진행 막대."""

    def __init__(self, remaining: int):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self.label = _label("", 16)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bar = QProgressBar()
        self.bar.setRange(0, SURGERY_COST)
        row = QHBoxLayout()
        row.addWidget(_label(won(SURGERY_COST), 11, color=DARK))
        row.addWidget(self.bar, 1)
        row.addWidget(_label("0원", 11, color=DARK))
        v.addWidget(self.label)
        v.addLayout(row)
        self.set(remaining)

    def set(self, remaining: int):
        self.label.setText(f"남은 수술비 <b style='color:#c00000'>{won(remaining)}</b>")
        self.bar.setValue(SURGERY_COST - remaining)


class GuideCard(_RetroWindow):
    """메인 알림 창: 큰 제목 + 남은 수술비 + ✕/○ 그림 + 동작 한 줄 + 버튼."""
    answered = Signal(str)        # done / snooze / skip
    want_alternative = Signal()   # 일어나기 알림에서 "못 일어나요"

    def __init__(self, ex: Exercise, kind: str, assets: Path, remaining: int,
                 character: str = "f", can_defer_stand: bool = False):
        super().__init__(f"{EXE} - 응용 프로그램 오류")
        self.ex = ex
        self.price = price_of(kind)
        self.remaining = remaining
        self.setFixedWidth(CARD_W)
        self.title_bar.closed.connect(lambda: self._answer("skip"))

        self.body.addWidget(_big_title())
        self.amount = AmountBar(remaining)
        self.body.addWidget(self.amount)

        imgs = QHBoxLayout()
        imgs.addStretch()
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "bad", character), "✕ 지금"))
        imgs.addSpacing(12)
        imgs.addWidget(image_panel(pose_image(assets, ex.id, "good", character), "○ 이렇게"))
        imgs.addStretch()
        self.body.addLayout(imgs)

        self.title = _label(ex.name, 16, bold=True)
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.question = _label(f"{ex.check}", 13)
        self.question.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.body.addWidget(self.title)
        self.body.addWidget(self.question)

        btns = QHBoxLayout()
        btns.setSpacing(BUTTON_GAP)
        ok = _button(f"했어요 (-{won(self.price)})", primary=True)
        ok.clicked.connect(self._complete)
        self.buttons = [ok]
        if can_defer_stand:
            alt = _button("못 일어나요")
            alt.clicked.connect(self._alternative)
            self.buttons.append(alt)
        later = _button("나중에")
        later.clicked.connect(lambda: self._answer("snooze"))
        self.buttons.append(later)
        # 가운데 정렬: 양옆에 빈 공간(stretch)을 넣고 버튼 폭은 고정
        btns.addStretch()
        width = BUTTON_W if len(self.buttons) <= 2 else BUTTON_W_3
        for b in self.buttons:
            b.setFixedWidth(width)
            btns.addWidget(b)
        btns.addStretch()
        self.body.addLayout(btns)

    def _complete(self):
        """'했어요' → 금액이 줄어든 모습을 1.6초 보여주고 닫힘."""
        if not self.isVisible():
            return
        self.answered.emit("done")
        left = max(0, self.remaining - self.price)
        self.amount.set(left)
        self.title.setText(f"✔ -{won(self.price)}!")
        self.title.setStyleSheet("color:#0b6b0b;")
        self.question.setText("0원이 될 때까지 계속해요" if left else "🎉 수술비 0원 달성!")
        for b in self.buttons:
            b.setEnabled(False)
        self.title_bar.closed.disconnect()
        self.title_bar.closed.connect(self.close)
        QTimer.singleShot(1600, self.close)

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
    """무시한 알림 수만큼 뒤에 쌓이는 장식용 에러창"""

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
    """눈 휴식처럼 가벼운 알림: 노란 경고창, 8초 뒤 저절로 닫힘"""
    answered = Signal(str)

    def __init__(self, ex: Exercise, remaining: int, auto_close_ms: int = 8000):
        super().__init__(f"{EXE}, 경고")
        self.setFixedWidth(320)
        self.title_bar.closed.connect(lambda: self._answer("skip"))
        self.body.addLayout(_error_header(
            Message(ex.name, f"{ex.steps[0]}\n남은 수술비 {won(remaining)}"),
            icon=WARNING, pal=WARNING_PAL))
        row = QHBoxLayout()
        row.addStretch()
        ok = _button(f"했어요 (-{won(price_of('eye'))})", primary=True)
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
    """오늘의 척추 견적서"""
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


class Onboarding(_RetroWindow):
    """처음 실행: ① 여자/남자 고르기 → ② '이제 시작할게요. 3,000만원 → 0원' → 시작."""
    finished = Signal(str)  # 고른 캐릭터 f / m

    def __init__(self, assets: Path):
        super().__init__(f"{APP_NAME} 설치")
        self.assets = assets
        self.setFixedWidth(420)
        self.title_bar.closed.connect(self.close)
        self.stack = QStackedWidget()
        self.stack.addWidget(self._pick_page())
        self.body.addWidget(self.stack)

    def center(self):
        self.fit()
        geo = self.screen().availableGeometry()
        self.move(geo.center() - self.rect().center())

    def _pick_page(self) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(12)
        v.addWidget(_big_title())
        ask = _label("캐릭터를 골라주세요", 15)
        ask.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(ask)
        row = QHBoxLayout()
        for ch, name in (("f", "여자"), ("m", "남자")):
            btn = QToolButton()
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIcon(QIcon(pose_image(self.assets, "", "good", ch)))
            btn.setIconSize(QSize(IMG_W, IMG_H))
            btn.setText(name)
            btn.setFont(retro_font(15))
            btn.clicked.connect(lambda _=False, c=ch: self._picked(c))
            row.addWidget(btn)
        v.addLayout(row)
        return page

    def _start_page(self, ch: str) -> QWidget:
        page = QWidget()
        v = QVBoxLayout(page)
        v.setSpacing(12)
        v.addWidget(_big_title())
        img = QLabel()
        img.setPixmap(pose_image(self.assets, "", "good", ch))
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(img)
        for text, px in (("이제 시작할게요.", 16),
                         (f"{won(SURGERY_COST)} → 0원을 목표로 할게요!", 18)):
            lb = _label(text, px, bold=True)
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(lb)
        row = QHBoxLayout()
        row.addStretch()
        go = _button("시작", primary=True)
        go.clicked.connect(lambda: (self.finished.emit(ch), self.close()))
        row.addWidget(go)
        row.addStretch()
        v.addLayout(row)
        return page

    def _picked(self, ch: str):
        self.stack.addWidget(self._start_page(ch))
        self.stack.setCurrentIndex(1)
        self.center()
