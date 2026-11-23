# 개발 가이드 — 척추수술3000 (Windows exe)

> 대상: 백엔드 개발자, Mac에서 개발하고 Windows용 exe로 배포
> 결론: **Python + PySide6 + PyInstaller**로 만듭니다.

---

## 1. 왜 PySide6인가? (PyQt를 써야 하나요?)

네, Qt 계열이 맞습니다. 다만 **PyQt 대신 PySide6**를 추천합니다.

| 선택지 | 장점 | 단점 | 판단 |
|---|---|---|---|
| **PySide6** (Qt 공식 Python 바인딩) | 트레이, 항상 위 창, SVG, 애니메이션 다 됨. **LGPL**이라 상업 배포도 부담 적음 | exe 용량 큼(60~100MB) | ✅ **추천** |
| PyQt6 | PySide6와 기능 거의 같음 | **GPL** — 소스 공개하거나 상업 라이선스를 사야 함 | PySide6로 대체 |
| Tkinter | 기본 내장 | 생김새가 낡고, 그림·투명 창 다루기 불편 | ❌ |
| Tauri (Rust + React) | 가볍고 예쁨 | Rust + 프론트엔드를 둘 다 배워야 함 | 나중에 고려 |
| C# WPF / WinUI | Windows에 가장 자연스러움 | **Mac에서 개발 불가** | ❌ (Mac 사용 중) |

PySide6와 PyQt는 코드가 거의 같습니다. `from PyQt6...`를 `from PySide6...`로 바꾸면 대부분 돌아가서, PyQt 예제를 찾아봐도 그대로 참고할 수 있습니다.

### 백엔드 개발자 관점에서 보는 구조
이 앱은 **"UI가 붙은 작은 백엔드 서비스"**입니다.

| 백엔드 개념 | 이 앱에서 |
|---|---|
| 스케줄러 / 크론 | 알림 엔진 (언제 무슨 알림을 띄울지 결정) |
| 이벤트 루프 | Qt 이벤트 루프 (`QTimer`가 5초마다 엔진을 호출) |
| 외부 연동 어댑터 | Windows API 호출부 (자리 비움, 전체 화면, 마이크 사용 여부) |
| Repository | SQLite 저장소 |
| View / Controller | 트레이 메뉴, 알림 팝업, 설정 창 |

**핵심 로직(엔진)은 Qt·Windows를 전혀 모르게** 만들면 Mac에서 pytest로 전부 테스트할 수 있습니다. 평소 하던 대로 "도메인 로직과 인프라 분리"를 하면 됩니다.

---

## 2. 개발 환경

### 2.1 Mac에서 할 일 (개발 대부분)
```bash
brew install uv
```
```bash
cd ~/Documents/coding_projects/posture-alert
```
```bash
uv init --python 3.12
```
```bash
uv add pyside6
```
```bash
uv add --dev pytest pyinstaller
```

PySide6는 Mac에서도 돌아가서 **팝업 UI와 엔진은 Mac에서 바로 띄워보며 개발**할 수 있습니다.

### 2.2 Windows가 꼭 필요한 일
- **exe 빌드**: PyInstaller는 크로스 컴파일이 안 됩니다. Windows exe는 Windows에서 빌드해야 합니다.
- **Windows 전용 기능 테스트**: 자리 비움 감지, 전체 화면 감지, 마이크 사용 감지, 자동 실행

방법은 두 가지입니다 (둘 다 쓰는 것을 추천합니다).
1. **GitHub Actions `windows-latest` 러너** — push하면 exe를 자동으로 빌드 (무료)
2. **Windows 실행 환경** — 회사 Windows PC, 또는 Mac에 Parallels / UTM + Windows 11 ARM

---

## 3. 프로젝트 구조

