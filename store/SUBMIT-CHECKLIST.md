# Chrome Web Store: fixing "Unable to publish" (all 7 items)

Do the Privacy tab, then Settings, then **Save draft**, then **Submit for review**.

---

## Privacy tab

### 1. Single purpose description

```
Middle Frame replaces the video thumbnails on YouTube pages with YouTube's own auto-generated frame from the middle of each video, so you see what is actually in a video instead of a clickbait thumbnail. An optional "Calm titles" switch rewrites ALL-CAPS words in video titles to normal case. It does nothing outside youtube.com.
```

### 2. storage justification

```
Used only to save the user's two on/off settings (Middle frames and Calm titles) with chrome.storage.sync, so the choice stays the same across pages and devices. No other data is stored.
```

### 3. Host permission justification

```
The content script runs only on www.youtube.com and m.youtube.com, because those are the only pages the extension changes. On those pages it swaps each thumbnail image's address for YouTube's own mid-video frame of the same video (i.ytimg.com/vi/<video id>/maxres2.jpg or hq2.jpg) and, if the user turns on Calm titles, rewrites ALL-CAPS words in the title text. It reads nothing beyond the thumbnail image addresses and title text it changes, and it sends nothing anywhere.
```

### 4. Are you using remote code?

Pick **No, I am not using remote code**. (Right now "Yes" is selected. All the code is in the zip; the frames it
loads from YouTube are images, not code.) The Justification box disappears when you switch.

### 5. Data usage

- Leave **every** "What user data do you plan to collect" box **unchecked**. Middle Frame collects nothing.
- Check **all three** certification boxes:
  - I do not sell or transfer user data to third parties...
  - I do not use or transfer user data for purposes that are unrelated to my item's single purpose
  - I do not use or transfer user data to determine creditworthiness or for lending purposes

### 6. Privacy policy URL

```
https://deonna.github.io/middle-frame/privacy.html
```

---

## Settings page (left menu, "Account" or the gear) - items 6 and 7 in the error list

- **Contact email:** the publisher email shown on the listing. Your public one works: `hi@deonnahodges.com`
- **Verify it:** click "Verify", then open the email Google sends and click the link. The error clears once it's verified.

---

## Optional but speeds up review: Access > Test instructions

```
No account or login needed.
1. Install the extension and open https://www.youtube.com/@MrBeast/videos. Every thumbnail changes to YouTube's own frame from the middle of that video.
2. Click the Middle Frame toolbar icon. Turn "Middle frames" off: the original thumbnails come back. Turn it on again: they swap back.
3. Turn on "Calm titles" and open https://www.youtube.com/@Sidemen/videos. ALL-CAPS titles change to sentence case (for example "SIDEMEN ESCAPE THE MANSION" becomes "Sidemen escape the mansion"). Turn it off and the original titles return.
The extension makes no network requests of its own and stores only these two settings.
```

---

The yellow note ("Due to the Host Permission, your extension may require an in-depth review") is normal for any
extension that runs on a site. Ours is already as narrow as it can be (only youtube.com), so nothing to change.
