"""Publish the oldest queued video to YouTube via the publishing services.

    python3 scripts/publish_daily.py           # post for real
    python3 scripts/publish_daily.py --dry     # everything except the HTTP post

Routing per HANDOVER section 13: posts 1-10 of the calendar month go through
Upload-Post, 11-30 through bundle.social, beyond that hold and alert.
On success the queue folder moves to data/published/ and publish_log.json gets
a line. Exit codes: 0 posted (or nothing to do / dry), 1 failure.
"""
import argparse
import json
import mimetypes
import shutil
import sys
import urllib.request
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "data" / "queue"
PUBLISHED = ROOT / "data" / "published"
LOG = ROOT / "data" / "state" / "publish_log.json"

UPLOAD_POST_LIMIT = 10      # free posts per month
BUNDLE_LIMIT = 20           # free posts per month


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def read_log():
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {"posts": []}


def month_counts(log):
    this_month = date.today().isoformat()[:7]
    counts = {"upload_post": 0, "bundle_social": 0}
    for p in log["posts"]:
        if p.get("ok") and p.get("date", "").startswith(this_month):
            counts[p["provider"]] = counts.get(p["provider"], 0) + 1
    return counts


def multipart(fields, file_field, file_path):
    """Encode a multipart/form-data body with one file. Stdlib only."""
    boundary = uuid.uuid4().hex
    body = b""
    for name, value in fields:
        body += (f"--{boundary}\r\nContent-Disposition: form-data; "
                 f'name="{name}"\r\n\r\n{value}\r\n').encode()
    ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body += (f"--{boundary}\r\nContent-Disposition: form-data; "
             f'name="{file_field}"; filename="{file_path.name}"\r\n'
             f"Content-Type: {ctype}\r\n\r\n").encode()
    body += file_path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def post_upload_post(env, video, meta, dry):
    fields = [
        ("user", env["UPLOAD_POST_PROFILE"]),
        ("platform[]", "youtube"),
        ("title", meta.get("title", "")[:100]),
        ("description", meta.get("description", "")),
        ("privacyStatus", "public"),
    ]
    if dry:
        print(f"  [dry] would POST to api.upload-post.com/api/upload: "
              f"{[(k, v[:60]) for k, v in fields]} + video ({video.stat().st_size // 1024} KB)")
        return {"ok": True, "dry": True}
    body, ctype = multipart(fields, "video", video)
    req = urllib.request.Request(
        "https://api.upload-post.com/api/upload", data=body,
        headers={"Authorization": f"Apikey {env['UPLOAD_POST_API_KEY']}",
                 "Content-Type": ctype, "User-Agent": "shorts-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.loads(r.read())
    print(f"  upload-post response: {json.dumps(resp)[:400]}")
    ok = bool(resp.get("success", resp.get("ok", False))) or "error" not in resp
    return {"ok": ok, "response": resp}


def post_bundle_social(env, video, meta, dry):
    team = env.get("BUNDLE_SOCIAL_TEAM_ID")
    if not team:
        return {"ok": False, "error": "BUNDLE_SOCIAL_TEAM_ID missing from .env "
                                      "(find it in the bundle.social dashboard)"}
    if dry:
        print("  [dry] would upload to api.bundle.social and create a YouTube SHORT post")
        return {"ok": True, "dry": True}
    # Step 1: upload media
    body, ctype = multipart([("teamId", team)], "file", video)
    req = urllib.request.Request(
        "https://api.bundle.social/api/v1/upload", data=body,
        headers={"x-api-key": env["BUNDLE_SOCIAL_API_KEY"], "Content-Type": ctype,
                 "User-Agent": "shorts-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=900) as r:
        up = json.loads(r.read())
    upload_id = up.get("id") or up.get("uploadId")
    if not upload_id:
        return {"ok": False, "error": f"no upload id in response: {json.dumps(up)[:300]}"}
    # Step 2: create the post
    post = {
        "teamId": team,
        "status": "SCHEDULED",
        "postDate": datetime.utcnow().isoformat() + "Z",
        "socialAccountTypes": ["YOUTUBE"],
        "data": {"YOUTUBE": {
            "type": "SHORT",
            "text": meta.get("title", "")[:100],
            "description": meta.get("description", ""),
            "uploadIds": [upload_id],
            "privacy": "PUBLIC",
            "madeForKids": False,
        }},
    }
    req = urllib.request.Request(
        "https://api.bundle.social/api/v1/post", data=json.dumps(post).encode(),
        headers={"x-api-key": env["BUNDLE_SOCIAL_API_KEY"],
                 "Content-Type": "application/json",
                 "User-Agent": "shorts-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read())
    print(f"  bundle.social response: {json.dumps(resp)[:400]}")
    return {"ok": True, "response": resp}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()
    env = load_env()

    # Posted-today guard: any duplicate trigger (late scheduler, manual click,
    # retry) is harmless — one successful post per calendar day, period.
    log_now = read_log()
    today = date.today().isoformat()
    if any(p.get("ok") and p.get("date") == today for p in log_now["posts"]):
        print(f"already posted today ({today}), nothing to do")
        return 0

    QUEUE.mkdir(parents=True, exist_ok=True)
    folders = sorted(p for p in QUEUE.iterdir() if p.is_dir())
    if not folders:
        print("queue empty, nothing to publish")
        return 0
    folder = folders[0]
    video = folder / "video.mp4"
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    print(f"publishing oldest: {folder.name} — {meta.get('title', '?')!r}")

    log = read_log()
    counts = month_counts(log)
    total = sum(counts.values())
    if counts["upload_post"] < UPLOAD_POST_LIMIT:
        provider, poster = "upload_post", post_upload_post
    elif counts["bundle_social"] < BUNDLE_LIMIT:
        provider, poster = "bundle_social", post_bundle_social
    else:
        print(f"HOLD: both monthly quotas used ({total} posts this month)")
        return 1
    print(f"provider: {provider} (this month so far: {counts})")

    try:
        result = poster(env, video, meta, args.dry)
    except Exception as e:
        detail = ""
        if hasattr(e, "read"):
            try:
                detail = e.read().decode()[:400]
            except Exception:
                pass
        print(f"  post FAILED: {type(e).__name__}: {e} {detail}")
        result = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    if args.dry:
        print("[dry] stopping before log/move")
        return 0

    log["posts"].append({
        "date": date.today().isoformat(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "provider": provider,
        "folder": folder.name,
        "title": meta.get("title"),
        "ok": result.get("ok", False),
        "detail": {k: v for k, v in result.items() if k != "ok"},
    })
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")

    if not result.get("ok"):
        print("post failed — folder stays in the queue for retry")
        return 1
    PUBLISHED.mkdir(parents=True, exist_ok=True)
    shutil.move(str(folder), PUBLISHED / folder.name)
    print(f"done: moved to published/{folder.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
