#!/usr/bin/env python3
"""End-to-end check of the unpacked extension in Playwright's Chromium, on live YouTube pages.

    python3 scripts/test_extension.py      # needs: pip install playwright && playwright install chromium

Loads extension/ into a fresh profile, then on a real channel page:
  1. frames OFF  -> screenshot (the uploaded thumbnails)              -> docs/img/before.png
  2. frames ON   -> every thumbnail swaps to a middle frame, live     -> docs/img/after.png
  3. scroll      -> thumbnails that load later swap too
  4. calm titles -> LOUD WORDS on a search page get quiet, and come back when it's switched off
Exits non-zero if any check fails.
"""
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extension"
CHANNEL = "https://www.youtube.com/@MrBeast/videos"
LOUD_SEARCH = "https://www.youtube.com/results?search_query=INSANE+GONE+WRONG"
GRID = {"x": 120, "y": 0, "width": 1280, "height": 800}

STATS = """() => {
  const imgs = [...document.querySelectorAll('img')].filter(i => /ytimg\\.com\\/vi/.test(i.getAttribute('src') || ''));
  const mf = imgs.filter(i => i.dataset.middleFrame === 'on');
  return { thumbs: imgs.length, swapped: mf.length,
           loaded: mf.filter(i => i.complete && i.naturalWidth > 120).length,
           sample: mf.slice(0, 3).map(i => i.getAttribute('src')) };
}"""


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    return ok


def main():
    results = []
    with sync_playwright() as p, tempfile.TemporaryDirectory() as prof:
        ctx = p.chromium.launch_persistent_context(
            prof, channel="chromium", headless=True, viewport={"width": 1400, "height": 900}, locale="en-US",
            args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}"])
        sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
        results.append(check("extension loaded", "chrome-extension://" in sw.url, sw.url))
        setv = lambda **kv: sw.evaluate("(kv) => chrome.storage.sync.set(kv)", kv)

        setv(frames=False, calmTitles=False)
        pg = ctx.new_page(); pg.goto(CHANNEL, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(5000)
        pg.mouse.wheel(0, 470); pg.wait_for_timeout(2500)                       # frame the video grid for the screenshots
        pg.screenshot(path=str(ROOT / "docs/img/before.png"), clip=GRID)
        s0 = pg.evaluate(STATS)
        results.append(check("off: nothing swapped", s0["swapped"] == 0 and s0["thumbs"] > 0, f"{s0['thumbs']} thumbnails"))

        setv(frames=True); pg.wait_for_timeout(3500)
        s1 = pg.evaluate(STATS)
        pg.screenshot(path=str(ROOT / "docs/img/after.png"), clip=GRID)
        results.append(check("on: thumbnails swapped live", s1["swapped"] >= max(1, int(0.8 * s1["thumbs"])), f"{s1['swapped']}/{s1['thumbs']}"))
        results.append(check("on: middle frames actually loaded", s1["loaded"] >= max(1, int(0.8 * s1["swapped"])), f"{s1['loaded']}/{s1['swapped']}; e.g. {s1['sample'][:1]}"))

        for _ in range(6): pg.mouse.wheel(0, 2500); pg.wait_for_timeout(900)
        pg.wait_for_timeout(2500); s2 = pg.evaluate(STATS)
        results.append(check("scroll: new thumbnails swap too", s2["swapped"] > s1["swapped"], f"{s1['swapped']} -> {s2['swapped']} of {s2['thumbs']}"))

        setv(frames=False); pg.wait_for_timeout(1500); s3 = pg.evaluate(STATS)
        results.append(check("off again: originals restored", s3["swapped"] == 0, f"{s3['swapped']} still swapped"))

        pg.goto(LOUD_SEARCH, wait_until="domcontentloaded", timeout=60000); pg.wait_for_timeout(5000)
        titles = "() => [...document.querySelectorAll('a.ytLockupMetadataViewModelTitle, #video-title')].map(e => e.innerText.trim()).filter(Boolean).slice(0, 40)"
        before = pg.evaluate(titles)
        setv(calmTitles=True); pg.wait_for_timeout(2500); after = pg.evaluate(titles)
        loud = lambda ts: sum(1 for t in ts for w in t.split() if sum(c.isupper() for c in w) >= 4 and w.upper() == w)
        results.append(check("calm titles: LOUD words get quiet", loud(before) > 0 and loud(after) == 0, f"{loud(before)} loud words -> {loud(after)}"))
        changed = [(a, b) for a, b in zip(before, after) if a != b][:3]
        for a, b in changed: print("     ", a, " ->  ", b)
        setv(calmTitles=False); pg.wait_for_timeout(2000); back = pg.evaluate(titles)
        results.append(check("calm titles off: originals back", loud(back) == loud(before), f"{loud(back)} loud words"))
        ctx.close()
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
