from datetime import datetime
from typing import Protocol

from ..engine.scheduler import Snapshot


class ActivityMonitor(Protocol):
    def idle_seconds(self) -> float: ...
    def fullscreen_or_dnd(self) -> bool: ...
    def in_meeting(self) -> bool: ...

    def snapshot(self, now: datetime | None = None) -> Snapshot:
        return Snapshot(
            now=now or datetime.now(),
            idle_seconds=self.idle_seconds(),
            fullscreen_or_dnd=self.fullscreen_or_dnd(),
            in_meeting=self.in_meeting(),
        )
