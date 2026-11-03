#!/usr/bin/env python3
"""Record the Chrome Web Store promo video: the extension running on live YouTube, with a small state label.

    python3 scripts/record_promo.py        # -> store/promo_video.mp4 (1280x720, ~25 s); upload it to YouTube, paste the link

The real toolbar popup can't be captured headless, so the switches are flipped through the extension's own storage
and a caption pill says which state is showing. Everything on the page is real YouTube with the real extension.
"""
import subprocess
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
OUT = ROOT / "store/promo_video.mp4"
FONT = Path.home() / "Repos/other/video-projects/assets/fonts/TikTokSans/static/TikTokSans_18pt-Bold.ttf"
CHANNEL = "https://www.youtube.com/@MrBeast/videos"
LOUD = "https://www.youtube.com/results?search_query=INSANE+GONE+WRONG"


def pill_png(label, path):
    """Caption pill (this ffmpeg has no drawtext): charcoal, white text, the state word in highlight yellow."""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(str(FONT), 30); head, _, state = label.rpartition(" ")
    d = ImageDraw.Draw(Image.new("RGBA", (4, 4))); wh, ws = d.textlength(head + " ", font=f), d.textlength(state, font=f)
    asc, desc = f.getmetrics(); w, h = int(wh + ws + 36), asc + desc + 22
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=(23, 23, 26, 228))
    d.text((18, 11), head + " ", font=f, fill=(255, 255, 255, 255))
    d.text((18 + wh, 11), state, font=f, fill=(255, 225, 77, 255) if state == "on" else (196, 194, 188, 255))
    im.save(path); return path


def main():
    marks = []                                            # (seconds into the recording, label)
    with sync_playwright() as p, tempfile.TemporaryDirectory() as prof, tempfile.TemporaryDirectory() as vids:
        ctx = p.chromium.launch_persistent_context(
            prof, channel="chromium", headless=True, viewport={"width": 1280, "height": 720}, locale="en-US",
            record_video_dir=vids, record_video_size={"width": 1280, "height": 720},
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
        setv = lambda **kv: sw.evaluate("(kv) => chrome.storage.sync.set(kv)", kv)
        setv(frames=False, calmTitles=False)
        pg = ctx.new_page(); t0 = time.monotonic(); at = lambda: time.monotonic() - t0
        pg.goto(CHANNEL, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4500)
        pg.mouse.wheel(0, 380); pg.wait_for_timeout(1200)
        start = at(); marks.append((start, "Middle Frame: off"))
        pg.wait_for_timeout(2600)
        setv(frames=True); marks.append((at(), "Middle Frame: on")); pg.wait_for_timeout(3200)
        for _ in range(10): pg.mouse.wheel(0, 260); pg.wait_for_timeout(260)
        pg.wait_for_timeout(1500); a_end = at()
        pg.goto(LOUD, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4200)
        b_start = at(); marks.append((b_start, "Calm titles: off")); pg.wait_for_timeout(2600)
        setv(calmTitles=True); marks.append((at(), "Calm titles: on")); pg.wait_for_timeout(3200)
        end = at()
        vpath = pg.video.path(); ctx.close()
        # two segments (the channel page, then the loud search), the page-load gap cut out; a caption pill per state
        labels = [l for _, l in marks]; pngs = [pill_png(l, Path(vids) / f"pill{i}.png") for i, l in enumerate(labels)]
        def chain(src, seg0, seg1, tag):
            out, cur = [f"[0:v]trim=start={seg0:.2f}:end={seg1:.2f},setpts=PTS-STARTPTS[{tag}0]"], f"{tag}0"
            for i, (t, label) in enumerate(marks):
                t1 = marks[i + 1][0] if i + 1 < len(marks) else end
                if t1 <= seg0 or t >= seg1: continue
                nxt = f"{tag}{i + 1}"
                out.append(f"[{cur}][{i + 1}:v]overlay=36:36:enable='between(t,{max(t, seg0) - seg0:.2f},{min(t1, seg1) - seg0:.2f})'[{nxt}]"); cur = nxt
            return out, cur
        fa, ca = chain(0, start, a_end, "a"); fb, cb = chain(0, b_start, end, "b")
        fc = ";".join(fa + fb + [f"[{ca}][{cb}]concat=n=2:v=1:a=0,fps=30[v]"])
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", vpath]
        for png in pngs: cmd += ["-i", str(png)]
        subprocess.run(cmd + ["-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                              "-movflags", "+faststart", str(OUT)], check=True)
        dur = (a_end - start) + (end - b_start)
    print(f"-> {OUT} ({dur:.1f} s)")


if __name__ == "__main__":
    main()
