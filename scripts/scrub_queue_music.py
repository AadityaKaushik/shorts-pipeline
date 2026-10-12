"""Re-render every cloud-queued video WITHOUT background music and replace the
release assets (video + repaired scene). Old scenes that fail the new quality
gates get the production repair loop. Optional args filter tags by substring.

Run with the renderer container's BGM_FILE empty.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_test as p

REPO = "AadityaKaushik/shorts-pipeline"


def sh(*cmd, tries=3):
    for attempt in range(tries):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout
        if attempt < tries - 1:
            print("   (command failed, retrying)")
            time.sleep(10)
    raise RuntimeError(f"{' '.join(cmd[:4])}...: {proc.stderr[-300:]}")


def render(code, segments, job_id):
    body = json.dumps({"code": code, "scene": "Main", "job_id": job_id,
                       "segments": segments}).encode()
    req = urllib.request.Request("http://localhost:8000/render", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=1800).read())


def scrub_one(tag, name):
    with tempfile.TemporaryDirectory() as td:
        sh("gh", "-R", REPO, "release", "download", tag, "--dir", td)
        d = Path(td)
        code = (d / "scene.py").read_text(encoding="utf-8")
        script = json.loads((d / "script.json").read_text(encoding="utf-8"))
        segments = [s["narration"] for s in script["segments"]]
        job = f"scrub-{name[:40]}"

        r = render(code, segments, job)
        rounds = 0
        while not r.get("ok") and r.get("stage") == "render" and rounds < 3:
            rounds += 1
            print(f"   quality gate: {str(r.get('error'))[:110]}...")
            print(f"   repair round {rounds}")
            seg_json = json.dumps(script["segments"], indent=2)
            reply = p.llm("repair", p.fill("repair", ERROR=str(r.get("error")),
                                           CODE=code, SEGMENTS_JSON=seg_json),
                          want_json=False)
            code = p.extract_code(reply)
            if p.static_check(code, len(segments)):
                continue
            r = render(code, segments, job)
        if not r.get("ok"):
            raise RuntimeError(f"still failing: {str(r.get('error'))[:150]}")

        src = Path("data/renders") / job / "final.mp4"
        (d / "video.mp4").write_bytes(src.read_bytes())
        (d / "scene.py").write_text(code, encoding="utf-8")
        sh("gh", "-R", REPO, "release", "upload", tag,
           str(d / "video.mp4"), str(d / "scene.py"), "--clobber")
        print(f"   replaced ({r['duration']}s, music-free, {rounds} repair(s))")


tags = [t for t in sh("gh", "-R", REPO, "release", "list", "--limit", "100",
                      "--json", "tagName", "--jq", ".[].tagName").splitlines()
        if t.startswith("queue-")]
if len(sys.argv) > 1:
    tags = [t for t in tags if any(a in t for a in sys.argv[1:])]
print(f"{len(tags)} queued release(s) to scrub")

failed = []
for tag in sorted(tags):
    name = tag[len("queue-"):]
    print(f"== {name}")
    try:
        scrub_one(tag, name)
    except Exception as e:
        print(f"   FAILED: {type(e).__name__}: {str(e)[:200]}")
        failed.append(name)

print("FAILED:" if failed else "ALL_SCRUBBED", failed or "")
sys.exit(1 if failed else 0)
