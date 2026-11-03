#!/usr/bin/env python3
"""Middle Frame icons: three film frames on charcoal, the middle one in highlight yellow.

    python3 scripts/make_icons.py      # -> extension/icons/icon{16,32,48,128}.png + store/icon_512.png
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
INK, GREY, MARK = (23, 23, 26, 255), (92, 92, 100, 255), (255, 225, 77, 255)


def draw(size=1024):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=int(size * 0.22), fill=INK)
    fw, fh, gap = size * 0.2, size * 0.42, size * 0.06           # side frames
    mw, mh = size * 0.26, size * 0.54                            # the middle frame, a little bigger
    cx, cy = size / 2, size / 2
    r = size * 0.045
    d.rounded_rectangle((cx - mw / 2, cy - mh / 2, cx + mw / 2, cy + mh / 2), radius=r, fill=MARK)
    for sgn in (-1, 1):
        x0 = cx + sgn * (mw / 2 + gap) - (fw if sgn < 0 else 0)
        d.rounded_rectangle((x0, cy - fh / 2, x0 + fw, cy + fh / 2), radius=r, fill=GREY)
    return im


def main():
    big = draw()
    (ROOT / "extension/icons").mkdir(parents=True, exist_ok=True); (ROOT / "store").mkdir(exist_ok=True)
    for s in (16, 32, 48, 128):
        big.resize((s, s), Image.LANCZOS).save(ROOT / f"extension/icons/icon{s}.png")
    big.resize((512, 512), Image.LANCZOS).save(ROOT / "store/icon_512.png")
    big.resize((128, 128), Image.LANCZOS).save(ROOT / "docs/img/icon128.png")
    print("icons ->", ROOT / "extension/icons")


if __name__ == "__main__":
    main()
