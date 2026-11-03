#!/usr/bin/env python3
"""Step 1 of the promo: record the extension running on live YouTube (raw take + when each switch was flipped).

    python3 scripts/record_promo.py      # -> store/.promo_raw.webm + store/.promo_cues.json
    python3 scripts/score_promo.py       # step 2: synthesize the music, cut the picture onto its bars, mux

The real toolbar popup can't be captured headless, so the switches are flipped through the extension's own storage;
score_promo.py adds a caption pill that says which state is showing. Everything on the page is real YouTube with the
real extension. Holds are generous so the edit can land every change on a bar line.
"""
import json
import shutil
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
RAW, CUES = ROOT / "store/.promo_raw.webm", ROOT / "store/.promo_cues.json"
CHANNEL = "https://www.youtube.com/@MrBeast/videos"
LOUD = "https://www.youtube.com/@Sidemen/videos"                      # a grid of ALL-CAPS titles


def main():
    cues = {}
    with sync_playwright() as p, tempfile.TemporaryDirectory() as prof, tempfile.TemporaryDirectory() as vids:
        ctx = p.chromium.launch_persistent_context(
            prof, channel="chromium", headless=True, viewport={"width": 1280, "height": 720}, locale="en-US",
            record_video_dir=vids, record_video_size={"width": 1280, "height": 720},
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
        setv = lambda **kv: sw.evaluate("(kv) => chrome.storage.sync.set(kv)", kv)
        setv(frames=False, calmTitles=False)
        pg = ctx.new_page(); t0 = time.monotonic(); at = lambda: round(time.monotonic() - t0, 3)
        pg.goto(CHANNEL, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4500)
        pg.mouse.wheel(0, 380); pg.wait_for_timeout(4500)                     # long "off" hold
        cues["frames_on"] = at(); setv(frames=True); pg.wait_for_timeout(4200)
        cues["scroll"] = at()
        for _ in range(12): pg.mouse.wheel(0, 240); pg.wait_for_timeout(300)
        pg.wait_for_timeout(2000); cues["a_end"] = at()
        pg.goto(LOUD, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(4000)
        pg.mouse.wheel(0, 380); pg.wait_for_timeout(1200)                     # frame the grid of titles
        cues["b_start"] = at(); pg.wait_for_timeout(4000)
        cues["calm_on"] = at(); setv(calmTitles=True); pg.wait_for_timeout(4500)
        cues["end"] = at()
        vpath = pg.video.path(); ctx.close()
        shutil.copy(vpath, RAW)
    CUES.write_text(json.dumps(cues, indent=1))
    print("raw ->", RAW, cues)


if __name__ == "__main__":
    main()