```
posture-alert/
├── pyproject.toml
├── src/posture_alert/
│   ├── main.py                 # 진입점: QApplication, 트레이, 타이머 연결
│   ├── engine/                 # ⭐ 순수 로직 (Qt·Windows 의존 없음)
│   │   ├── models.py           # Reminder, Exercise, 상태 dataclass
│   │   ├── scheduler.py        # 다음 알림 결정 (연속 착석, 겹침 방지, 단계별 강도)
│   │   └── messages.py         # 존댓말 문구, 시간대별 문구
│   ├── platform/               # 외부 연동 어댑터
│   │   ├── base.py             # ActivityMonitor 인터페이스 (Protocol)
│   │   ├── windows.py          # ctypes / winreg로 실제 구현
│   │   └── fake.py             # Mac 개발·테스트용 가짜 구현
│   ├── storage/
│   │   └── repo.py             # sqlite3: 완료 기록, 일어난 횟수, 설정
│   ├── ui/
│   │   ├── tray.py             # 트레이 아이콘 + 메뉴
│   │   ├── popup.py            # 가이드 카드 (그림, 단계, 타이머, 버튼)
│   │   └── settings.py         # 설정 창
│   └── assets/
│       ├── exercises.json      # 동작 정의 (이름, 단계, 체크 질문, 그림 파일)
│       └── img/                # chin_tuck_bad.svg, chin_tuck_good.svg ...
├── tests/
│   └── test_scheduler.py
├── installer/
│   └── setup.iss               # Inno Setup 설치 파일 스크립트
└── .github/workflows/build.yml # Windows exe 자동 빌드
```

---

## 4. 핵심 코드 뼈대

### 4.1 엔진 — 시계를 주입해서 테스트 가능하게

```python
# engine/scheduler.py
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

class Kind(Enum):
    EYE = "eye"          # 20분
    POSTURE = "posture"  # 30분
    STRETCH = "stretch"  # 60분
    STAND = "stand"      # 연속 착석 90분~

PRIORITY = [Kind.STAND, Kind.STRETCH, Kind.POSTURE, Kind.EYE]  # 겹치면 큰 것 하나만

@dataclass
class Snapshot:
    """플랫폼 어댑터가 매 tick마다 넘겨주는 현재 상태"""
    now: datetime
    idle_seconds: float
    fullscreen_or_dnd: bool
    in_meeting: bool

@dataclass
class Scheduler:
    intervals: dict[Kind, timedelta]
    away_threshold: timedelta = timedelta(minutes=3)
    last_fired: dict[Kind, datetime] = field(default_factory=dict)
    sitting_since: datetime | None = None
    deferred: bool = False

    def tick(self, s: Snapshot) -> Kind | None:
        # 1) 자리 비움 → "일어남"으로 인정하고 모든 타이머 초기화
        if s.idle_seconds >= self.away_threshold.total_seconds():
            self.sitting_since = None
            self.last_fired = {k: s.now for k in Kind}
            return None
        if self.sitting_since is None:
            self.sitting_since = s.now

        # 2) 회의·전체 화면 중이면 보류만 표시하고 띄우지 않음
        if s.in_meeting or s.fullscreen_or_dnd:
            self.deferred = True
            return None

        # 3) 타이핑 중이면 입력이 10초 멈출 때까지 기다림
        if s.idle_seconds < 10:
            return None

        # 4) 기한이 지난 알림 중 우선순위가 가장 높은 것 하나만
        due = [k for k in PRIORITY if self._is_due(k, s.now)]
        if not due:
            return None
        kind = due[0]
        for k in Kind:  # 겹친 작은 알림은 같이 처리한 것으로
            if PRIORITY.index(k) >= PRIORITY.index(kind):
                self.last_fired[k] = s.now
        self.deferred = False
        return kind

    def sitting_minutes(self, now: datetime) -> int:
        return 0 if self.sitting_since is None else int((now - self.sitting_since).total_seconds() // 60)

    def _is_due(self, k: Kind, now: datetime) -> bool:
        if k is Kind.STAND:
            return self.sitting_minutes(now) >= self.intervals[k].total_seconds() // 60 \
                and now - self.last_fired.get(k, self.sitting_since) >= timedelta(minutes=30)
        last = self.last_fired.get(k, self.sitting_since)
        return now - last >= self.intervals[k]
```

> 위 코드는 구조를 보여주는 뼈대입니다. 회의 후 묶음 알림, 150분 이후 강도 고정 같은 PRD 2.5 규칙은 테스트를 먼저 쓰고 하나씩 붙여가세요.

### 4.2 테스트 — Mac에서 바로 실행

