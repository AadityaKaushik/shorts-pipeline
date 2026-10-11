"""Render the same line in several candidate voices for a blind listen.

Kokoro voices via our tts service; Orpheus voices via Groq's speech API.
Output: assets/voice_samples/<name>.wav|mp3
"""
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "voice_samples"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
from scripts.verify_keys import load_env

LINE = ("Your phone records a thousand sounds a second. But sample too slowly, "
        "and a high note disguises itself as a low one. That's aliasing.")

KOKORO_VOICES = ["af_heart", "am_adam", "am_michael", "am_fenrir", "am_puck"]
ORPHEUS_VOICES = ["troy", "dan", "leo", "tara"]

for v in KOKORO_VOICES:
    try:
        req = urllib.request.Request(
            "http://localhost:8001/speak",
            data=json.dumps({"text": LINE, "voice": v}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.loads(r.read())
        (OUT / f"kokoro_{v}.wav").write_bytes(base64.b64decode(data["audio_b64"]))
        print(f"kokoro_{v}.wav OK ({data['duration']:.1f}s)")
    except Exception as e:
        print(f"kokoro_{v}: FAILED {type(e).__name__}")

key = load_env().get("GROQ_API_KEY", "")
for v in ORPHEUS_VOICES:
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/audio/speech",
            data=json.dumps({"model": "canopylabs/orpheus-v1-english",
                             "voice": v, "input": LINE,
                             "response_format": "wav"}).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {key}",
                     "User-Agent": "shorts-pipeline/0.1"})
        with urllib.request.urlopen(req, timeout=120) as r:
            audio = r.read()
        (OUT / f"orpheus_{v}.wav").write_bytes(audio)
        print(f"orpheus_{v}.wav OK ({len(audio) // 1024} KB)")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode()[:200]
        except Exception:
            pass
        print(f"orpheus_{v}: HTTP {e.code} {detail}")
    except Exception as e:
        print(f"orpheus_{v}: FAILED {type(e).__name__}")
