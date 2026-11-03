#!/usr/bin/env python3
"""Chrome Web Store artwork, in the site's look (charcoal, highlight yellow, TikTok Sans wide/heavy).

    python3 scripts/make_store_assets.py
      store/store_icon_128.png      128x128: 96x96 artwork + 16 px transparent padding (Web Store icon guideline)
      store/promo_tile_440x280.png  small promo tile
      store/marquee_1400x560.png    marquee promo tile
No screenshots or third-party faces in the tiles (the screenshot slot carries the before/after).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import make_icons

ROOT = Path(__file__).resolve().parents[1]
FONT = Path.home() / "Repos/other/video-projects/assets/fonts/TikTokSans/TikTokSans-VariableFont_opsz,slnt,wdth,wght.ttf"
INK, PAPER, MUTED, MARK, GREY = (23, 23, 26), (251, 250, 247), (196, 194, 188), (255, 225, 77), (92, 92, 100)


def font(px, wght=820, wdth=118, opsz=36):
    f = ImageFont.truetype(str(FONT), px); f.set_variation_by_axes([opsz, wdth, wght, 0]); return f


def frames(d, cx, cy, h):
    """The motif: three film frames, the middle one in highlight yellow (same geometry as the icon)."""
    fw, fh, mw, mh, gap, r = h * .37, h * .78, h * .48, h, h * .11, h * .085
    d.rounded_rectangle((cx - mw / 2, cy - mh / 2, cx + mw / 2, cy + mh / 2), radius=r, fill=MARK)
    for s in (-1, 1):
        x0 = cx + s * (mw / 2 + gap) - (fw if s < 0 else 0)
        d.rounded_rectangle((x0, cy - fh / 2, x0 + fw, cy + fh / 2), radius=r, fill=GREY)


def marked(d, xy, text, f, mark_word):
    """Tagline with the highlight marker behind one phrase, like the site's headline."""
    x, y = xy; before, _, after = text.partition(mark_word)
    for part, hl in ((before, False), (mark_word, True), (after, False)):
        if not part: continue
        w = d.textlength(part, font=f); asc, desc = f.getmetrics()
        if hl: d.rectangle((x - 3, y + asc * .18, x + w + 3, y + asc + desc * .35), fill=MARK)
        d.text((x, y), part, font=f, fill=INK if hl else PAPER); x += w


def tile(w, h, title_px, tag_px):
    """Marquee: title + tagline on the left, the motif centred in the space that's left (sized to fit)."""
    im = Image.new("RGB", (w, h), INK); d = ImageDraw.Draw(im)
    pad = round(h * .14); ft, fg = font(title_px), font(tag_px, wght=520, wdth=104, opsz=20)
    text_w = max(d.textlength("Middle Frame", font=ft), d.textlength("minus the shocked face.", font=fg))
    d.text((pad, h / 2 - title_px * 1.02), "Middle Frame", font=ft, fill=PAPER)
    marked(d, (pad, h / 2 + title_px * .22), "minus the shocked face.", fg, "shocked face")
    x0, x1 = pad + text_w + h * .16, w - pad
    mh = min(h * .56, (x1 - x0) / 1.44)                  # the motif is 1.44 x its height wide
    frames(d, (x0 + x1) / 2, h / 2, mh)
    return im


def small_tile(w=440, h=280):
    """Small tile: the motif left, the name stacked right, a short tagline under it (legible at small sizes)."""
    im = Image.new("RGB", (w, h), INK); d = ImageDraw.Draw(im)
    mh = 118; frames(d, 40 + mh * .72, h / 2, mh)
    x = 40 + mh * 1.44 + 30; ft = font(46, wdth=112)
    d.text((x, h / 2 - 78), "Middle", font=ft, fill=PAPER); d.text((x, h / 2 - 28), "Frame", font=ft, fill=PAPER)
    marked(d, (x, h / 2 + 34), "no shocked faces", font(19, wght=560, wdth=104, opsz=18), "shocked faces")
    return im


def main():
    s = ROOT / "store"
    big = make_icons.draw(1024).resize((96, 96), Image.LANCZOS)
    ic = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); ic.paste(big, (16, 16), big); ic.save(s / "store_icon_128.png")
    small_tile().save(s / "promo_tile_440x280.png")
    tile(1400, 560, 112, 48).save(s / "marquee_1400x560.png")
    print("->", *(p.name for p in sorted(s.glob("*.png"))))


if __name__ == "__main__":
    main()