```python
# tests/test_scheduler.py
from datetime import datetime, timedelta
from posture_alert.engine.scheduler import Scheduler, Snapshot, Kind

T0 = datetime(2026, 11, 24, 9, 0)
M = lambda n: timedelta(minutes=n)

def make():
    return Scheduler(intervals={Kind.EYE: M(20), Kind.POSTURE: M(30),
                                Kind.STRETCH: M(60), Kind.STAND: M(90)})

def snap(minutes, idle=15, fs=False, meeting=False):
    return Snapshot(T0 + M(minutes), idle, fs, meeting)

def test_자리비움이면_착석시간_초기화():
    s = make(); s.tick(snap(0)); s.tick(snap(50))
    s.tick(snap(55, idle=300))
    assert s.sitting_minutes(T0 + M(55)) == 0

def test_회의중엔_안띄운다():
    s = make(); s.tick(snap(0))
    assert s.tick(snap(30, meeting=True)) is None
    assert s.deferred

def test_60분엔_스트레칭_하나만():
    s = make(); s.tick(snap(0))
    assert s.tick(snap(60)) is Kind.STRETCH
```
```bash
uv run pytest
```

### 4.3 Windows 어댑터 — ctypes로 Windows API 호출

```python
# platform/windows.py
import ctypes, winreg
from ctypes import wintypes

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

def idle_seconds() -> float:
    info = LASTINPUTINFO(cbSize=ctypes.sizeof(LASTINPUTINFO))
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info))
    return (ctypes.windll.kernel32.GetTickCount() - info.dwTime) / 1000

def fullscreen_or_dnd() -> bool:
    # QUNS_ACCEPTS_NOTIFICATIONS(5)가 아니면 발표·전체 화면·방해 금지 등
    state = ctypes.c_int()
    ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state))
    return state.value != 5

def mic_in_use() -> bool:
    # 앱이 마이크를 쓰는 중이면 LastUsedTimeStop == 0
    base = r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\microphone"
    def scan(path):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, i); i += 1
                    except OSError:
                        return False
                    with winreg.OpenKey(key, sub) as k:
                        try:
                            if winreg.QueryValueEx(k, "LastUsedTimeStop")[0] == 0:
                                return True
                        except FileNotFoundError:
                            if scan(path + "\\" + sub):  # NonPackaged 하위 키
                                return True
        except OSError:
            return False
    return scan(base)
```

Mac에서 개발할 때는 `platform/fake.py`에 같은 함수 이름으로 가짜 값을 반환하게 하고, `main.py`에서 `sys.platform == "win32"`인지에 따라 골라 씁니다.

### 4.4 UI — 트레이 + 타이머 + 가이드 카드

```python
# main.py (요약)
import sys
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)          # 창을 닫아도 트레이에 남음

tray = QSystemTrayIcon(QIcon("assets/icon.png"))
menu = QMenu(); menu.addAction("지금 자세 체크"); menu.addAction("종료", app.quit)
tray.setContextMenu(menu); tray.show()

def on_tick():
    kind = scheduler.tick(monitor.snapshot())
    if kind:
        show_popup(kind)                       # ui/popup.py

timer = QTimer(); timer.timeout.connect(on_tick); timer.start(5_000)  # 5초마다
sys.exit(app.exec())
```

```python
# ui/popup.py 의 핵심 설정
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget
from PySide6.QtSvgWidgets import QSvgWidget

class GuideCard(QWidget):
    def __init__(self, exercise):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_ShowWithoutActivating)   # 타이핑 중인 창의 포커스를 뺏지 않음
        self.setFixedSize(360, 480)
        # 위: 나쁜 자세 / 좋은 자세 SVG 2장 (QSvgWidget)
        # 가운데: 단계 설명 QLabel, 타이머 QTimer
        # 아래: [네, 맞췄어요 ✓] [잘 모르겠어요] [5분 뒤]
        geo = self.screen().availableGeometry()
        self.move(geo.right() - 380, geo.bottom() - 500)  # 오른쪽 아래
```

- 창 하나로 토스트(작게)와 가이드 카드(크게)를 모두 처리하면, Windows 알림 센터 설정과 상관없이 똑같이 보입니다.
- 움직이는 그림은 GIF(`QMovie`)나 SVG 여러 장을 순서대로 바꿔 보여주는 방식이 가장 쉽습니다.

---

## 5. exe 만들기

