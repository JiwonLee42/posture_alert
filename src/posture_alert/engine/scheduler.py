"""알림 엔진: 언제 어떤 알림을 띄울지 결정하는 순수 로직 (Qt·Windows 의존 없음)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class Kind(Enum):
    EYE = "eye"          # 20분: 눈 휴식
    POSTURE = "posture"  # 30분: 자세 체크
    STRETCH = "stretch"  # 60분: 스트레칭
    STAND = "stand"      # 연속 착석 90분~: 일어나기


# 같은 시각에 여러 개가 걸리면 앞쪽(큰 것) 하나만 띄운다
PRIORITY = [Kind.STAND, Kind.STRETCH, Kind.POSTURE, Kind.EYE]


@dataclass
class Snapshot:
    """플랫폼 어댑터가 매 tick마다 넘겨주는 현재 상태."""
    now: datetime
    idle_seconds: float
    fullscreen_or_dnd: bool = False
    in_meeting: bool = False


def default_intervals(speed: float = 1.0) -> dict[Kind, timedelta]:
    """speed=60 이면 1분이 1초로 줄어든다 (디버그용)."""
    base = {Kind.EYE: 20, Kind.POSTURE: 30, Kind.STRETCH: 60, Kind.STAND: 90}
    return {k: timedelta(minutes=m) / speed for k, m in base.items()}


@dataclass
class Scheduler:
    intervals: dict[Kind, timedelta]
    away_threshold: timedelta = timedelta(minutes=3)
    stand_repeat: timedelta = timedelta(minutes=30)
    typing_grace_seconds: float = 10
    last_fired: dict[Kind, datetime] = field(default_factory=dict)
    sitting_since: datetime | None = None
    deferred: bool = False

    @classmethod
    def create(cls, speed: float = 1.0) -> "Scheduler":
        # 자리 비움·타이핑 판정은 실제 입력 시간이라 speed를 적용하지 않는다
        return cls(
            intervals=default_intervals(speed),
            stand_repeat=timedelta(minutes=30) / speed,
        )

    @classmethod
    def for_cycle(cls, every_minutes: float = 20, speed: float = 1.0) -> "Scheduler":
        """단계 사이클 모드: every_minutes 마다 한 번(다음 단계), 연속 착석 90분이면 일어나기 끼어들기."""
        never = timedelta(days=3650)
        return cls(
            intervals={Kind.EYE: timedelta(minutes=every_minutes) / speed,
                       Kind.POSTURE: never, Kind.STRETCH: never,
                       Kind.STAND: timedelta(minutes=90) / speed},
            # 일어나기는 90분마다 한 번 (그 차례의 단계 알림을 대신함). 30분마다 반복하면
            # 90분 뒤부터 모든 알림이 일어나기로 바뀌어 단계가 안 넘어간다.
            stand_repeat=timedelta(minutes=90) / speed,
        )

    def tick(self, s: Snapshot) -> Kind | None:
        # 1) 자리 비움 → "일어남"으로 인정하고 모든 타이머 초기화
        if s.idle_seconds >= self.away_threshold.total_seconds():
            self.sitting_since = None
            self.last_fired = {k: s.now for k in Kind}
            return None
        if self.sitting_since is None:
            self.sitting_since = s.now

        # 2) 회의·전체 화면 중이면 보류 표시만 하고 띄우지 않음
        if s.in_meeting or s.fullscreen_or_dnd:
            self.deferred = True
            return None

        # 3) 타이핑 중이면 입력이 잠깐 멈출 때까지 기다림
        if s.idle_seconds < self.typing_grace_seconds:
            return None

        # 4) 기한이 지난 알림 중 우선순위가 가장 높은 것 하나만
        due = [k for k in PRIORITY if self._is_due(k, s.now)]
        if not due:
            return None
        kind = due[0]
        for k in Kind:  # 겹친 작은 알림은 같이 처리한 것으로 본다
            if PRIORITY.index(k) >= PRIORITY.index(kind):
                self.last_fired[k] = s.now
        self.deferred = False
        return kind

    def sitting_time(self, now: datetime) -> timedelta:
        return timedelta(0) if self.sitting_since is None else now - self.sitting_since

    def sitting_minutes(self, now: datetime) -> int:
        return int(self.sitting_time(now).total_seconds() // 60)

    def next_in(self, now: datetime, kind: Kind = Kind.EYE) -> timedelta | None:
        """kind 알림이 뜨기까지 남은 시간 (이미 지났으면 0, 아직 앉기 시작 전이면 None)."""
        last = self.last_fired.get(kind, self.sitting_since)
        if last is None:
            return None
        return max(timedelta(0), self.intervals[kind] - (now - last))

    def _is_due(self, k: Kind, now: datetime) -> bool:
        last = self.last_fired.get(k, self.sitting_since)
        if k is Kind.STAND:
            return (self.sitting_time(now) >= self.intervals[k]
                    and now - last >= self.stand_repeat)
        return now - last >= self.intervals[k]
