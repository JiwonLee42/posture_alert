"""앱을 켜둔 시간(분) 카운터.

값은 메모리에 들고 있고(읽을 때 DB를 안 감), 분이 바뀔 때만 DB에 써서(write-through)
앱이 꺼지거나 죽어도 마지막 분까지는 남게 한다.
"""
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class UptimeCounter:
    clock: Callable[[], float] = time.monotonic  # 시스템 시계 변경에 영향 안 받는 시계
    started: float = field(default=0.0)
    saved_minutes: int = 0  # 마지막으로 DB에 쓴 분

    def __post_init__(self):
        self.started = self.clock()

    @property
    def minutes(self) -> int:
        return int((self.clock() - self.started) // 60)

    def poll(self) -> int | None:
        """분이 바뀌었으면 새 분을 돌려주고(→ DB에 저장), 아니면 None."""
        m = self.minutes
        if m != self.saved_minutes:
            self.saved_minutes = m
            return m
        return None
