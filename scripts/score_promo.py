#!/usr/bin/env python3
"""Step 2 of the promo: a psychedelic trance score synthesized from scratch (numpy + scipy, no samples), with the
picture cut onto its bars.

136 BPM, E Phrygian (the psytrance mode: that flat second, F over E, is the tension). Ten bars, 17.65 s:

  bars 1-2   OFF           drone + a dissonant "shock" stab, a 7-step acid arp cycling against the 16-step bar under
                           a closed filter, heartbeat kick, metallic FM pings, a reverse riser into...
  bars 3-6   ON            the drop: four-on-the-floor psy kick, rolling KBBB bass, open/closed hats, the acid line
                           opening up through a phaser and ping-pong delay, a 5-step inharmonic FM pattern (5 against
                           16), laser zaps
  bars 7-8   LOUD TITLES   beat-repeat stutter on the cut (1/8 -> 1/16 -> 1/32), kick out, bit-crushed clipped
                           cluster stabs (the LOUD titles), a riser into...
  bars 9-10  CALM TITLES   it resolves to E major 9: a wide shimmering pad, FM bells ping-ponging, half-time kick,
                           and a tape-stop to silence on the last beat

Every visual change is detected in the raw take (frame differences) and placed exactly on its bar line.

    python3 scripts/score_promo.py    # needs store/.promo_raw.webm from record_promo.py; numpy, scipy
      -> store/promo_music.wav (-14 LUFS, -1 dBTP) and store/promo_video.mp4 (picture + music + state pills)
"""
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from scipy import signal
from scipy.io import wavfile

ROOT = Path(__file__).resolve().parents[1]
RAW, CUES = ROOT / "store/.promo_raw.webm", ROOT / "store/.promo_cues.json"
OUT_WAV, OUT_MP4 = ROOT / "store/promo_music.wav", ROOT / "store/promo_video.mp4"
FONT = Path.home() / "Repos/other/video-projects/assets/fonts/TikTokSans/static/TikTokSans_18pt-Bold.ttf"

SR = 48000
BPM = 136.0
BEAT = 60 / BPM
S16 = BEAT / 4
BAR = 4 * BEAT
DROP, BREAK, CALM, END = 2 * BAR, 6 * BAR, 8 * BAR, 10 * BAR
N = int(round(END * SR))
t = np.arange(N) / SR
rng = np.random.default_rng(136)


def hz(m):
    return 440.0 * 2 ** ((np.asarray(m, dtype=float) - 69) / 12)


def place(dst, src, start, gain=1.0):
    s = int(round(start * SR))
    if s >= len(dst) or len(src) == 0:
        return
    if s < 0:
        src, s = src[-s:], 0
    e = min(len(dst), s + len(src))
    dst[s:e] += src[: e - s] * gain


# ---------------------------------------------------------------- oscillators and filters
TBL = 4096
_ph = np.arange(TBL) / TBL
SAW = sum(np.sin(2 * np.pi * k * _ph) / k for k in range(1, 64)); SAW /= np.abs(SAW).max()
SQR = sum(np.sin(2 * np.pi * k * _ph) / k for k in range(1, 64, 2)); SQR /= np.abs(SQR).max()


def osc(table, freq, phase0=0.0):
    ph = (phase0 + np.cumsum(freq) / SR) % 1.0
    idx = ph * TBL; i0 = idx.astype(np.int64); fr = idx - i0
    return table[i0 % TBL] * (1 - fr) + table[(i0 + 1) % TBL] * fr


def rbj_lp(fc, q):
    w0 = 2 * np.pi * np.clip(fc, 30, SR * 0.45) / SR; al = np.sin(w0) / (2 * q); c = np.cos(w0)
    b = np.array([(1 - c) / 2, 1 - c, (1 - c) / 2]); a = np.array([1 + al, -2 * c, 1 - al])
    return b / a[0], a / a[0]


