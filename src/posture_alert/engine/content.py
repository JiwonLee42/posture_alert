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


APP_NAME = "척추수술3000"
APP_TAGLINE = "기억하자 척추수술 3000만원"
APP_SUBTITLE = "오늘 당신의 구부정한 목이 청구한 병원비"

# 모든 문구는 존댓말. 금액은 billing.PRICE 와 맞춘다
MESSAGES: dict[Kind, Message] = {
    Kind.EYE: Message("안구 진료비 청구 예정",
                      "모니터만 20분째 보셨어요. 창밖 20초 보면 1,000원 할인돼요."),
    Kind.POSTURE: Message("거북목 견적 도착",
                          "30분째 같은 자세예요. 지금 턱 당기면 3,000원 방어돼요."),
    Kind.STRETCH: Message("도수치료비 청구 대기 중",
                          "1시간째 어깨가 굳고 있어요. 펴주시면 이번 청구 5,000원 취소돼요."),
    Kind.STAND: Message("착석 연체료 발생",
                        "오래 앉아 계셨어요. 일어나시면 연체료 8,000원 면제해 드려요."),
}


def message_for(kind: Kind, now: datetime | None = None, sitting_minutes: int = 0) -> Message:
    now = now or datetime.now()
    m = MESSAGES[kind]
    if kind is Kind.STAND and sitting_minutes >= 60:
        h, mm = divmod(sitting_minutes, 60)
        return Message("착석 연체료 발생",
                       f"{h}시간 {mm}분째 앉아 계세요. 지금 일어나시면 연체료 8,000원 면제!")
    if kind is Kind.POSTURE and 13 <= now.hour < 15:
        return Message("식곤증 할증 구간",
                       "졸리시죠? 이 시간 거북목은 할증이 붙어요. 허리부터 세워볼까요?")
    if kind is not Kind.EYE and now.hour >= 19:
        return Message("야간 할증 청구서",
                       "야근 중이시네요. 지금 목 풀어주시면 야간 진료비 방어돼요.")
    return m


def load_exercises(path: Path | None = None) -> list[Exercise]:
    data = json.loads((path or ASSETS / "exercises.json").read_text(encoding="utf-8"))
    return [Exercise(**e) for e in data]


def pick(exercises: list[Exercise], kind: str, rng: random.Random | None = None) -> Exercise:
    pool = [e for e in exercises if e.kind == kind]
    return (rng or random).choice(pool)
