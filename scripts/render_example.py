"""Render one example scene through the real pipeline.

Usage:  python3 scripts/render_example.py ex1_eigenvectors
Output: data/renders/<name>/final.mp4
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

name = sys.argv[1]
root = Path(__file__).resolve().parent.parent
spec = json.loads((root / "examples" / f"{name}.json").read_text(encoding="utf-8"))
code = (root / "examples" / f"{name}.py").read_text(encoding="utf-8")

body = json.dumps({
    "code": code,
    "scene": "Main",
    "job_id": name,
    "segments": [s["narration"] for s in spec["segments"]],
}).encode()
req = urllib.request.Request("http://localhost:8000/render", data=body,
                             headers={"Content-Type": "application/json"})
start = time.time()
result = json.loads(urllib.request.urlopen(req, timeout=1800).read())
print(json.dumps(result, indent=2))
print(f"took {time.time() - start:.1f}s")
sys.exit(0 if result.get("ok") else 1)
