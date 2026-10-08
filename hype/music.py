"""140 BPM arena-trap hype track, arranged bar-for-bar with hype.html's sections."""
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt

SR = 48000
BPM = 140; BT = 60 / BPM; BAR = 4 * BT
DUR = 18 * BAR + 0.15
N = int(DUR * SR); rng = np.random.default_rng(3)
def S(bar): return bar * BAR
def filt(x, f, k): return sosfilt(butter(2, f, k, fs=SR, output="sos"), x)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def put(buf, at, s, g=1.0):
    i = int(at * SR)
    if 0 <= i < N: buf[i:i + len(s)] += s[: N - i] * g
def steps(b0, b1, div=1):  # beat times from bar b0 to b1, `div` hits per beat
    return [S(b0) + k * BT / div for k in range(int((b1 - b0) * 4 * div))]
tt = lambda d: np.arange(int(d * SR)) / SR

drums = np.zeros(N); bass = np.zeros(N); syn = np.zeros(N); fx = np.zeros(N)

# --- sounds
t = tt(0.4); kick = np.tanh(2.2 * np.sin(2 * np.pi * (42 * t + 140 * (1 - np.exp(-t * 35)) / 35)) * np.exp(-t * 7))
kick[:200] += rng.normal(0, 0.5, 200)
t = tt(0.3); nz = filt(filt(rng.normal(0, 1, len(t)), 1000, "high"), 9000, "low")
clap = np.zeros(len(t))
for off in (0, 0.009, 0.019, 0.03): i = int(off * SR); clap[i:] += nz[: len(t) - i] * np.exp(-t[: len(t) - i] * (70 if off < 0.03 else 14))
clap = np.tanh(clap * 1.5) * 0.8
t = tt(0.35); stomp = (np.sin(2 * np.pi * (60 * t + 80 * (1 - np.exp(-t * 25)) / 25)) * np.exp(-t * 9) + filt(rng.normal(0, 1, len(t)), 400, "low") * np.exp(-t * 20) * 0.8)
t = tt(0.035); hat = filt(rng.normal(0, 1, len(t)), 8000, "high") * np.exp(-t * 110)
t = tt(0.2); snare = (filt(rng.normal(0, 1, len(t)), 1500, "high") * np.exp(-t * 18) + 0.6 * np.sin(2 * np.pi * 200 * t) * np.exp(-t * 35)) * 0.7
t = tt(1.8); crash = filt(rng.normal(0, 1, len(t)), 3500, "high") * np.exp(-t * 2.2) * 0.5
def s808(m, d, glide_from=None):
    t = tt(d); f = note(m) * np.ones(len(t))
    if glide_from is not None: f = note(m) + (note(glide_from) - note(m)) * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.tanh(2.5 * np.sin(ph) * np.minimum(1, t / 0.005) * np.exp(-t * 1.6))
def brass(ms, d):  # saw stack with swell, bright stab
    t = tt(d); s = sum(((t * note(m) * dt) % 1 * 2 - 1) for m in ms for dt in (0.995, 1.0, 1.006))
    env = np.minimum(1, t / 0.015) * np.exp(-t * 4.5)
    return filt(s * env, 3200, "low")

# --- arrangement
# bars 0-2: stadium stomp-stomp-clap + crowd swell + riser
for b in range(0, 2):
    for k, at in enumerate(steps(b, b + 1)):
        put(drums, at, stomp if k % 4 in (0, 1) else clap, 0.9)
L = int(S(2) * SR)
crowd = filt(filt(rng.normal(0, 1, L), 300, "high"), 2500, "low") * (0.15 + 0.25 * np.linspace(0, 1, L) ** 2) * (1 + 0.3 * np.sin(np.arange(L) / SR * 11))
fx[:L] += crowd * 0.5
fx[:L] += filt(rng.normal(0, 1, L), 2000, "high") * np.linspace(0, 1, L) ** 3 * 0.25

ROOTS = [33, 33, 29, 31]           # A, A, F, G (808 roots, MIDI)
CHORDS = [[57, 60, 64], [57, 60, 64], [53, 57, 60], [55, 59, 62]]