def tv_lp(x, cutoff, q=0.707, block=64):
    """Resonant low-pass whose cutoff follows a curve (the acid squelch)."""
    y = np.zeros_like(x); zi = np.zeros(2)
    for s in range(0, len(x), block):
        e = min(s + block, len(x)); b, a = rbj_lp(float(cutoff[min(len(cutoff) - 1, (s + e) // 2)]), q)
        y[s:e], zi = signal.lfilter(b, a, x[s:e], zi=zi)
    return y


def lp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "low"); return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), "high"); return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], "band"); return signal.lfilter(b, a, x)


def phaser(x, rate=0.23, depth=0.9, stages=6, mix=0.55, block=256):
    lfo = 0.5 + 0.5 * np.sin(2 * np.pi * rate * np.arange(len(x)) / SR)
    zis = [np.zeros(1) for _ in range(stages)]; out = np.zeros_like(x)
    for s in range(0, len(x), block):
        e = min(s + block, len(x)); a = -0.15 - depth * 0.75 * lfo[(s + e) // 2]; seg = x[s:e]
        for k in range(stages): seg, zis[k] = signal.lfilter([a, 1.0], [1.0, a], seg, zi=zis[k])
        out[s:e] = seg
    return (1 - mix) * x + mix * out


def pingpong(x, delay, fb=0.5, taps=6, dark=5200):
    L, R = x.copy() * 0.0, x.copy() * 0.0; d = int(delay * SR); tap = x.copy()
    for k in range(1, taps + 1):
        tap = lp(np.concatenate([np.zeros(d), tap[:-d]]), max(900, dark - 600 * k)) * fb
        (R if k % 2 else L)[:] += tap
    return L, R


def reverb(x, seconds=2.6, decay=0.85, seed=1):
    n = int(seconds * SR); tt = np.arange(n) / SR
    ir = lp(np.random.default_rng(seed).standard_normal(n) * np.exp(-tt / decay), 7000)
    ir[: int(0.015 * SR)] *= np.linspace(0, 1, int(0.015 * SR))
    return signal.fftconvolve(x, ir / np.sqrt(np.sum(ir ** 2)))[: len(x)]


def env(n, a=0.002, d=0.1, s=0.0, total=None):
    tt = np.arange(n) / SR
    return np.minimum(tt / max(a, 1e-4), 1) * (s + (1 - s) * np.exp(-tt / max(d, 1e-4)))


# ---------------------------------------------------------------- the score
E = {"E1": 28, "F1": 29, "E2": 40, "F2": 41, "G2": 43, "A2": 45, "B2": 47, "C3": 48, "D3": 50, "E3": 52, "F3": 53,
     "G3": 55, "G#3": 56, "B3": 59, "C4": 60, "D4": 62, "D#4": 63, "E4": 64, "F4": 65, "F#4": 66, "G4": 67, "G#4": 68,
     "B4": 71, "E5": 76, "G#5": 80, "B5": 83, "E6": 88}


def kick(vel=1.0, sub_only=False):
    n = int(0.34 * SR); tt = np.arange(n) / SR
    f = 47 + 190 * np.exp(-tt / 0.016)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.15) * np.minimum(tt / 0.0015, 1)
    click = 0 if sub_only else hp(rng.standard_normal(n), 2500) * np.exp(-tt / 0.0025) * 0.35
    return np.tanh(1.6 * (body + click)) * vel


