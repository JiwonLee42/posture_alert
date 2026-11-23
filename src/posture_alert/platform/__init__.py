"""OS별 활동 감지 어댑터. Windows·Mac은 실제 구현, 그 외는 가짜 구현."""
import sys

from .base import ActivityMonitor


def get_monitor() -> ActivityMonitor:
    if sys.platform == "win32":
        from .windows import WindowsMonitor
        return WindowsMonitor()
    if sys.platform == "darwin":
        from .mac import MacMonitor
        return MacMonitor()
    from .fake import FakeMonitor
    return FakeMonitor()


__all__ = ["ActivityMonitor", "get_monitor"]
