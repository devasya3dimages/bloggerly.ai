# Hype reel

31-second, 140 BPM, NBA-style psychedelic hype edit. Every section is 2 bars, and every cut and flash lands on the beat.

- `hype.html`: the whole edit, drawn on a canvas by `render(t)` (kaleidoscope, RGB split, tunnel, LED scoreboard).
- `music.py`: an original arena-trap track arranged bar-for-bar with the edit (`pip install numpy scipy soundfile`).
- `rec.js`: records frames with Playwright and pipes them to ffmpeg.

Posters: put the 55 Bloggerly-creatives-1 images (resized to 720 px wide, JPEG) in `p/`. They aren't committed.

```
python3 music.py
node rec.js 1080 1920 hype-9x16-silent.mp4
ffmpeg -i music.wav -af "acompressor=threshold=-16dB:ratio=3:makeup=4,loudnorm=I=-10:TP=-3,alimiter=limit=0.7" master.wav
ffmpeg -i hype-9x16-silent.mp4 -i master.wav -map 0:v -map 1:a -c:v libx264 -b:v 3300k -c:a aac -b:a 256k -shortest out.mp4
```
