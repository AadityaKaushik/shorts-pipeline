"""Publish the oldest queued video to YouTube via the publishing services.

    python3 scripts/publish_daily.py           # post for real
    python3 scripts/publish_daily.py --dry     # everything except the HTTP post

Routing per HANDOVER section 13: posts 1-10 of the calendar month go through
Upload-Post, 11-30 through bundle.social, beyond that hold and alert.
Graceful fallback: if the selected provider raises an HTTP quota/limit error
(402, 429) or a quota-related JSON flag in the response body, the script
automatically retries with the other provider before giving up.
On success the queue folder moves to data/published/ and publish_log.json gets
a line. Exit codes: 0 posted (or nothing to do / dry), 1 failure.

Override: set UPLOAD_POST_DISABLED=true in .env (or export it) to skip
Upload-Post entirely and go straight to bundle.social this month.
"""
import argparse
import json
import mimetypes
import shutil
import sys
import urllib.error
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

# HTTP status codes that reliably indicate a quota / billing limit was hit.
QUOTA_HTTP_CODES = {402, 429}


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


def _is_quota_error(exc):
    """Return True when *exc* looks like a provider quota / billing limit."""
    if isinstance(exc, urllib.error.HTTPError) and exc.code in QUOTA_HTTP_CODES:
        return True
    msg = str(exc).lower()
    return any(kw in msg for kw in ("quota", "limit", "exceeded", "402", "429",
                                     "upgrade", "plan", "billing"))


def _call_provider(name, poster, env, video, meta, dry):
    """Call *poster* and return (result_dict, quota_exceeded_bool)."""
    try:
        result = poster(env, video, meta, dry)
        # Some APIs signal quota exhaustion inside a 200 response body.
        if not result.get("ok"):
            detail = str(result.get("error", "") or result.get("response", "")).lower()
            quota_flag = any(kw in detail for kw in
                             ("quota", "limit", "exceeded", "upgrade", "plan", "billing"))
            return result, quota_flag
        return result, False
    except Exception as exc:
        detail = ""
        if hasattr(exc, "read"):
            try:
                detail = exc.read().decode()[:400]
            except Exception:
                pass
        print(f"  {name} FAILED: {type(exc).__name__}: {exc} {detail}")
        result = {"ok": False, "error": f"{type(exc).__name__}: {exc} {detail}".strip()}
        return result, _is_quota_error(exc)


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


def _provider_sequence(counts, env):
    """Return the ordered list of (provider_name, poster_fn) to try.

    - If UPLOAD_POST_DISABLED=true in the environment, upload-post is skipped
      entirely (the free quota is known to be exhausted for this month).
    - Otherwise the normal monthly-count gate applies: upload-post first until
      its limit is reached, then bundle.social.
    - Each entry is tried in turn; on a quota/limit error the next one is tried.
    """
    disabled = env.get("UPLOAD_POST_DISABLED", "").lower() in ("1", "true", "yes")

    sequence = []
    if not disabled and counts["upload_post"] < UPLOAD_POST_LIMIT:
        sequence.append(("upload_post", post_upload_post))
    if counts["bundle_social"] < BUNDLE_LIMIT:
        sequence.append(("bundle_social", post_bundle_social))
    # Reverse-fallback: if bundle.social is primary but hits a quota error,
    # add upload-post as a last resort (unless it is disabled).
    if not disabled and sequence and sequence[0][0] == "bundle_social":
        if counts["upload_post"] < UPLOAD_POST_LIMIT:
            sequence.append(("upload_post", post_upload_post))
    return sequence


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
    sequence = _provider_sequence(counts, env)

    if not sequence:
        total = sum(counts.values())
        print(f"HOLD: both monthly quotas used ({total} posts this month)")
        return 1

    print(f"provider sequence: {[p for p, _ in sequence]} (this month so far: {counts})")

    if args.dry:
        provider, poster = sequence[0]
        print(f"provider: {provider}")
        _call_provider(provider, poster, env, video, meta, dry=True)
        print("[dry] stopping before log/move")
        return 0

    result = None
    provider = None
    for attempt_provider, attempt_poster in sequence:
        print(f"  trying provider: {attempt_provider}")
        attempt_result, quota_hit = _call_provider(
            attempt_provider, attempt_poster, env, video, meta, dry=False)
        if attempt_result.get("ok"):
            result = attempt_result
            provider = attempt_provider
            break
        # Log the failed attempt for visibility.
        log["posts"].append({
            "date": today,
            "time": datetime.now().isoformat(timespec="seconds"),
            "provider": attempt_provider,
            "folder": folder.name,
            "title": meta.get("title"),
            "ok": False,
            "detail": {k: v for k, v in attempt_result.items() if k != "ok"},
        })
        if quota_hit:
            print(f"  {attempt_provider} quota exhausted — falling back to next provider")
            continue
        # Non-quota failure: stop immediately, do not waste the fallback.
        print(f"  {attempt_provider} failed with a non-quota error — not falling back")
        result = attempt_result
        provider = attempt_provider
        break

    if result is None:
        print("all providers exhausted")
        result = {"ok": False, "error": "all providers exhausted"}
        provider = "none"

    log["posts"].append({
        "date": today,
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