def acid_note(m, dur, cutoff_peak, q=7.0, glide_from=None, accent=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = np.full(n, float(hz(m)))
    if glide_from is not None: f = hz(m) * (hz(glide_from) / hz(m)) ** np.exp(-tt / 0.035)
    x = 0.65 * osc(SAW, f) + 0.35 * osc(SQR, f * 1.003)
    cut = 180 + cutoff_peak * accent * np.exp(-tt / (0.06 + 0.05 * accent))
    y = np.tanh(2.2 * tv_lp(x, cut, q)) * np.minimum(tt / 0.002, 1) * np.clip((dur - tt) / 0.012, 0, 1)
    return y * (0.75 + 0.35 * accent)


def fm(freq, dur, ratio, index, decay, vel=1.0):
    n = int(dur * SR); tt = np.arange(n) / SR
    mod = np.sin(2 * np.pi * freq * ratio * tt) * index * np.exp(-tt / (decay * 0.4))
    return np.sin(2 * np.pi * freq * tt + mod) * np.exp(-tt / decay) * np.minimum(tt / 0.001, 1) * vel


def noise_riser(dur, lo=400, hi=9000):
    n = int(dur * SR); tt = np.arange(n) / SR; x = rng.standard_normal(n); out = np.zeros(n)
    for s in range(0, n, 256):
        e = min(n, s + 256); fc = lo * (hi / lo) ** (s / n)
        out[s:e] = bp(x[max(0, s - 1024):e], fc * 0.6, fc * 1.5)[-(e - s):]
    return out * (tt / dur) ** 2.4


def zap(f0=3200, f1=160, dur=0.16):
    n = int(dur * SR); tt = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-tt / 0.03)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.06)


def crush(x, bits=5, hold=6):
    y = np.round(x * 2 ** (bits - 1)) / 2 ** (bits - 1)
    return np.repeat(y[::hold], hold)[: len(x)]


