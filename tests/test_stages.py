from posture_alert.engine.content import load_exercises
from posture_alert.engine.stages import STAGES, Stage, StageCycle, next_stage


def test_단계는_8개():
    assert [s.value for s in Stage] == list(range(1, 9))
    assert set(STAGES) == set(Stage)


def test_처음엔_1단계_새사이클():
    assert next_stage(None) == (Stage.EYE_FAR, True)


def test_순서대로_진행():
    assert next_stage(Stage.CHIN_TUCK) == (Stage.SHOULDER_OPEN, False)


def test_8단계_다음은_1단계로_돌아감():
    assert next_stage(Stage.STAND_WATER) == (Stage.EYE_FAR, True)


def test_사이클을_두바퀴_돌기():
    c = StageCycle()
    seen = [c.advance() for _ in range(10)]
    assert [s for s, _ in seen] == [*Stage, Stage.EYE_FAR, Stage.CHIN_TUCK]
    assert [new for _, new in seen].count(True) == 2


def test_컬럼_이름():
    assert Stage.SEAT_BACK.column == "stage_6"


def test_모든_단계의_동작이_exercises_json에_있음():
    ids = {e.id for e in load_exercises()}
    assert {info.exercise_id for info in STAGES.values()} <= ids
