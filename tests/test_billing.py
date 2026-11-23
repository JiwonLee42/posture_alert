from posture_alert.engine.billing import SURGERY_COST, build_receipt, remaining, won


def test_시작은_3000만원():
    assert remaining([]) == SURGERY_COST == 30_000_000


def test_하면_줄고_무시하면_늘어남():
    r = remaining([("posture", "done"), ("posture", "done"), ("stand", "skip")])
    assert r == 30_000_000 - 2_000_000 + 500_000


def test_0원_아래로_안내려감():
    assert remaining([("stand", "done")] * 100) == 0


def test_3000만원_위로_안올라감():
    assert remaining([("posture", "skip")] * 10) == SURGERY_COST


def test_순서대로_반영():
    # 이미 3000만원일 때 무시는 더 안 늘고, 그 뒤 한 번 하면 줄어듦
    assert remaining([("posture", "skip"), ("posture", "done")]) == 29_000_000


def test_자리비움으로_일어난것도_방어():
    assert remaining([("stand", "away")]) == 28_500_000


def test_잘모르겠어요_전환은_금액없음():
    r = build_receipt([("posture", "unsure"), ("stand", "switched")])
    assert r.saved == [] and r.billed == []
    assert remaining([("posture", "unsure"), ("stand", "shown")]) == SURGERY_COST


def test_견적서_합계():
    r = build_receipt([("posture", "done"), ("eye", "done"), ("stand", "snooze")])
    assert r.saved_total == 1_500_000
    assert r.billed_total == 500_000


def test_만원_표기():
    assert won(15_000_000) == "1,500만원"
    assert won(500_000) == "50만원"
    assert won(0) == "0원"
    assert won(1_234) == "1,234원"