def build():
    drums_l, drums_r = np.zeros(N), np.zeros(N)
    kick_bus, bass, lead, pad_l, pad_r, fx_l, fx_r, metal = (np.zeros(N) for _ in range(8))
    kicks = []
    bar_t = lambda b, beat=0.0: b * BAR + beat * BEAT          # bar index from 0

    # ---- kick: heartbeat in the intro, four on the floor in the drop, half-time in the calm
    for b in range(10):
        for beat in range(4):
            tk = bar_t(b, beat)
            if b < 2 and beat in (0, 2): place(kick_bus, kick(0.55, sub_only=True), tk); kicks.append((tk, 0.4))
            elif 2 <= b < 6: place(kick_bus, kick(1.0), tk); kicks.append((tk, 1.0))
            elif b >= 8 and beat in (0, 2) and tk < END - BEAT: place(kick_bus, kick(0.7), tk); kicks.append((tk, 0.6))

    # ---- rolling bass (K B B B): three 16ths after every kick in the drop; a long sub under the calm
    for b in range(2, 6):
        for beat in range(4):
            root = E["F1"] if (b == 5 and beat == 3) else E["E1"]             # the flat-second twist before the break
            for k in (1, 2, 3):
                n = acid_note(root + 12, S16 * 0.92, 700 + 260 * k, q=1.4) * 0.55
                sub = np.sin(2 * np.pi * hz(root) * np.arange(len(n)) / SR) * env(len(n), 0.002, 0.07) * 0.7
                place(bass, n + sub, bar_t(b, beat) + k * S16)
    sub_n = int((END - CALM) * SR); stt = np.arange(sub_n) / SR
    place(bass, np.sin(2 * np.pi * hz(E["E1"]) * stt) * np.minimum(stt / 0.05, 1) * np.clip((END - CALM - 0.75 - stt) / 0.4, 0, 1) * 0.55, CALM)

    # ---- hats: closed 16ths and open off-beats in the drop, a few in the calm
    for b in list(range(2, 6)) + [8, 9]:
        for s in range(16):
            ts = bar_t(b) + s * S16; drop = b < 6
            if ts >= END - BEAT: break
            if drop or s % 2 == 0:
                n = int(0.03 * SR); h = hp(rng.standard_normal(n), 8500) * np.exp(-np.arange(n) / SR / 0.012)
                v = [0.5, 0.22, 0.34, 0.25][s % 4] * (0.8 + 0.4 * rng.random()) * (1 if drop else 0.6)
                pan = 0.5 + 0.4 * np.sin(2 * np.pi * ts / (BAR * 0.75))
                place(drums_l, h * v * (1 - pan), ts); place(drums_r, h * v * pan, ts)
            if drop and s % 4 == 2:
                n = int(0.16 * SR); o = hp(rng.standard_normal(n), 6500) * np.exp(-np.arange(n) / SR / 0.06)
                place(drums_l, o * 0.3, ts); place(drums_r, o * 0.3, ts)
        if 2 <= b < 6:                                                       # a crunchy clap on 2 and 4
            for beat in (1, 3):
                n = int(0.22 * SR); c = bp(rng.standard_normal(n), 900, 6000) * np.exp(-np.arange(n) / SR / 0.07)
                place(drums_l, np.tanh(c * 2) * 0.22, bar_t(b, beat) + 0.004); place(drums_r, np.tanh(c * 2) * 0.22, bar_t(b, beat))

    # ---- the acid line: a 7-step pattern against the 16-step bar (it comes round differently every bar)
    pat = [("E3", 1.0, False), ("E4", 0.5, False), ("F3", 0.8, True), ("B3", 0.55, False), ("E3", 0.9, False),
           ("G3", 0.6, True), ("D4", 0.7, False)]
    step = 0
    for b in range(0, 6):
        for s in range(16):
            ts = bar_t(b) + s * S16
            name, acc, slide = pat[step % 7]; prev = pat[(step - 1) % 7][0]
            peak = np.interp(ts, [0, DROP - 0.01, DROP, BREAK], [350, 1600, 2600, 4200])
            note = acid_note(E[name], S16 * 1.02, peak, q=7.5 if b >= 2 else 5.0, glide_from=E[prev] if slide else None, accent=acc)
            place(lead, note * (0.5 if b < 2 else 0.85), ts); step += 1

    # ---- metallic FM (inharmonic): 5 steps against 16 through the drop, sparse in the intro
    for b in range(0, 6):
        for s in range(16):
            gstep = b * 16 + s
            if (gstep % 5 == 0 and b >= 2) or (b < 2 and gstep % 11 == 0):
                ts = bar_t(b) + s * S16; f0 = float(hz(E["B4"] if gstep % 3 else E["F4"]))
                m = fm(f0, 0.5, ratio=3.17, index=4.5, decay=0.16, vel=0.35); pan = rng.uniform(0.1, 0.9)
                place(fx_l, m * (1 - pan), ts); place(fx_r, m * pan, ts)

    # ---- pad: a dark Phrygian drone (E, B, F rubbing) that opens into E major 9 for the calm
    def chord_pad(notes, t0, t1, cutoff_from, cutoff_to, gain):
        n = int((t1 - t0) * SR); tt = np.arange(n) / SR; Lp, Rp = np.zeros(n), np.zeros(n)
        for m in notes:
            for dl, dr in ((-11, 7), (6, -8), (0, 13), (24, -21)):                 # wide detune, a little microtonal smear
                Lp += osc(SAW, np.full(n, float(hz(m)) * 2 ** (dl / 1200)), rng.random())
                Rp += osc(SAW, np.full(n, float(hz(m)) * 2 ** (dr / 1200)), rng.random())
        cut = cutoff_from * (cutoff_to / cutoff_from) ** (tt / (t1 - t0)) * (1 + 0.35 * np.sin(2 * np.pi * 0.37 * tt))
        e = np.minimum(tt / 0.5, 1) * np.clip((t1 - t0 - tt) / 0.35, 0, 1)
        place(pad_l, tv_lp(Lp, cut, 1.1, 256) * e * gain / len(notes), t0); place(pad_r, tv_lp(Rp, cut * 1.04, 1.1, 256) * e * gain / len(notes), t0)
    chord_pad([E["E2"], E["B2"], E["E3"], E["F3"]], 0.0, BREAK + 0.2, 260, 2400, 0.55)
    chord_pad([E["E2"], E["F2"], E["B2"], E["C3"]], BREAK, CALM + 0.05, 900, 300, 0.35)
    chord_pad([E["E2"], E["B2"], E["G#3"], E["D#4"], E["F#4"], E["B4"]], CALM - 0.02, END, 700, 5200, 0.6)

    # ---- effects
    sh = np.tanh(3 * sum(osc(SAW, np.full(int(0.55 * SR), float(hz(m)))) for m in (E["E3"], E["F3"], E["B3"], E["C4"])))
    sh = crush(sh * env(len(sh), 0.002, 0.2), 4, 8) * 0.5                       # the "shock" stab on frame 0
    place(fx_l, sh, 0.0); place(fx_r, sh, 0.012); place(fx_l, sh * 0.5, BAR + 0.006); place(fx_r, sh * 0.5, BAR)
    r = noise_riser(BAR * 1.0); place(fx_l, r * 0.5, DROP - BAR); place(fx_r, r * 0.5, DROP - BAR)
    n = int(1.6 * SR); tt = np.arange(n) / SR                                     # impact on the drop
    boom = np.sin(2 * np.pi * np.cumsum(34 + 40 * np.exp(-tt / 0.07)) / SR) * np.exp(-tt / 0.6) + lp(rng.standard_normal(n), 2500) * np.exp(-tt / 0.15) * 0.4
    place(fx_l, boom * 0.7, DROP); place(fx_r, boom * 0.7, DROP)
    for z, pan in ((bar_t(3, 3.5), 0.2), (bar_t(4, 3.5), 0.8), (bar_t(5, 2.5), 0.3), (bar_t(5, 3.25), 0.7)):
        zz = zap(); place(fx_l, zz * 0.32 * (1 - pan), z); place(fx_r, zz * 0.32 * pan, z)
    for b, beats in ((6, (2.5, 3, 3.5)), (7, (0, 0.5, 1, 1.5, 2, 2.75, 3))):    # the LOUD-title stabs (after the stutter)
        for beat in beats:
            st = np.tanh(6 * sum(osc(SQR, np.full(int(0.12 * SR), float(hz(m)))) for m in (E["E3"], E["F3"], E["B3"], E["C4"], E["F4"])))
            st = crush(st * env(len(st), 0.001, 0.05), 3, 10) * 0.32; pan = 0.5 + 0.4 * (-1) ** int(beat * 2)
            place(fx_l, st * (1 - pan), bar_t(b, beat)); place(fx_r, st * pan, bar_t(b, beat))
    r2 = noise_riser(BAR * 0.95, 600, 11000); place(fx_l, r2 * 0.55, CALM - BAR * 0.95); place(fx_r, r2 * 0.55, CALM - BAR * 0.95)
    for i, m in enumerate([E["E4"], E["G#4"], E["B4"], E["E5"], E["G#5"], E["B5"], E["E6"]]):   # the calm shimmer
        bl = fm(float(hz(m)), 2.2, ratio=2.0, index=1.6, decay=0.55, vel=0.32 - i * 0.025)
        place(fx_l if i % 2 else fx_r, bl, CALM + i * S16 * 0.5)
    bells = np.zeros(N)
    for s in range(16 * 2):                                                       # FM bells across the calm
        ts = CALM + s * S16 * 2
        if ts >= END - BEAT: break
        m = [E["B4"], E["G#4"], E["E5"], E["D#4"], E["F#4"], E["B4"], E["E5"], E["G#5"]][s % 8]
        place(bells, fm(float(hz(m)), 1.2, 1.41, 2.0, 0.35, 0.22 if s % 2 else 0.3), ts)
    bl_l, bl_r = pingpong(bells, BEAT * 0.75, 0.45, 5)
    fx_l += bells * 0.5 + bl_l; fx_r += bells * 0.5 + bl_r
    return kick_bus, bass, lead, pad_l, pad_r, drums_l, drums_r, fx_l, fx_r, kicks


