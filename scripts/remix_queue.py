"""Re-mix every cloud-queued video with the currently configured bgm, using the
kept final_raw.mp4 of the local scrub-* render jobs (no re-render, no LLM).
Replaces each release's video.mp4.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = "AadityaKaushik/shorts-pipeline"
RENDERS = Path(__file__).resolve().parent.parent / "data" / "renders"


def sh(*cmd, tries=3):
    for attempt in range(tries):
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            return proc.stdout
        if attempt < tries - 1:
            time.sleep(10)
    raise RuntimeError(f"{' '.join(cmd[:4])}...: {proc.stderr[-300:]}")


def postprocess(job_id):
    req = urllib.request.Request(
        "http://localhost:8000/postprocess",
        data=json.dumps({"job_id": job_id}).encode(),
        headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=900).read())


tags = [t for t in sh("gh", "-R", REPO, "release", "list", "--limit", "100",
                      "--json", "tagName", "--jq", ".[].tagName").splitlines()
        if t.startswith("queue-")]
failed = []
for tag in sorted(tags):
    name = tag[len("queue-"):]
    job = f"scrub-{name[:40]}"
    print(f"== {name}")
    if not (RENDERS / job / "final_raw.mp4").exists():
        print(f"   no local raw for {job} — skipping (needs re-render)")
        failed.append(name)
        continue
    r = postprocess(job)
    if not r.get("ok"):
        print(f"   postprocess failed: {str(r.get('error'))[:150]}")
        failed.append(name)
        continue
    with tempfile.TemporaryDirectory() as td:
        v = Path(td) / "video.mp4"
        v.write_bytes((RENDERS / job / "final.mp4").read_bytes())
        sh("gh", "-R", REPO, "release", "upload", tag, str(v), "--clobber")
    print(f"   re-mixed and replaced ({r.get('duration')}s)")

print("FAILED:" if failed else "ALL_REMIXED", failed or "")
sys.exit(1 if failed else 0)
