# Motion b-roll

Turns the static bloggerly.ai ad creatives into 7-second looping motion clips for social.

```
pip install numpy pillow        # plus ffmpeg with libx264
python3 render.py path/to/creatives            # renders every shot in shots.json -> out/
python3 render.py path/to/creatives --only horror --jobs 4
```

- `shots.json`: one entry per creative, with its focal point, headline height, motion and effects. To add a creative, add a line here.
- `render.py`: the renderer. Outputs `out/feed/*.mp4` (4:5) and `out/reels/*.mp4` (9:16).
- `SOCIAL_PLAN.md`: motion style per series, posting order, and a caption for every clip.

Source images live in the "Bloggerly creatives" Google Drive folder. The rendered videos are not committed.
