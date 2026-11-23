"""투명 배경으로 만든 그림의 바깥쪽에 남은 밝은 테두리(하얀 후광·점)를 지운다.

사용: uv run --with pillow --with numpy --with scipy python tools/defringe.py [폴더 또는 파일 ...]
기본은 src/posture_alert/assets/img 아래 전체. 여러 번 돌려도 안전하다.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

LIGHT = 130       # 이 값보다 밝은 색(RGB 최솟값)만 후광 후보
ITERATIONS = 2    # 바깥에서 몇 겹까지 벗길지


def defringe(path: Path) -> int:
    a = np.array(Image.open(path).convert("RGBA"))
    removed = 0
    for _ in range(ITERATIONS):
        transparent = a[..., 3] < 128
        near = ndi.binary_dilation(transparent, structure=np.ones((3, 3))) & ~transparent
        light = a[..., :3].min(axis=2) > LIGHT
        mask = near & light
        removed += int(mask.sum())
        a[mask, 3] = 0
    Image.fromarray(a).save(path)
    return removed


def main() -> None:
    args = sys.argv[1:] or ["src/posture_alert/assets/img"]
    files = []
    for arg in args:
        p = Path(arg)
        files += sorted(p.rglob("*.png")) if p.is_dir() else [p]
    for f in files:
        print(f"{f}: {defringe(f)}px")


if __name__ == "__main__":
    main()