### 5.1 PyInstaller (Windows에서 실행)
```bash
uv run pyinstaller --name posture-alert --windowed --icon assets/icon.ico --add-data "src/posture_alert/assets;assets" src/posture_alert/main.py
```
- `--windowed`: 검은 콘솔 창이 뜨지 않게 합니다.
- `--onefile`보다 **기본(onedir) + 설치 파일** 조합을 추천합니다. onefile은 실행이 느리고 백신이 오탐하는 경우가 많습니다.
- 에셋 경로는 실행 중에 `sys._MEIPASS`(PyInstaller 임시 경로)를 기준으로 찾아야 합니다.

### 5.2 설치 파일 — Inno Setup
`dist/posture-alert/` 폴더를 `척추수술3000-Setup.exe` 하나로 묶습니다. 시작 메뉴 바로가기와 제거 기능도 같이 생깁니다.

### 5.3 GitHub Actions로 자동 빌드
```yaml
# .github/workflows/build.yml
name: build-windows
on: [push]
jobs:
  build:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - run: uv sync
      - run: uv run pytest
      - run: uv run pyinstaller --name mokpyeo --windowed --add-data "src/posture_alert/assets;assets" src/posture_alert/main.py
      - uses: actions/upload-artifact@v4
        with: { name: mokpyeo-windows, path: dist/mokpyeo }
```
push할 때마다 Actions 탭에서 Windows용 결과물을 내려받을 수 있습니다. (CI에서는 한글 파일명보다 영문 이름이 안전합니다.)

### 5.4 Windows 시작 시 자동 실행
레지스트리 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`에 exe 경로를 등록합니다 (`winreg`로 설정 창에서 켜고 끄기).

### 5.5 배포 시 알아둘 것
- 코드 서명을 하지 않으면 처음 실행할 때 **"Windows의 PC 보호" (SmartScreen) 경고**가 뜹니다. 사내나 지인용이면 "추가 정보 → 실행"으로 넘어가면 되고, 일반 배포라면 코드 서명 인증서가 필요합니다.
- exe 크기는 PySide6 때문에 60~100MB 정도 됩니다. 쓰지 않는 Qt 모듈을 PyInstaller `--exclude-module`로 빼면 줄일 수 있습니다.

---

## 6. 개발 순서 (MVP까지 약 3~4주)

| 주차 | 할 일 | 완료 기준 |
|---|---|---|
| **1주** | 프로젝트 세팅, `engine/scheduler.py` + 테스트 (TDD) | 20/30/60분 알림, 연속 착석, 자리 비움 초기화, 겹침 방지 테스트 통과 |
| **1주** | 트레이 + 5초 타이머 + 간단한 팝업 (Mac에서 확인) | 시간을 1분 단위로 줄인 디버그 모드에서 팝업이 순서대로 뜸 |
| **2주** | 가이드 카드 UI: 그림 2장, 단계, 타이머, 버튼 3개 | "네, 맞췄어요"를 누르면 SQLite에 기록됨 |
| **2주** | `exercises.json` + 동작 6개 + 앉아서 대체 동작 3개, 그림 SVG | 카드에서 동작이 바뀌며 보임 |
| **3주** | Windows 어댑터 (자리 비움, 전체 화면) + GitHub Actions 빌드 | Windows에서 exe 실행, 전체 화면 영상 중에는 알림 안 뜸 |
| **3~4주** | 설정 창 (간격, 근무·점심 시간), 자동 실행, Inno Setup | 설치 파일로 설치 → 재부팅 후 자동 실행 |

**개발 팁**
- 환경변수 `POSTURE_DEBUG=1`이면 1분을 6초로 줄이는 "빠른 시계" 모드를 만들어 두면 UI 확인이 훨씬 빠릅니다.
- 그림은 처음에는 간단한 막대 인형 SVG로 시작하고, 나중에 일러스트로 바꾸세요 (`exercises.json`의 파일 경로만 바꾸면 됩니다).
- 문구는 `messages.py` 한 곳에 모아 두세요 (존댓말 통일, 나중에 수정이 쉬움).

---

## 7. 나중에 바꾸고 싶어진다면

- **용량·메모리를 줄이고 싶을 때**: Tauri(Rust + 웹 UI)로 옮기면 exe가 10MB 안팎이 됩니다. 엔진을 순수 로직으로 분리해 두었다면 스케줄 규칙과 테스트 케이스를 그대로 옮기면 됩니다.
- **웹캠 자세 확인(2단계)**: `mediapipe` + `opencv-python`을 추가합니다. exe 크기가 꽤 커지므로 별도 플러그인이나 선택 설치로 분리하는 것을 고려하세요.