def sidechain(kicks, depth=0.55):
    g = np.ones(N)
    for tk, v in kicks:
        i0 = int(tk * SR); n = min(int(0.32 * SR), N - i0); tt = np.arange(n) / SR
        g[i0:i0 + n] = np.minimum(g[i0:i0 + n], 1 - depth * v * np.exp(-tt / 0.11))
    return g


def stutter(x):
    """Beat-repeat on the cut into the break: the last beat before it, chopped 1/8 -> 1/16 -> 1/32, fading."""
    y = x.copy(); src0 = int((BREAK - BEAT) * SR); pos = BREAK
    for length, count in ((BEAT / 2, 2), (BEAT / 4, 4), (BEAT / 8, 4)):
        seg = x[src0:src0 + int(length * SR)].copy(); seg *= np.clip(np.linspace(1, 0, len(seg)) * 8, 0, 1)
        for _ in range(count):
            i = int(pos * SR); y[i:i + len(seg)] = seg * (0.95 - 0.05 * (pos - BREAK) / BEAT); pos += length
    return y


def tape_stop(x, start, dur):
    """The last beat slows to a stop: playback rate falls to zero, pitch with it."""
    i0, n = int(start * SR), int(dur * SR); y = x.copy()
    rate = np.clip(1 - np.arange(n) / n, 0, 1) ** 1.6; pos = i0 + np.cumsum(rate)
    y[i0:i0 + n] = np.interp(pos, np.arange(len(x)), x) * np.clip(1 - np.arange(n) / n, 0, 1) ** 0.5
    y[i0 + n:] = 0; return y


