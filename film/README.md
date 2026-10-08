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
