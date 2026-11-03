// Middle Frame popup: two switches, saved to chrome.storage.sync; the content script applies them live.
const keys = ["frames", "calmTitles"];
const defaults = { frames: true, calmTitles: false };

chrome.storage.sync.get(keys, (s) => {
  for (const k of keys) {
    const box = document.getElementById(k);
    box.checked = s[k] ?? defaults[k];
    box.addEventListener("change", () => chrome.storage.sync.set({ [k]: box.checked }));
  }
});
