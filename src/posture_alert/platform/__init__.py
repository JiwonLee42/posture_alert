"""OS별 활동 감지 어댑터. Windows면 실제 구현, 그 외(Mac 개발 환경)는 가짜 구현."""
import sys

from .base import ActivityMonitor


def get_monitor() -> ActivityMonitor:
    if sys.platform == "win32":
        from .windows import WindowsMonitor
        return WindowsMonitor()
    from .fake import FakeMonitor
    return FakeMonitor()


__all__ = ["ActivityMonitor", "get_monitor"]
