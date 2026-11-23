"""Windows 95 스타일 공통 요소: 색, 폰트, 스타일시트, 픽셀 스프라이트."""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPainter, QPixmap

GRAY = "#c0c0c0"
DARK = "#808080"
WHITE = "#ffffff"
BLACK = "#000000"
NAVY = "#000080"
BLUE = "#1084d0"

# assets/fonts 에 Galmuri11.ttf 등 픽셀 폰트를 넣으면 자동으로 쓴다
FONT_FAMILIES = ["Galmuri11", "DungGeunMo", "Malgun Gothic", "Apple SD Gothic Neo"]


def load_fonts(assets: Path) -> None:
    for f in (assets / "fonts").glob("*.[ot]tf"):
        QFontDatabase.addApplicationFont(str(f))


def retro_font(px: int = 12, bold: bool = False) -> QFont:
    f = QFont()
    f.setFamilies(FONT_FAMILIES)
    f.setPixelSize(px)
    f.setBold(bold)
    f.setStyleStrategy(QFont.StyleStrategy.NoAntialias)
    return f


def _raised(w=2):
    return (f"border-top:{w}px solid {WHITE}; border-left:{w}px solid {WHITE};"
            f"border-bottom:{w}px solid {BLACK}; border-right:{w}px solid {BLACK};")


def _sunken(w=2):
    return (f"border-top:{w}px solid {DARK}; border-left:{w}px solid {DARK};"
            f"border-bottom:{w}px solid {WHITE}; border-right:{w}px solid {WHITE};")


STYLESHEET = f"""
QFrame#window {{ background:{GRAY}; {_raised()} }}
QLabel {{ color:{BLACK}; background:transparent; }}
QLabel#titleText {{ color:{WHITE}; }}
QLabel#caption {{ color:{BLACK}; }}
QPushButton {{
    background:{GRAY}; color:{BLACK}; {_raised()}
    padding:5px 12px; min-width:64px;
}}
QPushButton:pressed {{
    border-top:2px solid {BLACK}; border-left:2px solid {BLACK};
    border-bottom:2px solid {WHITE}; border-right:2px solid {WHITE};
}}
QPushButton#primary {{ border:3px solid {BLACK}; }}
QPushButton#close {{ min-width:0; padding:0; font-weight:bold; }}
QFrame#sunken {{ background:{WHITE}; {_sunken()} }}
QProgressBar {{
    background:{WHITE}; {_sunken()} min-height:18px; max-height:18px;
    color:transparent;
}}
QProgressBar::chunk {{ background:{NAVY}; width:8px; margin:2px 1px; }}
"""


def sprite(rows: list[str], palette: dict[str, str], scale: int) -> QPixmap:
    """문자열 격자를 픽셀 그림으로 그린다. 공백은 투명."""
    h, w = len(rows), max(len(r) for r in rows)
    pm = QPixmap(w * scale, h * scale)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != " ":
                p.fillRect(x * scale, y * scale, scale, scale, QColor(palette[ch]))
    p.end()
    return pm


WARNING = [
    "       KK       ",
    "      KWYK      ",
    "      KYYK      ",
    "     KWDDYK     ",
    "     KYDDOK     ",
    "    KWYDDYOK    ",
    "    KYYDDYOK    ",
    "   KWYYDDYOOK   ",
    "   KYYYDDYYOK   ",
    "  KWYYYYYYYOOK  ",
    "  KYYYYDDYYOOK  ",
    " KYYYYYDDYYYOOK ",
    " KOOOOOOOOOOOOK ",
    "KKKKKKKKKKKKKKKK",
]
WARNING_PAL = {"K": "#111111", "Y": "#f2e626", "O": "#e8b923", "W": "#fff7b0", "D": "#2b2b2b"}

# 임시 자세 그림 (옆모습). 생성한 픽셀 이미지로 교체될 자리
GOOD_POSE = [
    "      KKK     ",
    "     KSSSK    ",
    "     KSSSE    ",
    "     KSSSK    ",
    "      KKK     ",
    "       N      ",
    "     BBBBB    ",
    "     BBBBB    ",
    "     BBBBB    ",
    "     BBBBB    ",
    "     PPPPPPP  ",
    "     PPPPPPP  ",
    "           P  ",
    "           P  ",
]
BAD_POSE = [
    "              ",
    "              ",
    "          KKK ",
    "         KSSSK",
    "         KSSSE",
    "        NKSSSK",
    "      BB  KKK ",
    "     BBBB     ",
    "     BBBBB    ",
    "     BBBBB    ",
    "     PPPPPPP  ",
    "     PPPPPPP  ",
    "           P  ",
    "           P  ",
]
POSE_PAL = {"K": "#3a2a1a", "S": "#f5c9a0", "E": "#222222", "N": "#f5c9a0",
            "B": "#3b6fd8", "P": "#404040"}
