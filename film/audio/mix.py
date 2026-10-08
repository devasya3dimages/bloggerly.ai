"""Synthesize a fast, drum-led 128 BPM bed, lay the voiceover on the timeline, light ducking, loud master."""
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 48000
tl = json.load(open("../timeline.json"))
DUR = tl["scenes"][-1]
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
BPM = 128
BEAT = 60 / BPM
DROP = tl["scenes"][1]                  # drums hit when the first scene after the logo starts
END = tl["scenes"][-2] + 2.6            # final logo impact
STOP = END                              # beat stops for the impact

def filt(x, f, kind): return sosfilt(butter(2, f, kind, fs=SR, output="sos"), x)
def note(m): return 440 * 2 ** ((m - 69) / 12)
def put(buf, at, s, g=1.0):
    i = int(at * SR)
    if 0 <= i < N: buf[i:i + len(s)] += s[: N - i] * g

def grid(start, stop, step):  # beat-aligned times from the drop
    return [DROP + k * step for k in range(int((stop - DROP) / step) + 1) if start <= DROP + k * step < stop]

drums = np.zeros(N); synth = np.zeros(N)

# kick: pitch-swept sine + click
kt = np.arange(int(0.32 * SR)) / SR
kick = np.sin(2 * np.pi * (48 * kt + 110 * (1 - np.exp(-kt * 38)) / 38)) * np.exp(-kt * 10)
kick[: int(0.004 * SR)] += filt(rng.normal(0, 1, int(0.004 * SR)), 2000, "high") * 0.6
kick = np.tanh(kick * 1.8)
for b in grid(DROP, STOP, BEAT): put(drums, b, kick, 1.0)

# clap/snare on 2 and 4: layered noise bursts + body tone
st = np.arange(int(0.22 * SR)) / SR
noise = filt(filt(rng.normal(0, 1, len(st)), 900, "high"), 7000, "low")
snare = noise * np.exp(-st * 16) + 0.5 * np.sin(2 * np.pi * 190 * st) * np.exp(-st * 30)
clap = np.zeros(len(st))
for off in (0, 0.011, 0.022): clap[int(off * SR):] += noise[: len(st) - int(off * SR)] * np.exp(-st[: len(st) - int(off * SR)] * 60) * 0.6
sn = (snare + clap) * 0.55
for b in grid(DROP + BEAT, STOP, 2 * BEAT): put(drums, b, sn)

# 16th hats, open hat on the off-beat
ht = np.arange(int(0.04 * SR)) / SR
chh = filt(rng.normal(0, 1, len(ht)), 8000, "high") * np.exp(-ht * 90)
ot = np.arange(int(0.18 * SR)) / SR
ohh = filt(rng.normal(0, 1, len(ot)), 7000, "high") * np.exp(-ot * 18)
for j, b in enumerate(grid(DROP, STOP, BEAT / 4)):
    put(drums, b, chh, 0.16 if j % 2 else 0.24)
for b in grid(DROP + BEAT / 2, STOP, BEAT): put(drums, b, ohh, 0.13)

# snare roll build into the close + crash at the drop
roll_start = tl["scenes"][-2] - 2 * BEAT * 2
for j, b in enumerate(np.arange(roll_start, tl["scenes"][-2], BEAT / 4)):
    put(drums, b, sn, 0.25 + 0.5 * j / 16)
ct = np.arange(int(1.6 * SR)) / SR
crash = filt(rng.normal(0, 1, len(ct)), 4000, "high") * np.exp(-ct * 2.5) * 0.35
put(drums, DROP, crash); put(drums, tl["scenes"][-2], crash)

# riser over the logo intro
L = int(DROP * SR)
rise = filt(rng.normal(0, 1, L), 1200, "high") * np.linspace(0, 1, L) ** 2.5 * 0.25
drums[:L] += rise

# bass: 8th-note saw following roots, side-chain pumped
chords = [[57, 60, 64], [53, 57, 60], [48, 55, 60], [55, 59, 62]]  # Am F C G
bar = 4 * BEAT
bass = np.zeros(N); bt8 = np.arange(int(BEAT / 2 * SR)) / SR
for b in grid(DROP, STOP, BEAT / 2):
    root = chords[int((b - DROP) / (2 * bar)) % 4][0] - 24
    s = ((bt8 * note(root)) % 1 * 2 - 1) * np.exp(-bt8 * 5)
    put(bass, b, s)
synth += filt(bass, 380, "low") * 0.5

# stab chords on the off-beat + 16th arp
stt = np.arange(int(0.18 * SR)) / SR
for b in grid(DROP + BEAT / 2, STOP, BEAT):
    ch = chords[int((b - DROP) / (2 * bar)) % 4]
    s = sum(((stt * note(m + 12) * d) % 1 * 2 - 1) for m in ch for d in (0.996, 1.004)) * np.exp(-stt * 14)
    put(synth, b, filt(s, 2600, "low"), 0.05)
at = np.arange(int(0.2 * SR)) / SR
for j, b in enumerate(grid(DROP, STOP, BEAT / 4)):
    ch = chords[int((b - DROP) / (2 * bar)) % 4]; m = ch[[0, 1, 2, 1][j % 4]] + 24
    put(synth, b, np.sin(2 * np.pi * note(m) * at) * np.exp(-at * 22), 0.05)

# sidechain pump on synths from the kick
pump = np.ones(N)
pt = np.arange(int(BEAT * SR)) / SR
shape = 1 - 0.6 * np.exp(-pt * 14)
for b in grid(DROP, STOP, BEAT):
    i = int(b * SR); pump[i:i + len(shape)] = shape[: N - i]
synth *= pump

# final impact
it = np.arange(int(2.2 * SR)) / SR
boom = np.tanh(2 * np.sin(2 * np.pi * (36 * it + 70 * (1 - np.exp(-it * 10)) / 10)) * np.exp(-it * 2.2))
put(drums, END, boom * 0.9); put(drums, END, crash)

music = drums + synth
music *= np.minimum(1, (DUR - t) / 0.6)

# voiceover
voice = np.zeros(N)
for k, s0 in enumerate(tl["vo_start"]):
    a, sr = sf.read(f"line{k}.wav")
    if sr != SR: a = resample_poly(a, SR, sr)
    put(voice, s0, a)
voice = filt(voice, 90, "high")
voice = voice / np.abs(voice).max()
voice = np.tanh(voice * 2.2) / np.tanh(2.2)          # compress/saturate for a punchy ad read

act = np.abs(voice) > 0.03
rms = lambda x: np.sqrt(np.mean(x ** 2))
music = music * (rms(voice[act]) / rms(music)) * 10 ** (-5 / 20)   # loud bed, ~5 dB under the voice
env = filt(np.abs(voice), 8, "low"); env = np.clip(env / env.max() * 3, 0, 1)
mix = voice + music * (1 - 0.35 * env)
mix = np.tanh(mix / np.abs(mix).max() * 1.6) / np.tanh(1.6)       # soft clip for loudness
sf.write("mix.wav", np.stack([mix, mix], 1) * 0.97, SR)
print("dur", DUR, "drop", DROP, "end", END)
