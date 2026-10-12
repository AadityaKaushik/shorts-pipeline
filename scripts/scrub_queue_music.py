"""Re-render every cloud-queued video WITHOUT background music and replace the
release asset. Uses each release's own scene.py + script.json, so the visuals
and narration are identical — only the music disappears.

Run AFTER the renderer container has BGM_FILE empty.
"""
import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

REPO = "AadityaKaushik/shorts-pipeline"


def sh(*cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd[:3])}...: {p.stderr[-300:]}")
    return p.stdout


def render(code, segments, job_id):
    body = json.dumps({"code": code, "scene": "Main", "job_id": job_id,
                       "segments": segments}).encode()
    req = urllib.request.Request("http://localhost:8000/render", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=1800).read())


tags = [t for t in sh("gh", "-R", REPO, "release", "list", "--limit", "100",
                      "--json", "tagName", "--jq", ".[].tagName").splitlines()
        if t.startswith("queue-")]
print(f"{len(tags)} queued release(s) to scrub")

failed = []
for tag in sorted(tags):
    name = tag[len("queue-"):]
    print(f"== {name}")
    with tempfile.TemporaryDirectory() as td:
        sh("gh", "-R", REPO, "release", "download", tag, "--dir", td)
        d = Path(td)
        code = (d / "scene.py").read_text(encoding="utf-8")
        script = json.loads((d / "script.json").read_text(encoding="utf-8"))
        segments = [s["narration"] for s in script["segments"]]
        job = f"scrub-{name[:40]}"
        r = render(code, segments, job)
        if not r.get("ok"):
            print(f"   RENDER FAILED: {str(r.get('error'))[:200]}")
            failed.append(name)
            continue
        src = Path("data/renders") / job / "final.mp4"
        (d / "video.mp4").write_bytes(src.read_bytes())
        sh("gh", "-R", REPO, "release", "upload", tag, str(d / "video.mp4"),
           "--clobber")
        print(f"   replaced ({r['duration']}s, music-free)")

print("FAILED:" if failed else "ALL_SCRUBBED", failed or "")
sys.exit(1 if failed else 0)
