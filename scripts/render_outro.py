"""Render the outro scene through the renderer and save it as assets/outro.mp4."""
import json
import shutil
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
code = (ROOT / "scripts" / "outro_scene.py").read_text(encoding="utf-8")

body = json.dumps({"code": code, "scene": "Outro", "job_id": "outro",
                   "segments": []}).encode()
req = urllib.request.Request("http://localhost:8000/render", data=body,
                             headers={"Content-Type": "application/json"})
start = time.time()
result = json.loads(urllib.request.urlopen(req, timeout=900).read())
print(json.dumps(result, indent=2))
if result.get("ok"):
    src = ROOT / "data" / "renders" / "outro" / "final.mp4"
    dst = ROOT / "assets" / "outro.mp4"
    shutil.copy2(src, dst)
    print(f"saved -> {dst} ({dst.stat().st_size // 1024} KB)")
print(f"took {time.time() - start:.1f}s")
