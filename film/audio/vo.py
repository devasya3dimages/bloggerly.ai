import json, soundfile as sf, numpy as np, sys
from kokoro_onnx import Kokoro
k = Kokoro("kokoro.onnx", "voices.bin")
voice = sys.argv[1] if len(sys.argv) > 1 else "af_heart"
LINES = [
 "Meet Bloggerly.",
 "The AI content studio that takes you from idea to published post.",
 "Every post needs research, writing, images, citations, and distribution.",
 "So we put it all in one place.",
 "One tool for the whole publishing job.",
 "Schedule three months of content in one sitting.",
 "Then turn one finished post into six channels.",
 "Just ask, right inside Claude or ChatGPT.",
 "Your tools in. Every channel out.",
 "Don't just draft. Publish everywhere. Bloggerly dot A I.",
]
out = []
for i, line in enumerate(LINES):
    a, sr = k.create(line, voice=voice, speed=1.12, lang="en-us")
    a = np.asarray(a, np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]; a = a[max(nz[0]-200,0):nz[-1]+1200]
    sf.write(f"line{i}.wav", a, sr); out.append(len(a)/sr)
json.dump({"sr": sr, "dur": out, "lines": LINES}, open("vo.json","w"), indent=1)
print([round(d,2) for d in out], round(sum(out),2))
