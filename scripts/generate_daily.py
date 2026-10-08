"""Production generation: make one video and put it at the back of the queue.

This is what the daily automation runs (both the morning slot and the top-up):
    python3 scripts/generate_daily.py            # generate unless the queue is full
    python3 scripts/generate_daily.py --topup    # same, but says so in the logs

Steps: queue-cap check -> full pipeline (topic ... render ... metadata, exactly
the harness's run_one) -> renderer /package (which also appends history.json).
Exit codes: 0 = packaged a video or queue already full; 1 = generation failed.
"""
import argparse
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline_test as p

RENDERER = "http://localhost:8000"
QUEUE_CAP = 5


def call(method, path, body=None):
    req = urllib.request.Request(
        RENDERER + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topup", action="store_true",
                    help="label this run as the top-up slot (same behaviour)")
    ap.add_argument("--cap", type=int, default=QUEUE_CAP)
    args = ap.parse_args()
    slot = "top-up" if args.topup else "daily"

    q = call("GET", "/queue/status")
    if q["count"] >= args.cap:
        print(f"[{slot}] queue already full ({q['count']}/{args.cap}), nothing to do")
        return 0

    print(f"[{slot}] queue {q['count']}/{args.cap} -> generating one video")
    history = (json.loads(p.HISTORY_PATH.read_text(encoding="utf-8"))
               if p.HISTORY_PATH.exists() else {"topics": []})
    run_dir = p.EXPERIMENTS / f"{datetime.now():%Y%m%d_%H%M%S}_{slot}"
    run_dir.mkdir(parents=True, exist_ok=True)

    run_args = SimpleNamespace(topic=None, category=None, code_model=None,
                               commit=False, reuse=None)
    row = p.run_one(run_dir, history, run_args, 0)
    if not row.get("ok"):
        print(f"[{slot}] generation FAILED at stage: {row.get('fail_stage')}")
        return 1

    packed = call("POST", "/package", row["package_info"])
    if not packed.get("ok"):
        print(f"[{slot}] packaging FAILED: {packed.get('error')}")
        return 1
    print(f"[{slot}] queued: {packed['folder']} "
          f"({row['duration']}s video, {row['attempts']} attempt(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
