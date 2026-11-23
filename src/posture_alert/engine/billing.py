"""척추수술 3000: 남은 수술비 3,000만원을 0원으로 줄이는 게임 (재미용 가상 금액).

- 알림에 응해 자세를 맞추면 → 수술비가 줄어듦 (방어)
- 건너뛰거나 미루거나 그냥 닫히면 → 수술비가 다시 늘어남 (청구)
"""
from dataclasses import dataclass

SURGERY_COST = 30_000_000  # 시작 금액: 척추수술 3,000만원 → 목표 0원

# 했을 때 줄어드는 금액
PRICE: dict[str, int] = {
    "eye": 500_000,
    "posture": 1_000_000,
    "stretch": 1_000_000,
    "stand": 1_500_000,
}
# 무시했을 때 다시 늘어나는 금액
PENALTY = 500_000

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


def remaining(events: list[tuple[str, str]], start: int = SURGERY_COST) -> int:
    """기록을 순서대로 반영한 남은 수술비 (0원 ~ 시작 금액 사이)."""
    r = start
    for kind, result in events:
        if result in SAVED_RESULTS:
            r = max(0, r - price_of(kind))
        elif result in BILLED_RESULTS:
            r = min(start, r + PENALTY)
    return r


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
    """events: (kind, result) 목록 → 견적서."""
    def lines(results: set[str], unit) -> list[Line]:
        out = []
        for kind in PRICE:
            n = sum(1 for k, r in events if k == kind and r in results)
            if n:
                out.append(Line(kind, ITEM_NAME[kind], n, n * unit(kind)))
        return out

    return Receipt(saved=lines(SAVED_RESULTS, price_of),
                   billed=lines(BILLED_RESULTS, lambda _: PENALTY))


def won(n: int) -> str:
    """1,500만원 / 50만원 / 0원 처럼 만원 단위로 표시."""
    if n == 0:
        return "0원"
    if n % 10_000 == 0:
        return f"{n // 10_000:,}만원"
    return f"{n:,}원"
