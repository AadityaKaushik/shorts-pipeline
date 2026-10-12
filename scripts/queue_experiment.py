"""Package a successful experiment run into the queue (local + cloud release).

Usage: python3 scripts/queue_experiment.py <experiment job dir>
The dir must hold topic.json, metadata.json, result.json and (fact-checked)
script segments; the render job referenced by result.json must still exist.
"""
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
jdir = Path(sys.argv[1])

topic = json.loads((jdir / "topic.json").read_text(encoding="utf-8"))
metadata = json.loads((jdir / "metadata.json").read_text(encoding="utf-8"))
result = json.loads((jdir / "result.json").read_text(encoding="utf-8"))
render_job = result["video_path"].split("/")[-2]

segments = None
fc = jdir / "factcheck.json"
if fc.exists():
    segments = json.loads(fc.read_text(encoding="utf-8")).get("segments")
if not segments:
    segments = json.loads((jdir / "script.json").read_text(encoding="utf-8"))["segments"]


def post(path, body):
    req = urllib.request.Request("http://localhost:8000" + path,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=300).read())


r = post("/package", {"job_id": render_job, "topic": topic,
                      "script": {"topic": topic.get("topic"), "segments": segments},
                      "metadata": metadata,
                      "attempts": [{"note": f"packaged from experiment {jdir.name}"}]})
print("package:", r)
if not r.get("ok"):
    sys.exit(1)
folder = Path(r["folder"].replace("/files", str(ROOT / "data")))
name = folder.name
subprocess.run(["gh", "release", "create", f"queue-{name}",
                *[str(p) for p in folder.iterdir()],
                "--title", f"queued: {name}", "--notes", "waiting to publish",
                "--latest=false"], check=True)
print(f"release queue-{name} uploaded")
