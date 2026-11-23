"""단계(Stage) 사이클: 알림이 뜰 때마다 1 → 2 → … → 8 → 1 순서로 돈다.

각 단계는 동작(자세)·멘트·금액 종류를 가진다. 순수 로직이라 Qt·DB를 모른다.
"""
from dataclasses import dataclass
from enum import IntEnum


class Stage(IntEnum):
    EYE_FAR = 1          # 먼 곳 보기
    CHIN_TUCK = 2        # 턱 당기기
    SHOULDER_OPEN = 3    # 어깨 펴기
    NECK_SIDE = 4        # 목 옆 늘리기
    SCAPULA_SQUEEZE = 5  # 날개뼈 모으기
    SEAT_BACK = 6        # 의자 위 허리 세우기
    ANKLE_PUMP = 7       # 발목 펌프
    STAND_WATER = 8      # 일어나서 물 마시기

    @property
    def column(self) -> str:
        """사이클 테이블의 boolean 컬럼 이름 (stage_1 ~ stage_8)."""
        return f"stage_{self.value}"


@dataclass(frozen=True)
class StageInfo:
    exercise_id: str   # exercises.json 의 동작 id (자세·단계 설명·그림)
    kind: str          # eye / posture / stretch / stand (금액·알림 창 종류)
    title: str         # 멘트 제목
    body: str          # 멘트 본문 (존댓말)


STAGES: dict[Stage, StageInfo] = {
    Stage.EYE_FAR: StageInfo(
        "eye_far", "eye", "안구 진료비 청구 예정",
        "모니터만 계속 보셨어요. 창밖 20초 보면 1,000원 할인돼요."),
    Stage.CHIN_TUCK: StageInfo(
        "chin_tuck", "posture", "거북목 견적 도착",
        "고개가 앞으로 나오기 쉬운 시간이에요. 지금 턱 당기면 3,000원 방어돼요."),
    Stage.SHOULDER_OPEN: StageInfo(
        "shoulder_open", "posture", "라운드숄더 청구 예정",
        "어깨가 안으로 말리고 있진 않나요? 펴주시면 3,000원 방어돼요."),
    Stage.NECK_SIDE: StageInfo(
        "neck_side", "stretch", "목 뭉침 도수치료 대기 중",
        "목 옆이 뻣뻣할 시간이에요. 15초씩 늘려주시면 5,000원 취소돼요."),
    Stage.SCAPULA_SQUEEZE: StageInfo(
        "scapula_squeeze", "stretch", "도수치료비 청구 대기 중",
        "등이 굽어 있을 시간이에요. 날개뼈 모아주시면 5,000원 취소돼요."),
    Stage.SEAT_BACK: StageInfo(
        "seat_back", "posture", "허리 견적 도착",
        "의자 끝에 걸터앉아 계신가요? 엉덩이를 등받이까지 넣으면 3,000원 방어돼요."),
    Stage.ANKLE_PUMP: StageInfo(
        "ankle_pump", "stretch", "하체 순환 장애 경고",
        "오래 앉으면 다리가 먼저 붓기 시작해요. 발목 20번이면 5,000원 취소돼요."),
    Stage.STAND_WATER: StageInfo(
        "stand_water", "stand", "착석 연체료 발생",
        "한 바퀴 다 돌았어요. 일어나서 물 한 잔 드시면 연체료 8,000원 면제!"),
}

FIRST = Stage(min(Stage))
LAST = Stage(max(Stage))


def next_stage(current: Stage | None) -> tuple[Stage, bool]:
    """다음 단계와 '새 사이클 시작 여부'를 돌려준다.

    current=None(처음) 이거나 마지막 단계였으면 → (1단계, True)
    """
    if current is None or current == LAST:
        return FIRST, True
    return Stage(current + 1), False


@dataclass
class StageCycle:
    """현재 사이클 위치를 메모리에 들고 있는 커서. DB에서 복원해 시작한다."""
    cycle_no: int = 0              # 몇 번째 사이클인지 (DB 행 id)
    position: Stage | None = None  # 마지막으로 보여준 단계

    def advance(self) -> tuple[Stage, bool]:
        stage, new_cycle = next_stage(self.position)
        self.position = stage
        return stage, new_cycle
