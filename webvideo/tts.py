"""Narrate segments.json with Kokoro and build the timeline the scene animates to.

Writes build/narration.wav (one continuous track) and build/timeline.json
({"beats": [{"start", "dur"}], "total"}). Stdlib only; TTS service on :8001.
"""
import base64
import io
import json
import urllib.request
import wave
from pathlib import Path

D = Path(__file__).resolve().parent
OUT = D / "build"
LEAD, GAP, TAIL = 0.5, 0.4, 1.8   # seconds: before first line, between lines, after last

spec = json.loads((D / "segments.json").read_text(encoding="utf-8"))
OUT.mkdir(exist_ok=True)

clips, params = [], None
for i, text in enumerate(spec["narration"]):
    body = json.dumps({"text": text, "voice": spec["voice"]}).encode()
    req = urllib.request.Request("http://localhost:8001/speak", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    with wave.open(io.BytesIO(base64.b64decode(r["audio_b64"]))) as w:
        params = params or w.getparams()
        clips.append(w.readframes(w.getnframes()))
    print(f"  beat {i}: {r['duration']:.2f}s")

rate, width, ch = params.framerate, params.sampwidth, params.nchannels
silence = lambda s: b"\x00" * (int(s * rate) * width * ch)
frames_per_sec = rate * width * ch

audio, beats, t = silence(LEAD), [], LEAD
for clip in clips:
    dur = len(clip) / frames_per_sec
    beats.append({"start": round(t, 3), "dur": round(dur, 3)})
    audio += clip + silence(GAP)
    t += dur + GAP
total = t - GAP + TAIL
audio = audio[: int((t - GAP) * rate) * width * ch] + silence(TAIL)

with wave.open(str(OUT / "narration.wav"), "wb") as w:
    w.setparams(params)
    w.writeframes(audio)
(OUT / "timeline.json").write_text(json.dumps({"beats": beats, "total": round(total, 3)}, indent=1))
print(f"total {total:.2f}s, {len(beats)} beats")
