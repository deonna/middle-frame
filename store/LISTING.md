# Chrome Web Store listing: Middle Frame

Upload: `dist/middle-frame.zip` (run `bash scripts/package.sh`). Dashboard: https://chrome.google.com/webstore/devconsole

## Store listing tab

- **Name:** Middle Frame
- **Summary (132 max):** YouTube thumbnails, minus the shocked face. Shows YouTube's own frame from the middle of each video instead.
- **Category:** Tools (or Fun)
- **Language:** English
- **Description:**

  Middle Frame swaps every thumbnail on YouTube for YouTube's own auto-generated frame from the middle of the video. You
  see what's actually in the video, not the ad for it.

  It's the trick Andrej Karpathy used for HackerTube, on the real YouTube.

  Two switches, in the toolbar popup:
  - Middle frames (on): every thumbnail becomes a frame from mid-video. Works through infinite scroll. Switch it off and
    the originals come back.
  - Calm titles (off): LOUD WORDS get quiet, and the shocked emoji and !!! go away.

  Collects nothing. No analytics, no accounts, no servers. Runs only on youtube.com.

  Not affiliated with YouTube or Google.

- **Icon:** `store/icon_512.png` (resize to 128 if asked: `extension/icons/icon128.png`)
- **Screenshots (1280x800):** `store/screenshot_1_before_after.png`
- **Small promo tile (440x280):** `store/promo_tile_440x280.png`
- **Homepage URL:** https://deonna.github.io/middle-frame/
- **Support URL:** https://github.com/deonna/middle-frame/issues

## Privacy practices tab

- **Single purpose:** Replaces YouTube video thumbnails with YouTube's own mid-video frames (and optionally calms
  ALL-CAPS titles) on youtube.com.
- **Permission justification, `storage`:** Saves the user's two on/off settings (Middle frames, Calm titles).
- **Host permission justification (content script on youtube.com):** The extension only changes thumbnail images and
  titles on YouTube pages, so it needs to run on youtube.com.
- **Remote code:** No, I am not using remote code.
- **Data usage:** Collects no user data (leave every box unchecked). Certify all three disclosures.
- **Privacy policy URL:** https://deonna.github.io/middle-frame/privacy.html

## Distribution

- Visibility: Public. Regions: all. Free.
