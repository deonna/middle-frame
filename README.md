# Middle Frame

**YouTube thumbnails, minus the shocked face.**

A tiny Chrome extension that swaps every thumbnail on YouTube for YouTube's own auto-generated frame from the middle of
the video. It's the trick Andrej Karpathy used for [HackerTube](https://karpathy.bearblog.dev/hacker-tube/), on the
real YouTube.

| Before | After |
|---|---|
| ![Before: uploaded thumbnails](docs/img/before_grid.png) | ![After: middle frames](docs/img/after_grid.png) |

Site: [deonna.github.io/middle-frame](https://deonna.github.io/middle-frame/)

## Install

1. [Download the zip](https://github.com/deonna/middle-frame/releases/latest/download/middle-frame.zip) and unzip it.
2. Open `chrome://extensions` and turn on **Developer mode**.
3. Click **Load unpacked** and pick the unzipped folder.

Works in Chrome, Edge, Brave and Arc.

## What it does

- **Middle frames** (on by default): each thumbnail's image becomes `i.ytimg.com/vi/<id>/maxres2.jpg`, falling back to
  `hq2.jpg`, then `hq1.jpg`, then the original if YouTube has no auto frame for that video. It keeps working through
  infinite scroll, and switching it off puts the originals back.
- **Calm titles** (off by default): ALL-CAPS words of 4+ letters become lowercase (AI, USA and NBA stay), shocked emoji
  are removed, and `!!!` becomes `!`.

No data collected, no analytics, no servers. See [privacy](docs/privacy.html).

## Develop

```bash
python3 scripts/make_icons.py          # icons
python3 scripts/test_extension.py      # end-to-end on live YouTube (needs: pip install playwright && playwright install chromium)
bash scripts/package.sh                # -> dist/middle-frame.zip (for the release and the Chrome Web Store)
```

`extension/content.js` is the whole thing: a `MutationObserver` that reads the video ID out of each thumbnail's image
URL (so it survives YouTube layout changes) and swaps the image.

Not affiliated with YouTube or Google. MIT licensed.