def mix():
    k, bass, lead, pad_l, pad_r, dr_l, dr_r, fx_l, fx_r, kicks = build()
    sc = sidechain(kicks)
    lead = phaser(lead, 0.19); pl, pr = pingpong(lead, BEAT * 0.75, 0.42, 5, 4200)
    lead_l, lead_r = lead * 0.75 + pl * 0.6, lead * 0.75 + pr * 0.6
    mel_l = (pad_l + lead_l) * sc; mel_r = (pad_r + lead_r) * sc
    mid, side = (mel_l + mel_r) / 2, hp((mel_l - mel_r) / 2, 200) * 1.4; mel_l, mel_r = mid + side, mid - side
    wet_l = reverb(mel_l * 0.35 + fx_l * 0.5 + dr_l * 0.2, seed=1); wet_r = reverb(mel_r * 0.35 + fx_r * 0.5 + dr_r * 0.2, seed=2)
    L = k * 0.95 + bass * sc * 0.9 + mel_l * 0.55 + dr_l + fx_l * 0.8 + wet_l * 0.45
    R = k * 0.95 + bass * sc * 0.9 + mel_r * 0.55 + dr_r + fx_r * 0.8 + wet_r * 0.45
    L, R = stutter(L), stutter(R)
    L, R = tape_stop(L, END - BEAT * 1.6, BEAT * 1.5), tape_stop(R, END - BEAT * 1.6, BEAT * 1.5)
    L, R = np.tanh(L * 1.25) / np.tanh(1.25), np.tanh(R * 1.25) / np.tanh(1.25)
    peak = max(np.abs(L).max(), np.abs(R).max()); return np.stack([L, R], 1) / peak * 0.85


# ---------------------------------------------------------------- picture: find each change, cut it onto its bar
def frames(path, ss, dur, w, h):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", str(path), "-vf",
                          f"fps=30,scale={w}:{h},format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, h, w).astype(np.float32)


def find_change(cue, w, h, crop=None, look=2.0):
    """First frame after the switch flip where the page visibly changes (the swap loads, the titles rewrite)."""
    f = frames(RAW, cue - 0.4, look + 0.4, w, h)
    if crop: f = f[:, crop[0]:crop[1]]
    d = np.r_[0, np.abs(np.diff(f, axis=0)).mean(axis=(1, 2))]
    base = np.median(d[:10]) + 1e-3; thr = max(base * 6, base + 0.04)
    hit = next((i for i in range(10, len(d)) if d[i] > thr), None)
    return (cue - 0.4 + hit / 30) if hit is not None else cue


def find_text_change(cue, look=1.2, min_px=800):
    """The first frame with a real on-screen change (used for both switches). Titles rewriting is a few thousand sharp pixel changes, too small for a mean difference: count them, at full
    resolution, in a window right after the flip (a codec keyframe can't sneak in that close)."""
    f = frames(RAW, cue - 0.1, look, 1280, 720).astype(np.int16)
    for i in range(1, len(f)):
        if (np.abs(f[i] - f[i - 1])[120:] > 40).sum() > min_px: return cue - 0.1 + i / 30
    return cue + 0.05


