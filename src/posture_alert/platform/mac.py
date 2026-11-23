"""macOS 어댑터: 마지막 키보드·마우스 입력 이후 시간만 실제로 읽는다 (ioreg 의 HIDIdleTime).
전체 화면·회의 감지는 아직 없다 (항상 False)."""
import re
import subprocess

from .base import ActivityMonitor

_IDLE = re.compile(rb'"HIDIdleTime"\s*=\s*(\d+)')


class MacMonitor(ActivityMonitor):
    def idle_seconds(self) -> float:
        try:
            out = subprocess.run(["ioreg", "-c", "IOHIDSystem"], capture_output=True, timeout=2).stdout
        except (OSError, subprocess.SubprocessError):
            return 15.0   # 못 읽으면 '잠깐 멈춘 상태'로 봐서 알림이 막히지 않게
        m = _IDLE.search(out)
        return int(m.group(1)) / 1e9 if m else 15.0   # 나노초 → 초

    def fullscreen_or_dnd(self) -> bool:
        return False

    def in_meeting(self) -> bool:
        return False
