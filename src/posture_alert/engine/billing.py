"""거북목 견적서: 알림 응답을 '가상 병원비'로 환산한다 (재미용 가상 금액).

- 알림에 응해 자세를 맞추면 → 그 금액만큼 "방어"
- 건너뛰거나 미루거나 그냥 닫히면 → 그 금액만큼 "청구"
"""
from dataclasses import dataclass

# 알림 종류별 1회 금액 (원). 도수치료 1회 10~15만원 선을 하루 단위로 쪼갠 느낌의 가상 값
PRICE: dict[str, int] = {
    "eye": 1_000,
    "posture": 3_000,
    "stretch": 5_000,
    "stand": 8_000,
}

ITEM_NAME: dict[str, str] = {
    "eye": "안구 혹사 진료비",
    "posture": "거북목 교정비",
    "stretch": "어깨 뭉침 도수치료",
    "stand": "착석 연체료",
}

SAVED_RESULTS = {"done", "away"}
BILLED_RESULTS = {"skip", "snooze", "timeout"}

DISCLAIMER = "※ 재미로 보는 가상 금액이에요. 실제 진료비와 다를 수 있어요."


def price_of(kind: str) -> int:
    return PRICE.get(kind, 0)


@dataclass
class Line:
    kind: str
    name: str
    count: int
    amount: int


@dataclass
class Receipt:
    saved: list[Line]
    billed: list[Line]

    @property
    def saved_total(self) -> int:
        return sum(l.amount for l in self.saved)

    @property
    def billed_total(self) -> int:
        return sum(l.amount for l in self.billed)

    @property
    def balance(self) -> int:
        """+면 방어 성공, -면 청구가 더 많음."""
        return self.saved_total - self.billed_total


def build_receipt(events: list[tuple[str, str]]) -> Receipt:
    """events: (kind, result) 목록 → 오늘의 견적서."""
    def lines(results: set[str]) -> list[Line]:
        out = []
        for kind in PRICE:
            n = sum(1 for k, r in events if k == kind and r in results)
            if n:
                out.append(Line(kind, ITEM_NAME[kind], n, n * PRICE[kind]))
        return out

    return Receipt(saved=lines(SAVED_RESULTS), billed=lines(BILLED_RESULTS))


def won(n: int) -> str:
    return f"{n:,}원"