def pill_png(label, path):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(str(FONT), 30); head, _, state = label.rpartition(" ")
    d = ImageDraw.Draw(Image.new("RGBA", (4, 4))); wh, ws = d.textlength(head + " ", font=f), d.textlength(state, font=f)
    asc, desc = f.getmetrics(); w, h = int(wh + ws + 36), asc + desc + 22
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=12, fill=(23, 23, 26, 228))
    d.text((18, 11), head + " ", font=f, fill=(255, 255, 255, 255))
    d.text((18 + wh, 11), state, font=f, fill=(255, 225, 77, 255) if state == "on" else (196, 194, 188, 255))
    im.save(path); return path


def loudnorm(src, dst):
    j = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(src), "-af", "loudnorm=I=-14:TP=-1.0:LRA=9:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    m = json.loads(j[j.rindex("{"):j.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.0:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
          f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,aresample=48000")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", af, "-c:a", "pcm_s16le", str(dst)], check=True)
    j = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(dst), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
    return j[j.rindex("Integrated loudness"):].split("\n")[1].strip(), j[j.rindex("True peak"):].split("\n")[1].strip()


def main():
    cues = json.loads(CUES.read_text())
    t_on = find_text_change(cues["frames_on"])             # the first frame where any thumbnail has swapped
    t_calm = find_text_change(cues["calm_on"])
    a0, a1 = t_on - DROP, t_on + (BREAK - DROP)                 # off for 2 bars, on for 4 (incl. the scroll)
    b0, b1 = t_calm - (CALM - BREAK), t_calm + (END - CALM)     # loud for 2 bars, calm for 2
    print(f"[1/4] visual changes: frames on {t_on:.3f} s (flip {cues['frames_on']:.3f}), calm titles {t_calm:.3f} s (flip {cues['calm_on']:.3f})")
    with tempfile.TemporaryDirectory() as tmp:
        print(f"[2/4] synthesizing {END:.2f} s at {BPM:.0f} BPM ...")
        raw = Path(tmp) / "raw.wav"; wavfile.write(raw, SR, mix().astype(np.float32))
        lufs, tp = loudnorm(raw, OUT_WAV); print(f"[3/4] music -> {OUT_WAV.name}: {lufs}, {tp}")
        labels = [("Middle Frame: off", 0, DROP), ("Middle Frame: on", DROP, BREAK), ("Calm titles: off", 0, CALM - BREAK), ("Calm titles: on", CALM - BREAK, END - BREAK)]
        pngs = [pill_png(l, Path(tmp) / f"p{i}.png") for i, (l, _, _) in enumerate(labels)]
        fc = (f"[0:v]trim=start={a0:.4f}:end={a1:.4f},setpts=PTS-STARTPTS[a0];"
              f"[a0][1:v]overlay=36:36:enable='between(t,{labels[0][1]:.4f},{labels[0][2]:.4f})'[a1];"
              f"[a1][2:v]overlay=36:36:enable='between(t,{labels[1][1]:.4f},{labels[1][2]:.4f})'[a];"
              f"[0:v]trim=start={b0:.4f}:end={b1:.4f},setpts=PTS-STARTPTS[b0];"
              f"[b0][3:v]overlay=36:36:enable='between(t,{labels[2][1]:.4f},{labels[2][2]:.4f})'[b1];"
              f"[b1][4:v]overlay=36:36:enable='between(t,{labels[3][1]:.4f},{labels[3][2]:.4f})'[b];"
              f"[a][b]concat=n=2:v=1:a=0,fps=30[v]")
        cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(RAW)] + sum((["-i", str(p)] for p in pngs), []) + ["-i", str(OUT_WAV)]
        subprocess.run(cmd + ["-filter_complex", fc, "-map", "[v]", "-map", "5:a", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
                              "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", str(OUT_MP4)], check=True)
    print(f"[4/4] video -> {OUT_MP4.name}: drop on bar 3 ({DROP:.3f} s), break bar 7 ({BREAK:.3f} s), calm bar 9 ({CALM:.3f} s), end {END:.3f} s")


if __name__ == "__main__":
    main()
