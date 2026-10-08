"""Three original beds for the carousel reels. Usage: python3 music_reels.py rules|engine|system '<beats json>'"""
import json, sys
import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
SR = 48000; rng = np.random.default_rng(11)
name = sys.argv[1]; bt = json.loads(sys.argv[2])
BPM = bt["bpm"]; B = 60 / BPM; DUR = bt["starts"][-1] + bt["durs"][-1]; N = int(DUR * SR)
def filt(x, f, k): return sosfilt(butter(2, f, k, fs=SR, output="sos"), x)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def put(buf, at, s, g=1.0):
    i = int(at * SR)
    if 0 <= i < N: buf[i:i + len(s)] += s[: N - i] * g
tt = lambda d: np.arange(int(d * SR)) / SR
beats = np.arange(0, DUR - 0.5, B)
out = np.zeros(N)
def kick(d=0.35, f0=45, sweep=110, k=8):
    t = tt(d); return np.tanh(1.8 * np.sin(2 * np.pi * (f0 * t + sweep * (1 - np.exp(-t * 35)) / 35)) * np.exp(-t * k))
def noise_hit(d, lo, hi, k): t = tt(d); return filt(filt(rng.normal(0, 1, len(t)), lo, "high"), hi, "low") * np.exp(-t * k)
def keys(ms, d, bright=1.0, trem=0):
    t = tt(d); s = sum(np.sin(2 * np.pi * note(m) * t) + 0.35 * bright * np.sin(4 * np.pi * note(m) * t) + 0.12 * bright * np.sin(6 * np.pi * note(m) * t) for m in ms)
    if trem: s *= 1 + 0.25 * np.sin(2 * np.pi * trem * t)
    return s * np.minimum(1, t / 0.01) * np.exp(-t * 1.8)
if name == "rules":      # calm editorial: felt keys, soft pulse, shaker
    CH = [[60, 64, 67, 71], [57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65]]
    for i, b in enumerate(beats):
        bar = int(i / 4)
        if i % 4 == 0: put(out, b, keys(CH[bar % 4], 4 * B, 0.6), 0.10)
        if i % 2 == 0: put(out, b, kick(0.3, 50, 60, 10), 0.35)
        put(out, b + B / 2, noise_hit(0.06, 5000, 12000, 60), 0.05)
        put(out, b, noise_hit(0.04, 6000, 12000, 90), 0.03)
        m = CH[bar % 4][[0, 2, 1, 3][i % 4]] + 12
        put(out, b + B / 2, keys([m], 0.5, 0.3), 0.05)
elif name == "engine":   # 128 drums, pumping bass, stabs
    CH = [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]]
    K = kick(); CL = noise_hit(0.2, 900, 7000, 16) * 0.6; HH = noise_hit(0.04, 8000, 16000, 90)
    for i, b in enumerate(beats):
        bar = int(i / 4); put(out, b, K, 0.9)
        if i % 2 == 1: put(out, b, CL, 0.7)
        for q in range(4): put(out, b + q * B / 4, HH, 0.12 if q % 2 else 0.2)
        r = CH[bar % 4][0] - 24; t = tt(B / 2)
        for h in (0, 0.5): put(out, b + h * B, filt(((t * note(r)) % 1 * 2 - 1) * np.exp(-t * 6), 400, "low"), 0.35)
        st = tt(0.16); put(out, b + B / 2, filt(sum(((st * note(m + 12)) % 1 * 2 - 1) for m in CH[bar % 4]) * np.exp(-st * 14), 2500, "low"), 0.04)
else:                    # lo-fi 90: dusty kick/snare, swung hats, rhodes, crackle
    CH = [[62, 65, 69, 72], [55, 59, 62, 65], [60, 64, 67, 71], [57, 60, 64, 67]]
    K = filt(kick(0.4, 48, 70, 7), 2500, "low"); SN = filt(noise_hit(0.25, 400, 6000, 14) + 0.4 * np.sin(2 * np.pi * 180 * tt(0.25)) * np.exp(-tt(0.25) * 25), 4500, "low") * 0.8
    HH = noise_hit(0.05, 6000, 11000, 70)
    for i, b in enumerate(beats):
        bar = int(i / 4); pos = i % 4
        if pos == 0: put(out, b, keys(CH[bar % 4], 4 * B, 0.5, trem=4.5), 0.09)
        if pos in (0,): put(out, b, K, 0.8)
        if pos == 2: put(out, b + B / 2, K, 0.6)
        if pos in (1, 3): put(out, b, SN, 0.55)
        put(out, b, HH, 0.10); put(out, b + B * 0.62, HH, 0.07)   # swing
    crack = (rng.random(N) > 0.9993) * rng.normal(0, 1, N) * 0.25 + filt(rng.normal(0, 1, N), 3000, "high") * 0.004
    out += crack
    out = filt(out, 6500, "low")
# whoosh into every slide change
for a in bt["starts"][1:]:
    L = int(0.35 * SR); i = int(a * SR) - L
    if i > 0: out[i:i + L] += filt(rng.normal(0, 1, L), 1800, "high") * np.linspace(0, 1, L) ** 2 * (0.05 if name != "engine" else 0.08)
t = np.arange(N) / SR
out *= np.minimum(1, t / 0.15) * np.minimum(1, (DUR - t) / 1.2)
out = np.tanh(out / np.abs(out).max() * 1.5) / np.tanh(1.5)
sf.write(f"music_{name}.wav", np.stack([out, out], 1) * 0.95, SR)
print(name, round(DUR, 2))
