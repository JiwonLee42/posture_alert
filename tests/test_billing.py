from posture_alert.engine.billing import build_receipt, won


def test_응하면_방어_무시하면_청구():
    r = build_receipt([
        ("posture", "done"), ("posture", "done"),
        ("stand", "skip"), ("eye", "timeout"), ("stretch", "unsure"),
    ])
    assert r.saved_total == 6_000
    assert r.billed_total == 9_000
    assert r.balance == -3_000


def test_자리비움으로_일어난것도_방어():
    r = build_receipt([("stand", "away")])
    assert r.saved_total == 8_000


def test_잘모르겠어요는_금액없음():
    r = build_receipt([("posture", "unsure")])
    assert r.saved == [] and r.billed == []


def test_원_표기():
    assert won(35000) == "35,000원"
