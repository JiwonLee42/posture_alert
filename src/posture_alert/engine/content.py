"""알림 문구(존댓말)와 동작 데이터 로딩."""
import json
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .scheduler import Kind

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@dataclass(frozen=True)
class Exercise:
    id: str
    kind: str          # eye / posture / stretch / stand / seated_alt
    name: str
    steps: list[str]
    check: str         # "이 자세가 되었나요?" 앞에 붙는 체크 질문
    hold_seconds: int
    reps: int
    tip: str = ""

    @property
    def total_seconds(self) -> int:
        return self.hold_seconds * self.reps


@dataclass(frozen=True)
class Message:
    title: str
    body: str


MESSAGES: dict[Kind, Message] = {
    Kind.EYE: Message("눈 휴식", "잠깐 창밖 한번 볼까요?"),
    Kind.POSTURE: Message("거북목 주의!", "귀가 어깨 위에 있나요?"),
    Kind.STRETCH: Message("스트레칭 시간", "1시간 지났어요, 어깨 한번 펴볼까요?"),
    Kind.STAND: Message("일어날 시간", "물 한 잔 마시고 오실래요?"),
}


def message_for(kind: Kind, now: datetime | None = None, sitting_minutes: int = 0) -> Message:
    now = now or datetime.now()
    m = MESSAGES[kind]
    if kind is Kind.STAND and sitting_minutes >= 120:
        h, mm = divmod(sitting_minutes, 60)
        return Message("일어날 시간", f"{h}시간 {mm}분째 앉아 계셨어요. 허리랑 다리가 제일 힘들 때예요")
    if kind is Kind.POSTURE and 13 <= now.hour < 15:
        return Message("식곤증 타임", "졸리시죠? 허리부터 세워볼까요?")
    if kind is not Kind.EYE and now.hour >= 19:
        return Message(m.title, "야근 중이시네요, 목 한번 풀어주세요")
    return m


def load_exercises(path: Path | None = None) -> list[Exercise]:
    data = json.loads((path or ASSETS / "exercises.json").read_text(encoding="utf-8"))
    return [Exercise(**e) for e in data]


def pick(exercises: list[Exercise], kind: str, rng: random.Random | None = None) -> Exercise:
    pool = [e for e in exercises if e.kind == kind]
    return (rng or random).choice(pool)
