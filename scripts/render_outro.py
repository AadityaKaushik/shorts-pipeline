"""Render the channel outro (with voiceover) and save it as assets/outro.mp4.

Synthesizes the voice line via the TTS service first, drops it in the job dir,
then renders the scene, which plays it with self.add_sound().
"""
import base64
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOB = ROOT / "data" / "renders" / "outro"

VOICE_LINE = ("Liked this one? Keep learning with The Compute Club — "
              "hit like and subscribe!")


def post(url, body, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


# 1. voice
JOB.mkdir(parents=True, exist_ok=True)
tts = post("http://localhost:8001/speak", {"text": VOICE_LINE})
(JOB / "voice.wav").write_bytes(base64.b64decode(tts["audio_b64"]))
(JOB / "voice.json").write_text(json.dumps({"duration": tts["duration"]}))
print(f"voice: {tts['duration']:.2f}s")

# 2. scene
code = (ROOT / "scripts" / "outro_scene.py").read_text(encoding="utf-8")
start = time.time()
result = post("http://localhost:8000/render",
              {"code": code, "scene": "Outro", "job_id": "outro", "segments": []},
              timeout=900)
print(json.dumps(result, indent=2))
if result.get("ok"):
    dst = ROOT / "assets" / "outro.mp4"
    shutil.copy2(JOB / "final.mp4", dst)
    print(f"saved -> {dst} ({dst.stat().st_size // 1024} KB)")
print(f"took {time.time() - start:.1f}s")
