"""Mac 개발용 가짜 어댑터: 항상 '입력이 잠깐 멈춘 상태'로 보고해서 알림이 뜨게 한다."""
from .base import ActivityMonitor


class FakeMonitor(ActivityMonitor):
    def __init__(self, idle: float = 15.0):
        self.idle = idle
        self.fullscreen = False
        self.meeting = False

    def idle_seconds(self) -> float:
        return self.idle

    def fullscreen_or_dnd(self) -> bool:
        return self.fullscreen

    def in_meeting(self) -> bool:
        return self.meeting
