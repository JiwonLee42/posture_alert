"""생성한 (X)/(O) 두 칸 그림을 잘라 앱 이미지로 저장한다.

    uv run --with pillow python tools/crop_pair.py 그림.png neck_side f
    uv run --with pillow python tools/crop_pair.py 그림.png --rows 3 --names neck_side,scapula_squeeze,stand_water m

결과: src/posture_alert/assets/img/{동작id}[_{f|m}]_{bad|good}.png
"""
import argparse
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parent.parent / "src" / "posture_alert" / "assets" / "img"


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
    a = p.parse_args()

    # 위치 인자가 하나뿐이면 (--rows 모드에서 캐릭터만 준 경우) 캐릭터로 취급
    if a.names and a.exercise_id in ("f", "m") and a.character is None:
        a.character, a.exercise_id = a.exercise_id, None
    names = a.names.split(",") if a.names else [a.exercise_id]
    if None in names or len(names) != a.rows:
        p.error("동작 id 개수가 줄 수와 맞지 않아요")

    im = Image.open(a.image).convert("RGB")
    W, H = im.size
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
            out = OUT / f"{name}{suffix}_{which}.png"
            im.crop(box).save(out, optimize=True)
            print("저장:", out.relative_to(OUT.parent.parent.parent.parent))


if __name__ == "__main__":
    main()
