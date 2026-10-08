"""Synthesize a minimal tech-ambient bed at 120 BPM, lay the voiceover on the timeline, duck music under voice."""
import json
import numpy as np
import soundfile as sf
from scipy.signal import butter, sosfilt, resample_poly

SR = 48000
tl = json.load(open("../timeline.json"))
vo = json.load(open("vo.json"))
DUR = tl["scenes"][-1]
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(7)
BEAT = 0.5

def lp(x, f): return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)
def hp(x, f): return sosfilt(butter(2, f, "high", fs=SR, output="sos"), x)
def note(m): return 440 * 2 ** ((m - 69) / 12)

music = np.zeros(N)
# pad: Am F C G, 2 bars each, detuned saws through a slowly opening low-pass
chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
pad = np.zeros(N)
for ci in range(int(DUR / 4) + 1):
    ch = chords[ci % 4]; a, b = int(ci * 4 * SR), min(int((ci + 1) * 4 * SR + 0.3 * SR), N)
    if a >= N: break
    tt = np.arange(b - a) / SR
    seg = sum(((tt * note(m) * d) % 1 * 2 - 1) for m in ch for d in (0.997, 1.003))
    env = np.minimum(1, tt / 0.6) * np.minimum(1, (len(tt) / SR - tt) / 0.3)
    pad[a:b] += seg * env
pad = lp(pad, 900) * 0.022
music += pad

# sub kick on every beat from 1.9 s (after the logo), soft
kick = np.zeros(N)
kt = np.arange(int(0.35 * SR)) / SR
k1 = np.sin(2 * np.pi * (45 * kt + 60 * (1 - np.exp(-kt * 30)) / 30)) * np.exp(-kt * 9)
for bt in np.arange(1.9, DUR - 1.6, BEAT):
    i = int(bt * SR); kick[i:i + len(k1)] += k1[: N - i]
music += kick * 0.33

# off-beat hats
hat = hp(rng.normal(0, 1, int(0.05 * SR)), 7000) * np.exp(-np.arange(int(0.05 * SR)) / SR * 80)
for bt in np.arange(1.9 + BEAT / 2, DUR - 1.6, BEAT):
    i = int(bt * SR); music[i:i + len(hat)] += hat[: N - i] * 0.05

# plucked 8th-note arp
arp = np.zeros(N); pt = np.arange(int(0.4 * SR)) / SR
for j, bt in enumerate(np.arange(3.0, DUR - 1.6, BEAT / 2)):
    ch = chords[int(bt / 4) % 4]; m = ch[[0, 2, 1, 3, 2, 1, 3, 2][j % 8]] + 12
    s = (np.sin(2 * np.pi * note(m) * pt) + 0.3 * np.sin(4 * np.pi * note(m) * pt)) * np.exp(-pt * 11)
    i = int(bt * SR); arp[i:i + len(s)] += s[: N - i]
music += lp(arp, 3500) * 0.045

# whooshes into each scene change + impact on the final logo
for sc in tl["scenes"][1:-1]:
    L = int(0.45 * SR); a = int(sc * SR) - L
    if a < 0: continue
    w = np.linspace(0, 1, L) ** 2
    music[a:a + L] += hp(rng.normal(0, 1, L), 1500) * w * 0.035
logo_t = tl["scenes"][-2] + 2.75
it = np.arange(int(1.8 * SR)) / SR
boom = np.sin(2 * np.pi * (38 * it + 50 * (1 - np.exp(-it * 12)) / 12)) * np.exp(-it * 2.6) * 0.5 + lp(rng.normal(0, 1, len(it)), 2000) * np.exp(-it * 10) * 0.08
i = int(logo_t * SR); music[i:i + len(boom)] += boom[: N - i]

# fade
music *= np.minimum(1, t / 0.8) * np.minimum(1, (DUR - t) / 1.2)

# voiceover
voice = np.zeros(N)
for k, st in enumerate(tl["vo_start"]):
    a, sr = sf.read(f"line{k}.wav")
    if sr != SR: a = resample_poly(a, SR, sr)
    i = int(st * SR); voice[i:i + len(a)] += a[: N - i]
voice = voice / (np.abs(voice).max() + 1e-9) * 0.9
# gentle presence: high-pass rumble, slight compression
voice = hp(voice, 90)
voice = np.sign(voice) * np.abs(voice) ** 0.85

# duck music under voice
env = lp(np.abs(voice), 6)
env = np.clip(env / (env.max() + 1e-9) * 3, 0, 1)
duck = 1 - 0.55 * env
act = np.abs(voice) > 0.02
rms = lambda x: np.sqrt(np.mean(x ** 2))
music = music * (rms(voice[act]) / rms(music)) * 10 ** (-11 / 20)   # bed sits 11 dB under the voice
mix = voice + music * duck
mix = mix / np.abs(mix).max() * 0.95
st = np.stack([mix, mix], 1)
sf.write("mix.wav", st, SR)
sf.write("music_only.wav", np.stack([music, music], 1) / np.abs(music).max() * 0.9, SR)
sf.write("voice_only.wav", np.stack([voice, voice], 1) * 0.95, SR)
print("dur", DUR)
