"""생성한 (X)/(O) 두 칸 그림을 잘라 앱 이미지로 저장한다.

    uv run --with pillow python tools/crop_pair.py 그림.png neck_side f
    uv run --with pillow python tools/crop_pair.py 그림.png --rows 3 --names neck_side,scapula_squeeze,stand_water m

결과: src/posture_alert/assets/img/{동작id}[_{f|m}]_{bad|good}.png
"""
import argparse
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "src" / "posture_alert" / "assets" / "img"


def erase_labels(im: "Image.Image", period: int) -> "Image.Image":
    """빨강/초록 글자 영역을 찾아, 같은 x 에서 period 만큼 위의 배경으로 덮는다."""
    im = im.copy()
    px = im.load()
    W, H = im.size

    def is_label(r, g, b):
        return (r > 170 and g < 100 and b < 100) or (g > 110 and r < 100 and b < 100)

    # 글자는 각 칸의 왼쪽 위에 있다. 얼굴(볼 터치 빨강)까지 잡지 않게 그 구역만 찾는다
    for x0 in (0, W // 2):
        x1 = x0 + W // 5
        hits = [(x, y) for y in range(0, int(H * 0.45), 2) for x in range(x0, x1, 2)
                if is_label(*px[x, y])]
        if not hits:
            continue
        xs, ys = [h[0] for h in hits], [h[1] for h in hits]
        pad = 14
        box = (max(min(xs) - pad, 0), max(min(ys) - pad, 0), min(max(xs) + pad, W), max(ys) + pad)
        src_y = box[1] - period
        if src_y < 0:
            continue
        patch = im.crop((box[0], src_y, box[2], src_y + box[3] - box[1]))
        im.paste(patch, box[:2])
    return im


def out_path(name: str, character: str | None, which: str) -> Path:
    """동작 id 'default' 는 메인(기본) 그림 자리: img/default/{f|m}_{bad|good}.png"""
    if name == "default":
        return OUT / "default" / f"{character or 'f'}_{which}.png"
    return OUT / f"{name}{'_' + character if character else ''}_{which}.png"


def finish(im: "Image.Image", a) -> "Image.Image":
    if a.height:
        im = im.resize((round(im.width * a.height / im.height), a.height), Image.LANCZOS)
    if a.transparent:
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from transparent import make_transparent
        im = make_transparent(im)
    return im


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("image")
    p.add_argument("exercise_id", nargs="?", help="동작 id (한 쌍일 때)")
    p.add_argument("character", nargs="?", choices=["f", "m"], help="캐릭터 (생략하면 공통)")
    p.add_argument("--rows", type=int, default=1, help="여러 쌍을 세로로 쌓은 그림의 줄 수")
    p.add_argument("--names", help="줄별 동작 id, 쉼표로 구분 (--rows 와 함께)")
    p.add_argument("--top", type=float, default=0.14, help="칸 위쪽에서 잘라낼 비율 ((X)/(O) 글자)")
    p.add_argument("--bottom", type=float, default=0.02, help="칸 아래쪽에서 잘라낼 비율")
    p.add_argument("--side", type=float, default=0.03, help="칸 양옆에서 잘라낼 비율")
    p.add_argument("--erase-labels", action="store_true",
                   help="빨강 (X)/초록 (O) 글자를 위쪽 배경 무늬로 덮어 지움")
    p.add_argument("--period", type=int, default=240, help="배경 체크무늬 반복 주기(px)")
    p.add_argument("--boxes", help="자를 상자 직접 지정: 'x0,y0,x1,y1;x0,y0,x1,y1' (✕칸;○칸)")
    p.add_argument("--height", type=int, help="저장할 때 이 높이(px)로 줄임 (예: 440)")
    p.add_argument("--transparent", action="store_true", help="체크무늬 배경을 투명으로 (tools/transparent.py)")
    a = p.parse_args()

    # 위치 인자가 하나뿐이면 (--rows 모드에서 캐릭터만 준 경우) 캐릭터로 취급
    if a.names and a.exercise_id in ("f", "m") and a.character is None:
        a.character, a.exercise_id = a.exercise_id, None
    names = a.names.split(",") if a.names else [a.exercise_id]
    if None in names or len(names) != a.rows:
        p.error("동작 id 개수가 줄 수와 맞지 않아요")

    im = Image.open(a.image).convert("RGB")
    if a.erase_labels:
        im = erase_labels(im, a.period)
    W, H = im.size
    if a.boxes:
        boxes = [tuple(int(v) for v in b.split(",")) for b in a.boxes.split(";")]
        out_dir = OUT
        suffix = f"_{a.character}" if a.character else ""
        for box, which in zip(boxes, ("bad", "good")):
            out = out_path(names[0], a.character, which)
            finish(im.crop(box), a).save(out, optimize=True)
            print("저장:", out.relative_to(OUT.parent.parent.parent.parent))
        return
    row_h = H / a.rows
    suffix = f"_{a.character}" if a.character else ""
    OUT.mkdir(parents=True, exist_ok=True)
    for r, name in enumerate(names):
        y0, y1 = r * row_h, (r + 1) * row_h
        for col, which in ((0, "bad"), (1, "good")):
            x0, x1 = col * W / 2, (col + 1) * W / 2
            cw, ch = x1 - x0, y1 - y0
            box = (int(x0 + cw * a.side), int(y0 + ch * a.top),
                   int(x1 - cw * a.side), int(y1 - ch * a.bottom))
            out = out_path(name, a.character, which)
            finish(im.crop(box), a).save(out, optimize=True)
            print("저장:", out.relative_to(OUT.parent.parent.parent.parent))


if __name__ == "__main__":
    main()