def groove(b0, b1, full=True, half=False):
    for b in range(b0, b1):
        bt = steps(b, b + 1)
        kpat = [0, 2.5] if half else ([0, 0.75, 2, 2.5] if full else [0, 1, 2, 3])
        for k in kpat: put(drums, bt[0] + k * BT, kick, 1.0)
        put(drums, bt[0] + (2 if not half else 2) * BT, clap, 1.0)
        if not half: put(drums, bt[0] + 3.75 * BT, clap, 0.35)
        for j, h in enumerate(steps(b, b + 1, 4 if full else 2)):
            put(drums, h, hat, 0.22 if j % 2 == 0 else 0.13)
        if full and b % 2 == 1:   # triplet hat roll at the end of every 2nd bar
            for j in range(6): put(drums, bt[3] + j * BT / 6, hat, 0.2)
        r = ROOTS[b % 4]
        put(bass, bt[0], s808(r, BAR * 0.7), 1.0)
        put(bass, bt[0] + 2.5 * BT, s808(r + (3 if b % 2 else 0), BT * 1.4, glide_from=r + 12), 0.9)
        put(syn, bt[0], brass([m + 12 for m in CHORDS[b % 4]], BT * 1.6), 0.09)
        if full: put(syn, bt[0] + 1.5 * BT, brass([m + 12 for m in CHORDS[b % 4]], BT * 0.5), 0.06)

put(drums, S(2), crash)
groove(2, 4, full=False)                 # lineup: building
put(drums, S(4), crash); put(fx, S(4), s808(21, 1.2), 0.6)
groove(4, 8, full=True)                  # kaleido drop + product
# scoreboard: buzzer + half-time
t = tt(0.9); buzz = np.sign(np.sin(2 * np.pi * 220 * t)) * 0.25 + np.sign(np.sin(2 * np.pi * 277 * t)) * 0.2
put(fx, S(8), filt(buzz * np.minimum(1, (0.9 - t) / 0.05), 3000, "low"), 0.45)
groove(8, 10, full=False, half=True)
put(drums, S(10), crash)
groove(10, 14, full=True)                # strobe + assists
for at in steps(10, 12, 2): put(syn, at, brass([m + 24 for m in CHORDS[int((at - S(10)) / BAR) % 4]], BT * 0.4), 0.035)
# bars 14-16: build — accelerating snare roll, riser, everything cuts on the last beat
for b in (14, 15):
    for k in range(4):
        put(drums, S(b) + k * BT, kick, 0.9)
roll = []
tr = S(14)
while tr < S(16) - BT:
    roll.append(tr); prog = (tr - S(14)) / (2 * BAR - BT); tr += BT / (2 if prog < 0.25 else 4 if prog < 0.6 else 8)
for i, r in enumerate(roll): put(drums, r, snare, 0.25 + 0.6 * i / len(roll))
L0, L1 = int(S(14) * SR), int((S(16) - BT) * SR)
fx[L0:L1] += filt(rng.normal(0, 1, L1 - L0), 1500, "high") * np.linspace(0, 1, L1 - L0) ** 2 * 0.35
sw = np.zeros(N); sw[L0:L1] = np.sin(2 * np.pi * np.cumsum(np.linspace(200, 1200, L1 - L0)) / SR) * np.linspace(0, 1, L1 - L0) * 0.08
fx += sw
# bars 16-18: impact
t = tt(3.0); boom = np.tanh(3 * np.sin(2 * np.pi * (30 * t + 90 * (1 - np.exp(-t * 9)) / 9)) * np.exp(-t * 1.4))
put(drums, S(16), boom, 1.0); put(drums, S(16), crash, 1.2); put(drums, S(16), kick, 1.0)
put(syn, S(16), brass([45, 57, 60, 64, 69], 2.5), 0.12)
put(bass, S(16), s808(21, 2.5), 0.9)

# sidechain synth/bass to the kick a little
mix = drums + 0.85 * filt(bass, 900, "low") + syn + fx
mix *= np.minimum(1, (DUR - np.arange(N) / SR) / 0.8)
mix = np.tanh(mix / np.abs(mix).max() * 2.0) / np.tanh(2.0)
sf.write("music.wav", np.stack([mix, mix], 1) * 0.95, SR)
print("dur", DUR)
