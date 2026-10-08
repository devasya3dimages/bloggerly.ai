#!/usr/bin/env python3
"""Turn static bloggerly.ai ad creatives into looping motion b-roll.

For every shot in shots.json this renders two silent, seamlessly looping MP4s:
  out/feed/<name>.mp4   1080x1350 (4:5)  - IG/FB/LinkedIn feed
  out/reels/<name>.mp4  1080x1920 (9:16) - Reels / TikTok / Shorts / Stories

Frame 0 is the untouched poster (so the auto-thumbnail is the ad itself), the
camera moves through the scene, and the last frame eases back to the poster so
the loop is invisible. Headline and logo can be pinned while the scene moves.

Usage: python3 render.py SRC_DIR [OUT_DIR] [--only substring] [--jobs N]
Needs: python3, numpy, Pillow, ffmpeg (libx264).
"""
import argparse
import json
import math
import os
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageFilter

W, H = 1080, 1350          # feed frame (4:5)
RW, RH = 1080, 1920        # reels frame (9:16)
REEL_Y = 210               # poster top in the 9:16 frame; keeps the logo above TikTok/Reels UI
FPS = 30
DUR = 7.0
N = int(FPS * DUR)
HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- easing

def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * x * (x * (x * 6 - 15) + 10)


def env(t, a=0.04, b=0.86, c=0.995):
    """0 -> 1 between a..b, back to 0 between b..c. t in [0, 1]."""
    if t < b:
        return smooth((t - a) / (b - a))
    return 1.0 - smooth((t - b) / (c - b))


def wobble(t, seed, freqs=(0.37, 0.61, 1.13)):
    return sum(math.sin(2 * math.pi * f * t * DUR + seed * (i + 1.7)) / (i + 1) for i, f in enumerate(freqs)) / 1.8


# ---------------------------------------------------------------- camera

