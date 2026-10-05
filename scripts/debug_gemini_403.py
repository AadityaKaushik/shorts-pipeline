"""Diagnose the generateContent 403: print Google's error JSON (no keys)."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_test as p

for step in ["topic", "factcheck", "code", "repair", "metadata"]:
    model = p.MODELS.get(step, "gemini-3.8-flash")
    key = p.ENV[p.KEY_NAMES[step]]
    body = {"contents": [{"parts": [{"text": "Reply with the word ok"}]}]}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "shorts-pipeline/0.1", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        print(f"{step} ({model}): OK — {text!r}")
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:600]
        print(f"{step} ({model}): HTTP {e.code}\n{detail}\n")
