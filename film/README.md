# Brand film

A 40-second kinetic-type film (X × 1X case-study style) built from the Marketing Assets screenshots.

`film.html` is the whole film: every element has an in/out time, and `render(t)` draws frame `t`.
Open it in a browser and call `render(12.5)` in the console to scrub.

```
cd film
node rec.js 1080 1080 bloggerly-film-1x1.mp4    # square
node rec.js 1080 1920 bloggerly-film-9x16.mp4   # vertical
```

Needs Node with `playwright` and ffmpeg. Edit copy or timings in `film.html` and re-run.

## v3: male voice, 128 BPM drums, loud master (28 s)

Voice: `python3 vo.py am_michael` (speed 1.3).

1. `audio/vo.py` writes one WAV per line with Kokoro (`pip install kokoro-onnx soundfile`, plus the
   `kokoro.onnx` and `voices.bin` model files from the kokoro-onnx GitHub releases).
   To use another voice tool (e.g. Voicebox), export the same lines as `audio/line0.wav` … `line9.wav`
   and run `vo.json` through the same steps.
2. `python3 retime.py` re-times `film.html` to the line lengths and writes `film_fast.html` + `timeline.json`.
3. `cd audio && python3 mix.py` synthesises the 120 BPM music bed, lays the voice on the timeline,
   ducks the music under it and writes `mix.wav` (needs `scipy`).
4. `FILM=film_fast.html node rec.js 1080 1080 out.mp4`, then mux:
   `ffmpeg -i out.mp4 -i audio/mix.wav -map 0:v -map 1:a -c:v copy -af loudnorm=I=-10.5:TP=-2,alimiter=limit=0.8 -c:a aac -shortest final.mp4`