def camera(shot, t, seed):
    """Return zoom, centre (fx, fy as image fractions), rotation (deg), pixel jitter (dx, dy)."""
    fx, fy = shot["focal"]
    k = shot.get("strength", 1.0)
    lock = shot.get("lock", True)
    m = shot["motion"]
    e = env(t)
    z, cx, cy, rot, dx, dy = 1.0, 0.5, 0.5, 0.0, 0.0, 0.0
    sec = t * DUR

    if m == "push":
        z = 1 + 0.14 * k * e
        cx, cy = 0.5 + (fx - 0.5) * e, 0.5 + (fy - 0.5) * e
    elif m == "crash":  # documentary snap zoom, hold, ease out
        z = 1 + 0.03 * smooth(sec / 1.5)
        snap = smooth((sec - 1.5) / 0.22) * (1 - smooth((sec - 5.9) / 0.9))
        z += 0.24 * k * snap
        w = max(smooth(sec / 1.5) * 0.3, snap)
        cx, cy = 0.5 + (fx - 0.5) * w, 0.5 + (fy - 0.5) * w
    elif m == "spin":
        z = 1 + 0.13 * k * e
        rot = 4.0 * k * e * (1 if seed % 2 else -1)
        cx, cy = 0.5 + (fx - 0.5) * e, 0.5 + (fy - 0.5) * e
    elif m == "pan":
        z = 1 + 0.17 * k * (smooth(t / 0.2) if t < 0.86 else 1 - smooth((t - 0.86) / 0.135))
        p = smooth((t - 0.04) / 0.86) * 2 - 1
        half = 0.5 - 0.5 / z
        cx = 0.5 + p * half * 0.95
        cy = 0.5 + (fy - 0.5) * e
    elif m == "tiltup":
        a = smooth(t / 0.15) if t < 0.8 else 1 - smooth((t - 0.8) / 0.195)
        z = 1 + 0.28 * k * a
        p = smooth((t - 0.15) / 0.6)
        bottom = 1 - 0.5 / z
        cy = 0.5 + ((bottom + (fy - bottom) * p) - 0.5) * a
        cx = 0.5 + (fx - 0.5) * a
    elif m == "rise":
        z = 1 + 0.1 * k * e
        cx = 0.5 + (fx - 0.5) * e
        cy = 0.5 + (fy - 0.5 + 0.05 * (smooth(t / 0.9) - 0.4)) * e
    elif m == "bounce":  # beat pops at 120 bpm
        pulse = 0.0
        for b in np.arange(0.5, DUR - 0.6, 0.5):
            if sec >= b:
                pulse += math.exp(-(sec - b) / 0.11) * (1.6 if int(b * 2) % 4 == 0 else 1.0)
        z = 1 + (0.07 + 0.022 * pulse) * k * e
        cx, cy = 0.5 + (fx - 0.5) * e, 0.5 + (fy - 0.5) * e

    fxs = shot["fx"]
    if "handheld" in fxs:
        dx += 5 * wobble(t, seed) * (0.4 + e)
        dy += 4 * wobble(t, seed + 3) * (0.4 + e)
        rot += 0.25 * wobble(t, seed + 7)
    if "shake" in fxs:
        amp = 2.0 + 6.0 * (m == "crash" and 1.5 < sec < 2.1)
        dx += amp * wobble(t, seed, (2.3, 3.7, 5.9))
        dy += amp * wobble(t, seed + 5, (2.9, 4.1, 6.7))

    if lock and m != "tiltup":
        # pinned bands cover the top/bottom; land the subject in the open window between them
        w = (z - 1) / 0.14 if m != "crash" else (z - 1) / 0.35
        w = min(max(w, 0.0), 1.0)
        win = (shot["text"] + 0.04 + 0.88) / 2
        sy = fy + (win - fy) * w
        sx = fx + (0.5 - fx) * w
        cy = fy - (sy - 0.5) / z if m != "pan" else cy
        if m not in ("pan",):
            cx = fx - (sx - 0.5) / z
    if not lock and m == "push":
        # full-bleed art: keep the headline on screen by anchoring the top edge
        z = 1 + 0.07 * k * e
        cy = 0.5 / z
        cx = 0.5 + (fx - 0.5) * e * (1 - 1 / z)
    z = max(z, 1.0)
    half = 0.5 / z
    cx = min(max(cx, half), 1 - half)
    cy = min(max(cy, half), 1 - half)
    return z, cx, cy, rot, dx, dy


def transform(img, z, cx, cy, rot, dx, dy):
    """Sample img (W x H) so that image point (cx, cy) lands in the frame centre at zoom z."""
    if rot:  # zoom enough to hide corners while rotating
        r = math.radians(abs(rot))
        z = max(z, math.cos(r) + (H / W) * math.sin(r), math.cos(r) + (W / H) * math.sin(r))
    a = math.radians(rot)
    ca, sa = math.cos(a) / z, math.sin(a) / z
    ox, oy = W / 2 + dx, H / 2 + dy
    sx, sy = cx * W, cy * H
    # output (u, v) -> input (x, y)
    coeffs = (ca, -sa, sx - ca * ox + sa * oy,
              sa, ca, sy - sa * ox - ca * oy)
    return img.transform((W, H), Image.AFFINE, coeffs, resample=Image.BICUBIC)


# ---------------------------------------------------------------- effects

def masks(shot):
    y = np.arange(H, dtype=np.float32)[:, None] / H
    x = np.arange(W, dtype=np.float32)[None, :] / W
    tb = shot["text"]
    head = np.clip((tb + 0.02 - y) / 0.03, 0, 1)                       # headline band
    logo = np.clip(1 - np.sqrt(((x - 0.5) / 0.26) ** 2 + ((y - 0.935) / 0.055) ** 2), 0, 1)
    logo = np.clip(logo * 3, 0, 1)                                        # soft ellipse around wordmark
    pin = np.maximum(head, logo)[..., None]
    vig = 1 - 0.32 * np.clip(np.sqrt((x - 0.5) ** 2 + (y - 0.55) ** 2) / 0.72, 0, 1) ** 2.2
    return pin, vig[..., None]


