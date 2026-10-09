"""One-time: apply outro+bgm to the three chosen starter videos and queue them.

For each: POST /postprocess on its render job, then POST /package using the
topic/segments/metadata saved in its experiment dir.
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXP = ROOT / "data" / "experiments"

# (render job id, experiment run dir, dir holding script/factcheck segments)
STARTERS = [
    ("223539-central-limit-theorem-a1",
     "20261007_223539", "20261005_182304"),          # CLT: reused script lives in the older dir
    ("225706-fourier-transform-audio-frequency-decomp-a1",
     "20261007_225704", "20261007_225704"),
    ("230840-rc-circuit-charging-exponential-a3",
     "20261007_230838", "20261007_230838"),
]


def call(path, body):
    req = urllib.request.Request(
        "http://localhost:8000" + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=900) as r:
        return json.loads(r.read())


def job_dir(run_name):
    run = EXP / run_name
    return next(p for p in run.iterdir() if p.is_dir())


ok_all = True
for render_job, meta_run, seg_run in STARTERS:
    mdir, sdir = job_dir(meta_run), job_dir(seg_run)
    topic = json.loads((mdir / "topic.json").read_text(encoding="utf-8"))
    metadata = json.loads((mdir / "metadata.json").read_text(encoding="utf-8"))
    segments = None
    fc = sdir / "factcheck.json"
    if fc.exists():
        segs = json.loads(fc.read_text(encoding="utf-8"))
        segments = segs.get("segments")
    if not segments:
        segments = json.loads((sdir / "script.json").read_text(encoding="utf-8"))["segments"]

    print(f"== {topic['topic']}")
    r = call("/postprocess", {"job_id": render_job})
    print(f"   postprocess: {r}")
    if not r.get("ok"):
        ok_all = False
        continue
    r = call("/package", {
        "job_id": render_job,
        "topic": topic,
        "script": {"topic": topic.get("topic"), "segments": segments},
        "metadata": metadata,
        "attempts": [{"note": "starter video, post-processed manually"}],
    })
    print(f"   package: {r}")
    ok_all = ok_all and r.get("ok", False)

sys.exit(0 if ok_all else 1)
