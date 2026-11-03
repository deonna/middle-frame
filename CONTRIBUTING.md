# Contributing to Middle Frame

Thanks for helping. Middle Frame is deliberately tiny: one content script, one popup, no build step, no dependencies.
Contributions that keep it that way are the easiest to merge.

## Good first contributions

- **YouTube changed its layout and something stopped swapping.** Open an issue with the page URL and a screenshot, or
  send a fix. The swap keys off each thumbnail's image address (`i.ytimg.com/vi/<id>/...`), so most layout changes
  don't break it, but new surfaces (end screens, the player's poster, Shorts) sometimes use other patterns.
- **Calm titles missing a spot.** New title selectors go in `TITLE_SEL` in `extension/content.js`.
- **Firefox / Safari ports.** The code is plain WebExtension APIs; it mostly needs manifest tweaks.

## Run it locally

1. Clone the repo, open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked**, pick `extension/`.
2. After editing, click the reload icon on the extension's card and refresh YouTube.

## Before you open a pull request

```bash
pip install playwright && playwright install chromium
python3 scripts/test_extension.py   # loads the extension into Chromium and checks live YouTube pages (8 checks)
bash scripts/package.sh             # builds dist/middle-frame.zip
```

- Keep the privacy promise: no analytics, no network calls besides YouTube's own image server, no new permissions
  without a very good reason (explain it in the PR).
- Keep it dependency-free and build-free.
- One change per PR, with a before/after screenshot when it's visual.

## Releasing (maintainer)

Bump `version` in `extension/manifest.json`, run `bash scripts/package.sh`, then
`gh release create vX.Y.Z dist/middle-frame.zip`, and upload the same zip to the Chrome Web Store dashboard.

By contributing you agree your work is released under the MIT license and that you'll follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