def clean_plate(img, text):
    """Replace headline and logo areas with a vertical blend of the rows around them."""
    out = img.copy()
    for y0, y1, x0, x1 in ((0, text - 0.005, 0.0, 1.0), (0.865, 1.0, 0.18, 0.82)):
        a, b = int(y0 * H), min(int(y1 * H), H - 1)
        l, r = int(x0 * W), int(x1 * W)
        top = img[max(a - 1, 0), l:r] if a > 0 else img[b, l:r]
        bot = img[b, l:r] if y1 < 1.0 else img[a - 1, l:r]
        f = np.linspace(0, 1, b - a, dtype=np.float32)[:, None, None]
        fill = top[None] * (1 - f) + bot[None] * f
        fill = np.asarray(Image.fromarray(fill.astype(np.uint8)).filter(ImageFilter.GaussianBlur(25)), np.float32)
        fx = np.minimum(np.arange(r - l) / 40.0, (r - l - 1 - np.arange(r - l)) / 40.0).clip(0, 1)[None, :, None] if x0 > 0 else 1.0
        out[a:b, l:r] = fill * fx + out[a:b, l:r] * (1 - fx)
    return out


def render_shot(args):
    shot, src_dir, out_dir = args
    name = os.path.splitext(shot["file"])[0]
    path = os.path.join(src_dir, shot["file"])
    if not os.path.exists(path):
        return f"skip {shot['file']} (missing)"
    if all(os.path.exists(os.path.join(out_dir, k, name + ".mp4")) for k in ("feed", "reels")):
        return f"skip {name} (already rendered)"
    seed = sum(map(ord, name))
    rng = np.random.default_rng(seed)

    src = Image.open(path).convert("RGB")
    # cover-fit to 4:5
    s = max(W / src.width, H / src.height)
    src = src.resize((round(src.width * s), round(src.height * s)), Image.LANCZOS)
    l, t0 = (src.width - W) // 2, (src.height - H) // 2
    base = src.crop((l, t0, l + W, t0 + H))
    base_np = np.asarray(base, dtype=np.float32)

    bg = base.resize((RW, round(RW * H / W)), Image.BILINEAR)
    s2 = RH / bg.height * 1.08
    bg = bg.resize((round(bg.width * s2), round(bg.height * s2)), Image.BILINEAR)
    l2, t2 = (bg.width - RW) // 2, (bg.height - RH) // 2
    bg = bg.crop((l2, t2, l2 + RW, t2 + RH)).filter(ImageFilter.GaussianBlur(48))
    bg_np = np.asarray(bg, dtype=np.float32) * 0.82
    shadow = np.zeros((RH, 1), np.float32)
    yy = np.arange(RH)
    shadow[:, 0] = 1 - 0.35 * np.exp(-np.minimum(np.abs(yy - REEL_Y), np.abs(yy - REEL_Y - H)) / 40.0)
    bg_np *= shadow[..., None]

    pin, vig = masks(shot)
    plate = base
    if shot.get("lock", True):
        plate = Image.fromarray(clean_plate(base_np, shot["text"]).astype(np.uint8))
    fxs = shot["fx"]
    lock = shot.get("lock", True)
    grain = [rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32) for _ in range(6)]

    # deterministic flicker events
    flick = np.ones(N, np.float32)
    if "flicker" in fxs:
        flick -= rng.uniform(0, 0.035, N).astype(np.float32)
        for start in rng.choice(np.arange(int(N * 0.15), int(N * 0.8)), 3, replace=False):
            for j, d in enumerate((0.45, 0.15, 0.5, 0.2)[: rng.integers(2, 5)]):
                if start + j < N:
                    flick[start + j] = 1 - d
    light_mask = None
    if "lights" in fxs:
        hsv = np.asarray(base.convert("HSV"), dtype=np.float32) / 255
        light_mask = np.clip((hsv[..., 1] - 0.45) * 3, 0, 1) * np.clip((hsv[..., 2] - 0.55) * 3, 0, 1)
        light_mask = np.asarray(Image.fromarray((light_mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6)), np.float32)[..., None] / 255

    os.makedirs(os.path.join(out_dir, "feed"), exist_ok=True)
    os.makedirs(os.path.join(out_dir, "reels"), exist_ok=True)

    def enc(w, h, out):
        return subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-",
             "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", "-profile:v", "high",
             "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", out],
            stdin=subprocess.PIPE)

    feed = enc(W, H, os.path.join(out_dir, "feed", name + ".mp4"))
    reel = enc(RW, RH, os.path.join(out_dir, "reels", name + ".mp4"))
    canvas = bg_np.copy()

    for i in range(N):
        t = i / (N - 1)
        z, cx, cy, rot, dx, dy = camera(shot, t, seed)
        frame = np.asarray(transform(plate, z, cx, cy, rot, dx, dy), dtype=np.float32)
        e = env(t)

        if light_mask is not None:  # chase the string lights left -> right
            xs = np.linspace(0, 1, W, dtype=np.float32)[None, :, None]
            phase = np.sin(2 * math.pi * (xs * 3.0 - t * DUR * 0.9))
            lm = np.asarray(transform(Image.fromarray((light_mask[..., 0] * 255).astype(np.uint8)), z, cx, cy, rot, dx, dy), np.float32)[..., None] / 255
            frame *= 1 - lm * 0.55 * (0.5 - 0.5 * phase)
            frame += lm * 60 * np.clip(phase, 0, 1)
        if "heat" in fxs:
            rows = np.arange(H)
            off = (1.6 * np.sin(rows * 0.045 + t * DUR * 7.0) * np.clip((rows / H - 0.5) * 3, 0, 1)).astype(np.int32)
            idx = (np.arange(W)[None, :] + off[:, None]) % W
            frame = np.take_along_axis(frame, idx[..., None].repeat(3, 2), 1)
        if lock:
            frame = frame * (1 - pin) + base_np * pin
        if "glow" in fxs:
            small = Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).resize((W // 4, H // 4), Image.BILINEAR)
            g = np.asarray(small.point(lambda v: max(0, v - 150) * 2).filter(ImageFilter.GaussianBlur(10)).resize((W, H), Image.BILINEAR), np.float32)
            frame += g * (0.35 + 0.25 * math.sin(t * DUR * 2 * math.pi * 0.8))
        if "leak" in fxs:
            y = np.arange(H, dtype=np.float32)[:, None] / H
            x = np.arange(W, dtype=np.float32)[None, :] / W
            lx, ly = 0.85 - 0.5 * t, 0.15 + 0.1 * math.sin(t * math.pi)
            d = np.exp(-((x - lx) ** 2 + (y - ly) ** 2) / 0.09)[..., None]
            frame += d * np.array([255, 150, 80], np.float32) * (0.10 + 0.07 * e)
        if "vignette" in fxs:
            frame *= vig
        frame *= flick[i]
        if "grain" in fxs:
            gr = np.kron(grain[i % 6], np.ones((2, 2), np.float32))[..., None]
            frame += gr * 3.0

        out = np.clip(frame, 0, 255).astype(np.uint8)
        feed.stdin.write(out.tobytes())
        canvas[REEL_Y:REEL_Y + H] = out
        reel.stdin.write(canvas.astype(np.uint8).tobytes())
        canvas[REEL_Y:REEL_Y + H] = bg_np[REEL_Y:REEL_Y + H]

    for p in (feed, reel):
        p.stdin.close()
        p.wait()
    return f"done {name}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out", nargs="?", default=os.path.join(HERE, "out"))
    ap.add_argument("--only", default="")
    ap.add_argument("--jobs", type=int, default=os.cpu_count())
    a = ap.parse_args()
    shots = json.load(open(os.path.join(HERE, "shots.json")))["shots"]
    shots = [s for s in shots if a.only in s["file"]]
    with Pool(a.jobs) as pool:
        for msg in pool.imap_unordered(render_shot, [(s, a.src, a.out) for s in shots]):
            print(msg, flush=True)


if __name__ == "__main__":
    sys.exit(main())
