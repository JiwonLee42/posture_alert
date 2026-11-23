"""그림 속 '가짜 투명 배경'(체크무늬)을 진짜 투명(알파 0)으로 바꾼다.

이미지 생성 도구가 투명 배경 대신 체크무늬를 그려 넣는 경우가 많아서,
그림 가장자리와 이어진 '체크무늬 색과 비슷한 픽셀'만 지운다 (flood fill).
가장자리와 이어지지 않은 안쪽 색(옷·얼굴의 밝은 부분)은 남는다.

    uv run --with pillow --with numpy python tools/transparent.py 그림.png [그림2.png ...] [--tol 22] [--out 폴더]
"""
import argparse
from collections import Counter, deque
from pathlib import Path

import numpy as np
from PIL import Image


def background_colors(a: np.ndarray, n: int = 2) -> np.ndarray:
    """테두리 픽셀에서 가장 흔한 색 n개 (체크무늬 두 톤)."""
    border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bins = Counter(tuple(c // 8) for c in border)
    out = []
    for key, _ in bins.most_common(n):
        sel = np.all(border // 8 == key, axis=1)
        out.append(border[sel].mean(axis=0))
    return np.array(out)


def _flood(mask: np.ndarray, seeds, done: np.ndarray) -> list[tuple[int, int]]:
    h, w = mask.shape
    q = deque()
    out = []
    for y, x in seeds:
        if mask[y, x] and not done[y, x]:
            done[y, x] = True
            q.append((y, x))
    while q:
        y, x = q.popleft()
        out.append((y, x))
        for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not done[ny, nx]:
                done[ny, nx] = True
                q.append((ny, nx))
    return out


def make_transparent(im: Image.Image, tol: float = 22, min_area: int = 1500) -> Image.Image:
    rgb = np.asarray(im.convert("RGB")).astype(np.int16)
    h, w, _ = rgb.shape
    bg = background_colors(rgb)
    # 각 픽셀이 배경색 중 하나와 가까운지 (RGB 거리)
    dist = np.min(np.linalg.norm(rgb[:, :, None, :] - bg[None, None, :, :], axis=3), axis=2)
    near = dist <= tol

    # 배경 두 톤 중 어느 쪽에 가까운지 (갇힌 영역이 진짜 체크무늬인지 판단용)
    tone = np.argmin(np.linalg.norm(rgb[:, :, None, :] - bg[None, None, :, :], axis=3), axis=2)

    # 1) 가장자리와 이어진 배경
    clear = np.zeros((h, w), bool)
    border = [(y, x) for y in range(h) for x in (0, w - 1)] + [(y, x) for x in range(w) for y in (0, h - 1)]
    for y, x in _flood(near, border, clear):
        pass

    # 2) 가장자리와 안 이어졌지만(책상 밑 등) 체크무늬 두 톤이 다 들어 있는 넓은 영역도 배경
    seen = clear.copy()
    ys, xs = np.nonzero(near & ~clear)
    for y, x in zip(ys, xs):
        if seen[y, x]:
            continue
        region = _flood(near, [(y, x)], seen)
        if len(region) < min_area:
            continue
        ry, rx = zip(*region)
        share = np.bincount(tone[ry, rx], minlength=2) / len(region)
        if share.min() >= 0.2:  # 두 톤이 섞여 있으면 체크무늬
            clear[ry, rx] = True

    rgba = np.dstack([rgb.astype(np.uint8), np.where(clear, 0, 255).astype(np.uint8)])
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("images", nargs="+")
    p.add_argument("--tol", type=float, default=22, help="배경색으로 볼 색 거리 (클수록 많이 지움)")
    p.add_argument("--out", help="저장 폴더 (생략하면 원본을 덮어씀)")
    a = p.parse_args()
    for f in map(Path, a.images):
        out = Path(a.out) / f.name if a.out else f
        make_transparent(Image.open(f), a.tol).save(out, optimize=True)
        print("투명화:", out)


if __name__ == "__main__":
    main()
