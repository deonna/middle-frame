// Middle Frame
// Swaps every YouTube thumbnail for YouTube's own auto-generated frame from the middle of the video
// (i.ytimg.com/vi/<id>/maxres2.jpg, then hq2.jpg, then hq1.jpg), the same trick Karpathy's HackerTube uses.
// Optional "calm titles": LOUD WORDS become quiet words, shocked emoji and !!! go away.
// Runs only on youtube.com. Stores two on/off settings in chrome.storage.sync. Collects nothing.
(() => {
  "use strict";

  const MARK = "#middle-frame"; // our URLs carry this fragment, so we never swap our own swap
  const ID_RE = /^https?:\/\/i\d*\.ytimg\.com\/(?:vi|vi_webp)\/([A-Za-z0-9_-]{11})\//;
  const PLACEHOLDER_MAX_W = 120; // YouTube answers a missing size with a 120x90 grey card
  const MAX_SWAPS_PER_IMG = 40; // if YouTube keeps fighting us on one image, let it win
  const frameUrls = (id) => [
    `https://i.ytimg.com/vi/${id}/maxres2.jpg`,
    `https://i.ytimg.com/vi/${id}/hq2.jpg`,
    `https://i.ytimg.com/vi/${id}/hq1.jpg`,
  ];

  const settings = { frames: true, calmTitles: false };
  const originals = new WeakMap(); // img -> { src, srcset }
  const swapped = new Set(); // imgs currently showing a middle frame
  const calmed = new Map(); // title text node -> original text

  // ------------------------------------------------------------------ thumbnails
  const srcOf = (img) => img.getAttribute("src") || "";

  function videoId(img) {
    const src = srcOf(img);
    if (src.includes(MARK)) return null;
    const m = src.match(ID_RE);
    return m ? m[1] : null;
  }

  function tryNext(img) {
    const st = img.__mf;
    if (!st) return;
    st.i += 1;
    if (st.i < st.urls.length) img.src = st.urls[st.i] + MARK;
    else restore(img, true); // no auto frames for this video: keep the uploaded thumbnail
  }

  function onLoad(e) {
    const img = e.currentTarget;
    if (img.__mf && srcOf(img).includes(MARK) && img.naturalWidth && img.naturalWidth <= PLACEHOLDER_MAX_W) tryNext(img);
  }

  function onError(e) {
    const img = e.currentTarget;
    if (img.__mf && srcOf(img).includes(MARK)) tryNext(img);
  }

  function swap(img) {
    if (!settings.frames) return;
    const src = srcOf(img);
    if (img.__mfFailed === src) return;
    const id = videoId(img);
    if (!id) return;
    img.__mfCount = (img.__mfCount || 0) + 1;
    if (img.__mfCount > MAX_SWAPS_PER_IMG) return;
    originals.set(img, { src, srcset: img.getAttribute("srcset") });
    img.__mf = { id, urls: frameUrls(id), i: 0 };
    if (!img.__mfBound) {
      img.addEventListener("load", onLoad);
      img.addEventListener("error", onError);
      img.__mfBound = true;
    }
    img.removeAttribute("srcset");
    img.src = img.__mf.urls[0] + MARK;
    img.dataset.middleFrame = "on";
    swapped.add(img);
  }

  function restore(img, failed = false) {
    const o = originals.get(img);
    img.__mf = null;
    delete img.dataset.middleFrame;
    swapped.delete(img);
    if (!o) return;
    originals.delete(img);
    if (failed) img.__mfFailed = o.src; // don't retry this exact thumbnail
    if (o.srcset) img.setAttribute("srcset", o.srcset);
    img.src = o.src;
  }

  const scanImages = (root) => {
    if (root.tagName === "IMG") swap(root);
    if (root.querySelectorAll) root.querySelectorAll("img").forEach(swap);
  };

  // ------------------------------------------------------------------ calm titles
  const TITLE_SEL = [
    "a.ytLockupMetadataViewModelTitle", // home, channel, search and sidebar cards
    "#video-title", // older layouts
    "ytd-watch-metadata h1", // the title under the player
    ".shortsLockupViewModelHostMetadataTitle",
    ".shortsLockupViewModelHostOutsideMetadataTitle",
  ].join(",");
  const LOUD = /\b[A-Z][A-Z0-9'’]*[A-Z]\b/g; // a word in ALL CAPS
  const SHOCK = /[\u{1F631}\u{1F92F}\u{1F633}\u{1F632}\u{1F62E}\u{1F628}\u{203C}\u{2757}\u{2755}]\uFE0F?/gu;

  const ACRONYMS = new Set(["AI", "USA", "UK", "US", "EU", "NBA", "NFL", "NHL", "MLB", "UFC", "WWE", "F1", "GTA", "PS5", "PC",
    "TV", "DIY", "CEO", "FBI", "CIA", "NASA", "GPT", "ASMR", "DJ", "IRL", "NYC", "4K", "HD", "MIT", "API", "iOS"]);

  function calm(s) {
    const letters = s.replace(/[^A-Za-z]/g, ""), upper = s.replace(/[^A-Z]/g, "");
    let out;
    if (letters.length >= 8 && upper.length / letters.length > 0.6) {
      // the whole title is shouting: sentence case, real acronyms kept
      out = s.toLowerCase().replace(/[a-z0-9']+/g, (w) => (ACRONYMS.has(w.toUpperCase()) ? w.toUpperCase() : w));
      out = out.replace(/^([^a-z]*)([a-z])/, (m, pre, c) => pre + c.toUpperCase());
    } else {
      // a few LOUD words: quiet those (4+ letters, so AI, USA and NBA stay)
      out = s.replace(LOUD, (w) => (w.replace(/[^A-Z]/g, "").length >= 4 && !ACRONYMS.has(w) ? w.toLowerCase() : w));
    }
    return out.replace(SHOCK, "").replace(/!{2,}/g, "!").replace(/\?{2,}/g, "?").replace(/ {2,}/g, " ");
  }

  function calmTitles() {
    if (!settings.calmTitles) return;
    document.querySelectorAll(TITLE_SEL).forEach((el) => {
      const walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      for (let n = walk.nextNode(); n; n = walk.nextNode()) {
        const cur = n.nodeValue;
        const prev = calmed.get(n);
        const base = prev !== undefined && cur === calm(prev) ? prev : cur; // YouTube may have rewritten it
        const quiet = calm(base);
        if (quiet !== cur) {
          calmed.set(n, base);
          n.nodeValue = quiet;
        }
      }
    });
    for (const n of calmed.keys()) if (!n.isConnected) calmed.delete(n);
  }

  function uncalmTitles() {
    for (const [n, orig] of calmed) if (n.isConnected) n.nodeValue = orig;
    calmed.clear();
  }

  // ------------------------------------------------------------------ wiring
  const pending = new Set();
  let scheduled = false;
  function schedule(node) {
    pending.add(node);
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      const nodes = [...pending];
      pending.clear();
      if (settings.frames) nodes.forEach(scanImages);
      calmTitles();
    });
  }

  new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "attributes") schedule(m.target);
      else m.addedNodes.forEach((n) => n.nodeType === 1 && schedule(n));
    }
  }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src"] });

  setInterval(calmTitles, 1200); // titles change text in place when YouTube recycles cards

  function apply(next) {
    const framesWas = settings.frames;
    Object.assign(settings, next);
    if (settings.frames && !framesWas) scanImages(document);
    if (!settings.frames && framesWas) [...swapped].forEach((img) => restore(img));
    if (settings.calmTitles) calmTitles();
    else uncalmTitles();
  }

  chrome.storage.sync.get(["frames", "calmTitles"], (s) => {
    apply({ frames: s.frames ?? true, calmTitles: s.calmTitles ?? false });
    scanImages(document);
  });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area !== "sync") return;
    const next = {};
    for (const k of ["frames", "calmTitles"]) if (k in changes) next[k] = changes[k].newValue;
    apply(next);
  });
})();
