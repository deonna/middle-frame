// Middle Frame: set the defaults once, on install.
chrome.runtime.onInstalled.addListener(async () => {
  const cur = await chrome.storage.sync.get(["frames", "calmTitles"]);
  await chrome.storage.sync.set({
    frames: cur.frames ?? true,
    calmTitles: cur.calmTitles ?? false,
  });
});
